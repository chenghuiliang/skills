# Compile log analyzer for torch_npu builds
# All comments in this file are in English per project guidelines

import re
from typing import List, Dict, Optional

from remote.core.exceptions import AnalysisError
from remote.models.data_models import CompileAnalysis, ErrorInfo, CommandResult


class CompileAnalyzer:
    """Analyzes torch_npu compilation logs.

    Detects common error patterns and provides suggestions for fixes.

    Example:
        analyzer = CompileAnalyzer()
        result = executor.execute_sync("bash ci/build.sh")
        analysis = analyzer.analyze(result)

        if not analysis.success:
            for error in analysis.errors:
                print(f"Error: {error.message}")
            for suggestion in analysis.suggestions:
                print(f"Suggestion: {suggestion}")
    """

    # Error patterns with their categories and suggestions
    ERROR_PATTERNS = {
        # Link errors
        r"undefined reference to `op_api::": {
            "category": "link_error",
            "message": "op-plugin submodule commit mismatch",
            "suggestion": "Check git submodule status and align op-plugin with torch_npu tag"
        },
        r"is not a member of 'at_npu::native::OpCommand':": {
            "category": "link_error",
            "message": "OpCommand API version mismatch",
            "suggestion": "op-plugin version is newer than torch_npu, downgrade op-plugin or upgrade torch_npu"
        },
        r"ld: cannot find -lstdc\+\+fs": {
            "category": "link_error",
            "message": "GCC version/ABI incompatibility",
            "suggestion": "Use GCC version matching torch/Python (check with readelf -p .comment)"
        },
        r"ld: cannot find -ltorch_npu": {
            "category": "link_error",
            "message": "torch_npu library not found",
            "suggestion": "Check build output directory and library search path"
        },

        # Header errors
        r"No such file or directory:.*aclnn.*\.h": {
            "category": "header_error",
            "message": "CANN version too old, missing ACLNN headers",
            "suggestion": "Upgrade CANN to newer version or use DO_COMPATIBILITY fallback"
        },
        r"fatal error:.*No such file or directory": {
            "category": "header_error",
            "message": "Missing header file",
            "suggestion": "Check include paths and dependencies"
        },
        r"was not declared in this scope": {
            "category": "compile_error",
            "message": "Function or variable not declared",
            "suggestion": "Check header includes and forward declarations"
        },

        # C++ standard errors
        r"is_convertible_v was not declared": {
            "category": "cpp_standard_error",
            "message": "C++ standard set to C++14 instead of C++17",
            "suggestion": "Check CMakeLists.txt for CMAKE_CXX_STANDARD and set to 17"
        },
        r"if constexpr": {
            "category": "cpp_standard_error",
            "message": "C++17 feature used with older standard",
            "suggestion": "Ensure CMAKE_CXX_STANDARD is set to 17 in CMakeLists.txt"
        },

        # CANN/GE errors
        r"error code 500002": {
            "category": "cann_error",
            "message": "GE graph compilation failed",
            "suggestion": "Check plog files in $HOME/ascend/log/debug/plog/, verify opp_kernel package"
        },
        r"executor was not declared": {
            "category": "header_error",
            "message": "Missing forward declaration in header",
            "suggestion": "Add 'struct aclopExecute;' forward declaration"
        },

        # GCC ABI errors
        r"undefined symbol:.*cxx11": {
            "category": "abi_error",
            "message": "GCC ABI mismatch",
            "suggestion": "Check GCC versions with readelf -p .comment on libpython, torch, torch_npu"
        },

        # Version mismatch
        r"Failed to load the backend extension: torch_npu": {
            "category": "version_error",
            "message": "Version triplet incompatibility",
            "suggestion": "Check CANN + torch_npu + op-plugin version compatibility"
        },
    }

    # Warning patterns
    WARNING_PATTERNS = {
        r"warning: deprecated": {
            "category": "deprecation_warning",
            "message": "Using deprecated API"
        },
        r"warning: unused": {
            "category": "unused_warning",
            "message": "Unused variable or function"
        },
    }

    def analyze(self, result: CommandResult) -> CompileAnalysis:
        """Analyze compilation result.

        Args:
            result: Command execution result

        Returns:
            CompileAnalysis: Analysis result with errors and suggestions
        """
        output = result.stdout + "\n" + result.stderr

        errors = self._extract_errors(output)
        warnings = self._extract_warnings(output)

        # Categorize errors
        error_categories: Dict[str, List[str]] = {}
        for error in errors:
            cat = error.category
            if cat not in error_categories:
                error_categories[cat] = []
            error_categories[cat].append(error.message)

        # Generate suggestions
        suggestions = self._generate_suggestions(errors, output)

        # Detect specific error types
        is_link_error = any(
            e.category == "link_error" for e in errors
        )
        is_op_plugin_error = any(
            "op-plugin" in e.message or "op_plugin" in output
            for e in errors
        )
        is_abi_error = any(
            e.category == "abi_error" for e in errors
        )
        is_version_mismatch = any(
            e.category == "version_error" for e in errors
        )

        return CompileAnalysis(
            success=result.exit_code == 0,
            error_count=len(errors),
            warning_count=len(warnings),
            error_categories=error_categories,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            is_link_error=is_link_error,
            is_op_plugin_error=is_op_plugin_error,
            is_abi_error=is_abi_error,
            is_version_mismatch=is_version_mismatch,
            raw_output=output[:10000]  # Limit raw output size
        )

    def _extract_errors(self, output: str) -> List[ErrorInfo]:
        """Extract error messages from output."""
        errors = []

        # Common error patterns
        error_patterns = [
            # GCC/Clang errors
            r"([^:]+):(\d+):(\d+):\s*error:\s*(.+?)(?=\n[^\s]|\Z)",
            r"([^:]+):(\d+):\s*error:\s*(.+?)(?=\n[^\s]|\Z)",
            # Linker errors
            r"(ld):\s*(.+?)(?=\n[^\s]|\Z)",
            # CMake errors
            r"CMake Error.*:\s*(.+?)(?=\n[^\s]|\Z)",
            # Python build errors
            r"(subprocess\.CalledProcessError|error: command)\s*(.+?)(?=\n[^\s]|\Z)",
        ]

        for pattern in error_patterns:
            for match in re.finditer(pattern, output, re.MULTILINE | re.DOTALL):
                groups = match.groups()
                if len(groups) >= 2:
                    if len(groups) >= 4:
                        # With line/column info
                        file_path = groups[0]
                        line = int(groups[1]) if groups[1].isdigit() else None
                        column = int(groups[2]) if len(groups) > 2 and groups[2] and groups[2].isdigit() else None
                        message = groups[-1].strip()
                    elif len(groups) == 3:
                        file_path = groups[0]
                        line = int(groups[1]) if groups[1].isdigit() else None
                        column = None
                        message = groups[2].strip()
                    else:
                        file_path = None
                        line = None
                        column = None
                        message = groups[-1].strip()

                    # Determine category from patterns
                    category = "compile_error"
                    suggestion = None

                    for pattern_regex, info in self.ERROR_PATTERNS.items():
                        if re.search(pattern_regex, message, re.IGNORECASE):
                            category = info["category"]
                            suggestion = info.get("suggestion")
                            break

                    errors.append(ErrorInfo(
                        message=message,
                        category=category,
                        file_path=file_path,
                        line_number=line,
                        column=column,
                        suggestion=suggestion
                    ))

        # Also check for specific patterns that might not match above
        for pattern_regex, info in self.ERROR_PATTERNS.items():
            for match in re.finditer(pattern_regex, output, re.IGNORECASE):
                # Check if we already captured this error
                message = match.group(0)
                already_captured = any(e.message == message for e in errors)
                if not already_captured:
                    errors.append(ErrorInfo(
                        message=info["message"],
                        category=info["category"],
                        suggestion=info.get("suggestion")
                    ))

        return errors

    def _extract_warnings(self, output: str) -> List[ErrorInfo]:
        """Extract warning messages from output."""
        warnings = []

        warning_pattern = r"([^:]+):(\d+):(\d+):\s*warning:\s*(.+?)(?=\n[^\s]|\Z)"

        for match in re.finditer(warning_pattern, output, re.MULTILINE | re.DOTALL):
            groups = match.groups()
            if len(groups) >= 4:
                file_path = groups[0]
                line = int(groups[1]) if groups[1].isdigit() else None
                column = int(groups[2]) if groups[2].isdigit() else None
                message = groups[3].strip()

                category = "warning"
                for pattern_regex, info in self.WARNING_PATTERNS.items():
                    if re.search(pattern_regex, message, re.IGNORECASE):
                        category = info["category"]
                        break

                warnings.append(ErrorInfo(
                    message=message,
                    category=category,
                    file_path=file_path,
                    line_number=line,
                    column=column
                ))

        return warnings

    def _generate_suggestions(
        self,
        errors: List[ErrorInfo],
        output: str
    ) -> List[str]:
        """Generate fix suggestions based on errors."""
        suggestions = []

        # Collect unique suggestions from errors
        seen_suggestions = set()
        for error in errors:
            if error.suggestion and error.suggestion not in seen_suggestions:
                suggestions.append(error.suggestion)
                seen_suggestions.add(error.suggestion)

        # Add general suggestions based on error categories
        categories = {e.category for e in errors}

        if "link_error" in categories:
            suggestions.append("Clean build directory: rm -rf build/ && rebuild")
            suggestions.append("Check CMakeCache.txt for stale paths")

        if "header_error" in categories:
            suggestions.append("Verify CANN installation and ASCEND_HOME_PATH")
            suggestions.append("Check that op-plugin submodule is initialized")

        if "abi_error" in categories:
            suggestions.append("Compare GCC versions: readelf -p .comment on all .so files")
            suggestions.append("Consider using container with matching GCC version")

        if "version_error" in categories:
            suggestions.append("Check version compatibility matrix")
            suggestions.append("Verify CANN, torch_npu, and op-plugin versions align")

        if "cann_error" in categories:
            suggestions.append("Check plog files: $HOME/ascend/log/debug/plog/")
            suggestions.append("Verify opp_kernel package is installed for your SoC")

        return suggestions

    def extract_key_errors(self, output: str, max_errors: int = 5) -> List[ErrorInfo]:
        """Extract most important errors from output.

        Args:
            output: Build output
            max_errors: Maximum number of errors to return

        Returns:
            List of key error infos
        """
        all_errors = self._extract_errors(output)

        # Prioritize: link errors > header errors > compile errors
        priority_order = {
            "link_error": 0,
            "version_error": 1,
            "abi_error": 2,
            "header_error": 3,
            "cann_error": 4,
            "compile_error": 5,
            "cpp_standard_error": 6,
        }

        sorted_errors = sorted(
            all_errors,
            key=lambda e: priority_order.get(e.category, 999)
        )

        return sorted_errors[:max_errors]
