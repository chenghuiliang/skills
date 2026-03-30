# Test output analyzer for pytest results
# All comments in this file are in English per project guidelines

import re
from typing import Dict, List, Optional

from remote.core.exceptions import AnalysisError
from remote.models.data_models import TestAnalysis, TestResult, CommandResult


class TestAnalyzer:
    """Analyzes pytest output for torch_npu tests.

    Parses test results, extracts failure details, and categorizes issues.

    Example:
        analyzer = TestAnalyzer()
        result = executor.execute_sync("pytest test/test_ops/test_add.py -v")
        analysis = analyzer.analyze(result)

        print(f"Passed: {analysis.passed}/{analysis.total_tests}")
        for test in analysis.failed_tests:
            print(f"Failed: {test}")
    """

    # Error patterns for test failures
    ERROR_PATTERNS = {
        r"NotImplementedError.*PrivateUse1": {
            "category": "operator_not_implemented",
            "message": "Operator not registered for NPU backend",
            "suggestion": "Check TORCH_LIBRARY_IMPL registration in op-plugin"
        },
        r"RuntimeError.*ACL_ERROR": {
            "category": "acl_error",
            "message": "ACL execution error",
            "suggestion": "Check CANN logs and ACL error code documentation"
        },
        r"AssertionError.*allclose|AssertionError.*rtol": {
            "category": "precision_error",
            "message": "Precision mismatch in test assertion",
            "suggestion": "Compare CPU/NPU results, check dtype handling"
        },
        r"RuntimeError.*shape mismatch|RuntimeError.*size mismatch": {
            "category": "shape_error",
            "message": "Tensor shape mismatch",
            "suggestion": "Check output shape calculation in KernelNpuOutputSize"
        },
        r"RuntimeError.*dtype": {
            "category": "dtype_error",
            "message": "Data type mismatch or unsupported",
            "suggestion": "Check dtype handling and conversion logic"
        },
        r"SIGSEGV|Segmentation fault": {
            "category": "crash",
            "message": "Segmentation fault during test",
            "suggestion": "Enable ASCEND_LAUNCH_BLOCKING=1, check for null pointer access"
        },
        r"EZ9999|error code.*0x800000": {
            "category": "aicore_error",
            "message": "AICore hardware error",
            "suggestion": "Check for multi-framework conflicts, verify input data"
        },
        r"EJ0001|HCCL.*failed": {
            "category": "hccl_error",
            "message": "HCCL communication error",
            "suggestion": "Kill残留进程, check device availability"
        },
        r"OOM|out of memory": {
            "category": "oom_error",
            "message": "Out of memory error",
            "suggestion": "Reduce batch size or check for memory leaks"
        },
        r"timeout|timed out": {
            "category": "timeout",
            "message": "Test execution timed out",
            "suggestion": "Check for infinite loops or deadlocks"
        },
    }

    def analyze(self, result: CommandResult) -> TestAnalysis:
        """Analyze pytest output.

        Args:
            result: Command execution result

        Returns:
            TestAnalysis: Parsed test results
        """
        output = result.stdout + "\n" + result.stderr

        # Parse summary line
        summary = self._parse_summary(output)

        # Parse individual test results
        test_results = self._parse_test_results(output)

        # Extract failed tests
        failed_tests = [t.name for t in test_results if t.status == "failed"]

        # Build error details map
        error_details: Dict[str, str] = {}
        for test in test_results:
            if test.status == "failed" and test.error_message:
                error_details[test.name] = test.error_message

        # Calculate totals
        passed = sum(1 for t in test_results if t.status == "passed")
        failed = sum(1 for t in test_results if t.status == "failed")
        skipped = sum(1 for t in test_results if t.status == "skipped")
        errors = sum(1 for t in test_results if t.status == "error")

        # Estimate duration if not in summary
        duration = summary.get("duration", result.execution_time)

        return TestAnalysis(
            success=result.exit_code == 0 and failed == 0,
            total_tests=summary.get("total", len(test_results)),
            passed=summary.get("passed", passed),
            failed=summary.get("failed", failed),
            skipped=summary.get("skipped", skipped),
            errors=summary.get("errors", errors),
            duration=duration,
            failed_tests=failed_tests,
            error_details=error_details,
            test_results=test_results,
            raw_output=output[:10000]  # Limit raw output
        )

    def _parse_summary(self, output: str) -> Dict[str, int]:
        """Parse pytest summary line.

        Example formats:
            ===== 10 passed, 2 failed, 1 skipped in 5.32s =====
            ===== 5 passed in 2.1s =====
            ===== 1 failed in 0.5s =====
        """
        summary = {}

        # Match summary line
        pattern = r"=+\s*(.+?)\s*in\s+([\d.]+)s\s*=+"
        match = re.search(pattern, output)

        if match:
            counts_str = match.group(1)
            duration = float(match.group(2))
            summary["duration"] = duration

            # Parse counts
            count_pattern = r"(\d+)\s+(\w+)"
            for count_match in re.finditer(count_pattern, counts_str):
                count = int(count_match.group(1))
                status = count_match.group(2).lower()

                if status in ("passed", "failed", "skipped", "error"):
                    summary[status] = count

            # Calculate total
            summary["total"] = sum(
                summary.get(k, 0) for k in ["passed", "failed", "skipped", "error"]
            )

        return summary

    def _parse_test_results(self, output: str) -> List[TestResult]:
        """Parse individual test results from output."""
        results = []

        # Pattern for test status lines
        test_pattern = r"(PASSED|FAILED|ERROR|SKIPPED)\s+\[\s*([\d.]+)%\]\s+(.+?)(?=\n|$)"

        for match in re.finditer(test_pattern, output):
            status_code = match.group(1)
            percentage = float(match.group(2))
            test_name = match.group(3).strip()

            # Map status codes
            status_map = {
                "PASSED": "passed",
                "FAILED": "failed",
                "ERROR": "error",
                "SKIPPED": "skipped"
            }
            status = status_map.get(status_code, "unknown")

            # Extract error message for failed tests
            error_message = None
            stack_trace = None

            if status in ("failed", "error"):
                error_message, stack_trace = self._extract_error_for_test(
                    output, test_name
                )

            results.append(TestResult(
                name=test_name,
                status=status,
                duration=0.0,  # Would need to parse from detailed output
                error_message=error_message,
                stack_trace=stack_trace
            ))

        return results

    def _extract_error_for_test(
        self,
        output: str,
        test_name: str
    ) -> tuple:
        """Extract error message and stack trace for a specific test.

        Args:
            output: Full test output
            test_name: Name of the test

        Returns:
            Tuple of (error_message, stack_trace)
        """
        # Find the section for this test
        # Look for test name followed by error info
        pattern = rf"{re.escape(test_name)}.*?\n(.*?)(?=\n\w+\s+\[|\Z)"
        match = re.search(pattern, output, re.DOTALL)

        if not match:
            return None, None

        section = match.group(1)

        # Extract the main error message (usually the last assertion or exception)
        error_message = None
        stack_trace = section.strip()

        # Look for common error patterns
        for pattern_regex, info in self.ERROR_PATTERNS.items():
            if re.search(pattern_regex, section, re.IGNORECASE):
                error_message = info["message"]
                break

        if not error_message:
            # Try to extract from AssertionError or other exceptions
            exception_match = re.search(
                r"(\w+Error):\s*(.+?)(?=\n\s+at |\n\s+File |\Z)",
                section,
                re.DOTALL
            )
            if exception_match:
                error_message = f"{exception_match.group(1)}: {exception_match.group(2).strip()}"

        return error_message, stack_trace

    def categorize_failure(self, error_message: str) -> Dict[str, str]:
        """Categorize a test failure based on error message.

        Args:
            error_message: Error message from test

        Returns:
            Dict with category, message, and suggestion
        """
        for pattern, info in self.ERROR_PATTERNS.items():
            if re.search(pattern, error_message, re.IGNORECASE):
                return {
                    "category": info["category"],
                    "message": info["message"],
                    "suggestion": info["suggestion"]
                }

        return {
            "category": "unknown",
            "message": "Unknown error type",
            "suggestion": "Check full error output for details"
        }

    def get_failed_tests_by_category(
        self,
        analysis: TestAnalysis
    ) -> Dict[str, List[str]]:
        """Group failed tests by error category.

        Args:
            analysis: Test analysis result

        Returns:
            Dict mapping category to list of test names
        """
        by_category: Dict[str, List[str]] = {}

        for test_name, error_msg in analysis.error_details.items():
            category = self.categorize_failure(error_msg)["category"]

            if category not in by_category:
                by_category[category] = []
            by_category[category].append(test_name)

        return by_category

    def generate_fix_suggestions(self, analysis: TestAnalysis) -> List[str]:
        """Generate fix suggestions based on test failures.

        Args:
            analysis: Test analysis result

        Returns:
            List of suggestions
        """
        suggestions = []
        categories = self.get_failed_tests_by_category(analysis)

        if "operator_not_implemented" in categories:
            suggestions.append(
                "Check TORCH_LIBRARY_IMPL registration for missing operators"
            )

        if "acl_error" in categories:
            suggestions.append("Check CANN version compatibility")
            suggestions.append("Enable ASDOPS_LOG_LEVEL=INFO for ATB errors")

        if "precision_error" in categories:
            suggestions.append("Compare CPU/NPU results with torch.allclose")
            suggestions.append("Check dtype promotion in op implementation")
            suggestions.append("Try setting CLOSE_MATMUL_K_SHIFT=1 for matmul issues")

        if "shape_error" in categories:
            suggestions.append("Check KernelNpuOutputSize for shape calculation")
            suggestions.append("Verify dim/keepdim handling for reduce ops")

        if "dtype_error" in categories:
            suggestions.append("Check npu_preparation::apply_tensor dtype parameter")
            suggestions.append("Verify output dtype matches input dtype")

        if "crash" in categories:
            suggestions.append("Run with ASCEND_LAUNCH_BLOCKING=1 to catch async errors")
            suggestions.append("Check for null pointer access in op implementation")

        if "aicore_error" in categories:
            suggestions.append("Check for multi-framework conflicts")
            suggestions.append("Isolate test with ASCEND_RT_VISIBLE_DEVICES")

        if "hccl_error" in categories:
            suggestions.append("Kill残留进程 and wait 10 seconds")
            suggestions.append("Check HCCL initialization")

        if "oom_error" in categories:
            suggestions.append("Check npu-smi info for memory usage")
            suggestions.append("Look for memory leaks in test")

        return suggestions
