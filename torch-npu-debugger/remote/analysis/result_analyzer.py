# Main result analyzer combining compile and test analysis
# All comments in this file are in English per project guidelines

from typing import List, Optional

from remote.core.exceptions import AnalysisError
from remote.models.data_models import (
    CommandResult,
    CompileAnalysis,
    TestAnalysis,
    ErrorAnalysis,
    ErrorInfo,
)
from remote.analysis.compile_analyzer import CompileAnalyzer
from remote.analysis.test_analyzer import TestAnalyzer


class ResultAnalyzer:
    """Main result analyzer combining compile and test analysis.

    Provides unified interface for analyzing command execution results,
    automatically detecting result type and applying appropriate analysis.

    Example:
        analyzer = ResultAnalyzer()

        # Analyze compile result
        compile_result = executor.execute_sync("bash ci/build.sh")
        analysis = analyzer.analyze_compile_result(compile_result)

        # Analyze test result
        test_result = executor.execute_sync("pytest test/test_ops/ -v")
        analysis = analyzer.analyze_test_result(test_result)

        # General error analysis
        error_analysis = analyzer.analyze_error(result.stderr, result.stdout)
    """

    def __init__(self):
        """Initialize result analyzer."""
        self.compile_analyzer = CompileAnalyzer()
        self.test_analyzer = TestAnalyzer()

    def analyze_compile_result(self, result: CommandResult) -> CompileAnalysis:
        """Analyze compilation result.

        Args:
            result: Command execution result from build

        Returns:
            CompileAnalysis: Detailed compile analysis
        """
        return self.compile_analyzer.analyze(result)

    def analyze_test_result(self, result: CommandResult) -> TestAnalysis:
        """Analyze test execution result.

        Args:
            result: Command execution result from pytest

        Returns:
            TestAnalysis: Detailed test analysis
        """
        return self.test_analyzer.analyze(result)

    def analyze_error(
        self,
        stderr: str,
        stdout: str = ""
    ) -> ErrorAnalysis:
        """Analyze error output and categorize.

        Args:
            stderr: Standard error output
            stdout: Standard output

        Returns:
            ErrorAnalysis: Error categorization and suggestions
        """
        combined = stderr + "\n" + stdout

        # Determine error category
        category = self._categorize_error(combined)

        # Determine severity
        severity = self._determine_severity(combined, category)

        # Extract root cause
        root_cause = self._extract_root_cause(combined, category)

        # Generate suggestions
        suggestions = self._generate_suggestions(category, combined)

        # Find related files
        related_files = self._extract_related_files(combined)

        # Calculate confidence
        confidence = self._calculate_confidence(category, combined)

        return ErrorAnalysis(
            category=category,
            severity=severity,
            root_cause=root_cause,
            suggestions=suggestions,
            related_files=related_files,
            confidence=confidence
        )

    def extract_key_errors(
        self,
        log: str,
        max_errors: int = 5
    ) -> List[ErrorInfo]:
        """Extract key errors from any log output.

        Args:
            log: Log output to analyze
            max_errors: Maximum number of errors to extract

        Returns:
            List of key error infos
        """
        # Try compile analyzer first
        errors = self.compile_analyzer.extract_key_errors(log, max_errors)

        if errors:
            return errors

        # Fall back to generic extraction
        return self._extract_generic_errors(log, max_errors)

    def _categorize_error(self, output: str) -> str:
        """Categorize error from output."""
        import re

        patterns = {
            "compile_error": [
                r"error:.*compile",
                r"g\+\+.*error",
                r"clang.*error",
                r"make.*Error",
            ],
            "link_error": [
                r"undefined reference",
                r"ld:.*cannot find",
                r"linker.*error",
            ],
            "import_error": [
                r"ImportError",
                r"ModuleNotFoundError",
                r"undefined symbol",
                r"No module named",
            ],
            "runtime_error": [
                r"RuntimeError",
                r"SIGSEGV",
                r"Segmentation fault",
                r"ACL_ERROR",
            ],
            "test_failure": [
                r"FAILED.*test",
                r"AssertionError",
                r"pytest.*failed",
            ],
            "environment_error": [
                r"CANN.*not found",
                r"ASCEND.*not set",
                r"environment.*error",
            ],
        }

        for category, patterns_list in patterns.items():
            for pattern in patterns_list:
                if re.search(pattern, output, re.IGNORECASE):
                    return category

        return "unknown"

    def _determine_severity(self, output: str, category: str) -> str:
        """Determine error severity."""
        import re

        # Critical indicators
        critical_patterns = [
            r"SIGSEGV|Segmentation fault",
            r"core dumped",
            r"FATAL",
            r"critical.*error",
        ]

        for pattern in critical_patterns:
            if re.search(pattern, output, re.IGNORECASE):
                return "critical"

        # High severity
        high_patterns = [
            r"undefined reference",
            r"cannot find.*library",
            r"import.*failed",
            r"version.*mismatch",
        ]

        for pattern in high_patterns:
            if re.search(pattern, output, re.IGNORECASE):
                return "high"

        # Medium severity
        if category in ("compile_error", "runtime_error"):
            return "medium"

        return "low"

    def _extract_root_cause(self, output: str, category: str) -> Optional[str]:
        """Extract root cause from output."""
        import re

        # Try to find the first actual error
        error_patterns = [
            r"error:\s*(.+?)(?=\n|$)",
            r"Error:\s*(.+?)(?=\n|$)",
            r"ERROR:\s*(.+?)(?=\n|$)",
        ]

        for pattern in error_patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                return match.group(1).strip()[:200]  # Limit length

        return None

    def _generate_suggestions(self, category: str, output: str) -> List[str]:
        """Generate fix suggestions based on category."""
        suggestions = []

        if category == "compile_error":
            suggestions.append("Check compiler version compatibility")
            suggestions.append("Verify all header files are present")
            suggestions.append("Clean and rebuild: rm -rf build/ && rebuild")

        elif category == "link_error":
            suggestions.append("Check library paths in CMakeLists.txt")
            suggestions.append("Verify all dependencies are built")
            suggestions.append("Check for ABI compatibility issues")

        elif category == "import_error":
            suggestions.append("Verify PYTHONPATH is set correctly")
            suggestions.append("Check that module is installed")
            suggestions.append("Run with python -v for verbose import tracing")

        elif category == "runtime_error":
            suggestions.append("Enable debug logging")
            suggestions.append("Check environment variables")
            suggestions.append("Verify hardware availability")

        elif category == "test_failure":
            suggestions.append("Run failing test in isolation")
            suggestions.append("Check test dependencies")
            suggestions.append("Verify test environment setup")

        elif category == "environment_error":
            suggestions.append("Source environment setup script")
            suggestions.append("Verify CANN installation")
            suggestions.append("Check ASCEND_HOME_PATH")

        return suggestions

    def _extract_related_files(self, output: str) -> List[str]:
        """Extract file paths from error output."""
        import re

        # Match file paths
        file_pattern = r'(/[\w\-/.]+\.(py|cpp|h|hpp|cmake|txt|yaml|json))'
        matches = re.findall(file_pattern, output)

        # Extract full paths
        files = [match[0] for match in matches]

        # Remove duplicates while preserving order
        seen = set()
        unique_files = []
        for f in files:
            if f not in seen and len(f) > 5:  # Filter out very short matches
                seen.add(f)
                unique_files.append(f)

        return unique_files[:10]  # Limit to 10 files

    def _calculate_confidence(self, category: str, output: str) -> float:
        """Calculate confidence level of analysis."""
        import re

        if category == "unknown":
            return 0.3

        # More specific patterns increase confidence
        confidence = 0.7

        # Boost confidence for clear error patterns
        clear_patterns = [
            r"error:\s*\w+",
            r"Error\(\w+\):",
            r"FAILED.*=",
        ]

        for pattern in clear_patterns:
            if re.search(pattern, output, re.IGNORECASE):
                confidence = min(confidence + 0.1, 0.95)

        return confidence

    def _extract_generic_errors(self, log: str, max_errors: int) -> List[ErrorInfo]:
        """Extract errors using generic patterns."""
        import re

        errors = []

        # Generic error patterns
        patterns = [
            r"(ERROR|Error|error):\s*(.+?)(?=\n|$)",
            r"(FAILED|Failed|failed):\s*(.+?)(?=\n|$)",
            r"(Exception|exception):\s*(.+?)(?=\n|$)",
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, log, re.MULTILINE):
                if len(errors) >= max_errors:
                    break

                message = match.group(2).strip()[:500]
                errors.append(ErrorInfo(
                    message=message,
                    category="generic_error"
                ))

        return errors
