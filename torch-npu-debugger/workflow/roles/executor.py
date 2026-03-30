# Executor role for workflow
# All comments in this file are in English per project guidelines

import os
import re
import subprocess
from datetime import datetime
from typing import Any, Dict, List, Optional

from workflow.roles.base import Role, RoleCapability
from workflow.models.task import Task, TaskState, RoleState
from workflow.models.message import MessageType


class Executor(Role):
    """Executor role responsible for actual implementation work.

    The executor performs the actual debugging work including:
    - Analyzing error logs
    - Locating source code
    - Implementing fixes
    - Self-testing
    """

    def __init__(self, coordinator: "Coordinator"):
        """Initialize the executor role."""
        super().__init__("executor", coordinator)
        self.capabilities = [
            RoleCapability.EXECUTE,
            RoleCapability.ANALYZE,
        ]
        self.sub_roles = {
            "analyzer": AnalyzerSubRole(self),
            "locator": LocatorSubRole(self),
            "fixer": FixerSubRole(self),
            "tester": TesterSubRole(self),
        }

    def receive_task(self, task: Task) -> bool:
        """Receive a task for execution.

        Args:
            task: The task to execute

        Returns:
            bool: True if task was accepted
        """
        if task.state != TaskState.EXECUTING and task.state != TaskState.RETRYING:
            return False

        self.current_task = task
        self.state = RoleState.WORKING
        task.current_role = self.name
        return True

    def execute(self, task: Task) -> Dict[str, Any]:
        """Execute the implementation task.

        Args:
            task: The task to execute

        Returns:
            Dict containing execution results
        """
        plan = task.plan
        if not plan:
            return {"success": False, "error": "No execution plan found"}

        deliverables = []
        all_success = True

        # Execute each step in the plan
        for step in plan.steps:
            if step.completed:
                continue

            # Check dependencies
            deps_satisfied = all(
                self._get_step_by_id(plan, dep_id).completed
                for dep_id in step.dependencies
            )
            if not deps_satisfied:
                continue

            # Execute step based on sub-role
            sub_role_name = step.role.replace("executor.", "")
            sub_role = self.sub_roles.get(sub_role_name)

            if sub_role:
                self.report_progress(
                    plan.get_progress(),
                    f"Executing: {step.description}"
                )

                result = sub_role.execute_step(step, task)

                if result.get("success"):
                    step.completed = True
                    step.actual_duration = result.get("duration", 0)
                    step.output = result.get("output", "")
                    deliverables.extend(result.get("deliverables", []))
                else:
                    all_success = False
                    self.report_block(
                        f"Step {step.step_id} failed: {result.get('error')}",
                        {"step": step.step_id, "result": result}
                    )
                    break

        # Complete task
        if all_success:
            self.complete_task(
                deliverables=deliverables,
                metrics={
                    "steps_completed": len([s for s in plan.steps if s.completed]),
                    "total_steps": len(plan.steps),
                    "lines_changed": sum(d.get("lines", 0) for d in deliverables),
                }
            )

        return {
            "success": all_success,
            "deliverables": deliverables,
            "steps_completed": len([s for s in plan.steps if s.completed]),
        }

    def _get_step_by_id(self, plan, step_id: str):
        """Get a step by its ID."""
        for step in plan.steps:
            if step.step_id == step_id:
                return step
        return None


class AnalyzerSubRole:
    """Sub-role for detailed log analysis."""

    def __init__(self, executor: Executor):
        self.executor = executor

    def execute_step(self, step, task: Task) -> Dict[str, Any]:
        """Execute analysis step."""
        context = task.context
        error_log = context.get("error_log", "")

        # Perform analysis
        analysis = {
            "error_summary": self._extract_error_summary(error_log),
            "stack_trace": self._parse_stack_trace(error_log),
            "error_category": self._categorize_error(error_log),
            "relevant_files": self._identify_relevant_files(error_log),
            "timestamp": datetime.now().isoformat(),
        }

        return {
            "success": True,
            "duration": 1800,
            "output": "Analysis complete",
            "deliverables": [{
                "name": "detailed_analysis",
                "type": "report",
                "content": analysis,
                "lines": 0
            }]
        }

    def _extract_error_summary(self, log: str) -> str:
        """Extract key error messages from log."""
        lines = log.split('\n')
        errors = []
        for line in lines:
            if 'error' in line.lower() or 'exception' in line.lower():
                errors.append(line.strip())
        return '\n'.join(errors[:5])  # Top 5 errors

    def _parse_stack_trace(self, log: str) -> List[str]:
        """Parse stack trace from log."""
        lines = log.split('\n')
        stack = []
        in_trace = False
        for line in lines:
            if 'Traceback' in line or 'stack trace' in line.lower():
                in_trace = True
            if in_trace:
                stack.append(line)
            if in_trace and line.strip() == '':
                break
        return stack

    def _categorize_error(self, log: str) -> str:
        """Categorize the error type."""
        log_lower = log.lower()
        if 'aclnn' in log_lower or 'acl_error' in log_lower:
            return 'ACLNN_LAYER'
        if 'not implemented' in log_lower:
            return 'REGISTRATION'
        if 'precision' in log_lower or 'allclose' in log_lower:
            return 'PRECISION'
        return 'GENERAL'

    def _identify_relevant_files(self, log: str) -> List[str]:
        """Identify files mentioned in the log."""
        # Pattern for file paths
        pattern = r'([\w/]+\.(py|cpp|h|hpp))'
        matches = re.findall(pattern, log)
        return list(set(m[0] for m in matches))


class LocatorSubRole:
    """Sub-role for source code location."""

    def __init__(self, executor: Executor):
        self.executor = executor

    def execute_step(self, step, task: Task) -> Dict[str, Any]:
        """Execute location step."""
        context = task.context
        analysis = context.get("analysis", {})
        relevant_files = analysis.get("relevant_files", [])

        # Locate source files
        locations = []
        for file_path in relevant_files:
            full_path = self._find_file(file_path, task)
            if full_path:
                locations.append({
                    "file": full_path,
                    "exists": True,
                    "type": self._get_file_type(full_path)
                })

        return {
            "success": True,
            "duration": 900,
            "output": f"Found {len(locations)} relevant files",
            "deliverables": [{
                "name": "source_locations",
                "type": "location_list",
                "content": locations,
                "lines": len(locations)
            }]
        }

    def _find_file(self, file_path: str, task: Task) -> Optional[str]:
        """Find a file in the workspace."""
        # Try relative to workspace
        workspace = task.context.get("workspace", ".")
        full_path = os.path.join(workspace, file_path)
        if os.path.exists(full_path):
            return full_path

        # Try various search paths
        search_paths = [
            "third_party/op-plugin/op_plugin/",
            "torch_npu/csrc/",
            "test/",
        ]
        for search_path in search_paths:
            full = os.path.join(workspace, search_path, file_path)
            if os.path.exists(full):
                return full

        return None

    def _get_file_type(self, file_path: str) -> str:
        """Get the type of file."""
        ext = os.path.splitext(file_path)[1]
        return {
            '.py': 'python',
            '.cpp': 'cpp',
            '.h': 'header',
            '.hpp': 'header',
        }.get(ext, 'unknown')


class FixerSubRole:
    """Sub-role for implementing fixes."""

    def __init__(self, executor: Executor):
        self.executor = executor

    def execute_step(self, step, task: Task) -> Dict[str, Any]:
        """Execute fix implementation step."""
        context = task.context
        locations = context.get("locations", [])

        # Generate fix
        fix_result = self._generate_fix(task, locations)

        return {
            "success": fix_result["success"],
            "duration": fix_result.get("duration", 1800),
            "output": fix_result.get("message", ""),
            "deliverables": [{
                "name": "fix_patch",
                "type": "patch",
                "content": fix_result.get("patch", ""),
                "files_modified": fix_result.get("files_modified", []),
                "lines": fix_result.get("lines_changed", 0)
            }]
        }

    def _generate_fix(
        self,
        task: Task,
        locations: List[Dict]
    ) -> Dict[str, Any]:
        """Generate a fix based on analysis."""
        # This would integrate with the actual fix patterns
        # For now, return a placeholder structure

        classification = task.context.get("classification", {})
        category = classification.get("category", "GENERAL")

        # Generate appropriate fix based on category
        if category == "ACLNN_LAYER":
            return self._generate_aclnn_fix(task, locations)
        elif category == "PRECISION":
            return self._generate_precision_fix(task, locations)
        else:
            return self._generate_general_fix(task, locations)

    def _generate_aclnn_fix(self, task: Task, locations: List[Dict]) -> Dict:
        """Generate fix for ACLNN layer issues."""
        # Implementation would apply ACLNN fix patterns
        return {
            "success": True,
            "message": "ACLNN operator fix generated",
            "patch": "diff placeholder",
            "files_modified": [loc["file"] for loc in locations],
            "lines_changed": 50,
            "duration": 1800
        }

    def _generate_precision_fix(self, task: Task, locations: List[Dict]) -> Dict:
        """Generate fix for precision issues."""
        return {
            "success": True,
            "message": "Precision handling fix generated",
            "patch": "diff placeholder",
            "files_modified": [loc["file"] for loc in locations],
            "lines_changed": 30,
            "duration": 1200
        }

    def _generate_general_fix(self, task: Task, locations: List[Dict]) -> Dict:
        """Generate general fix."""
        return {
            "success": True,
            "message": "General fix generated",
            "patch": "diff placeholder",
            "files_modified": [loc["file"] for loc in locations],
            "lines_changed": 20,
            "duration": 900
        }


class TesterSubRole:
    """Sub-role for self-testing."""

    def __init__(self, executor: Executor):
        self.executor = executor

    def execute_step(self, step, task: Task) -> Dict[str, Any]:
        """Execute self-test step."""
        context = task.context
        fix_result = context.get("fix_result", {})

        # Run self-tests
        test_results = self._run_self_tests(task, fix_result)

        return {
            "success": test_results["success"],
            "duration": 1800,
            "output": test_results.get("summary", ""),
            "deliverables": [{
                "name": "self_test_report",
                "type": "test_report",
                "content": test_results,
                "lines": test_results.get("tests_run", 0)
            }]
        }

    def _run_self_tests(
        self,
        task: Task,
        fix_result: Dict
    ) -> Dict[str, Any]:
        """Run self-tests on the fix."""
        # Run relevant tests
        tests = self._identify_relevant_tests(task)

        results = {
            "tests_run": len(tests),
            "tests_passed": 0,
            "tests_failed": 0,
            "details": []
        }

        for test in tests:
            # Would actually run the test
            result = self._run_single_test(test, task)
            results["details"].append(result)
            if result["passed"]:
                results["tests_passed"] += 1
            else:
                results["tests_failed"] += 1

        results["success"] = results["tests_failed"] == 0
        results["summary"] = (
            f"Tests: {results['tests_run']}, "
            f"Passed: {results['tests_passed']}, "
            f"Failed: {results['tests_failed']}"
        )

        return results

    def _identify_relevant_tests(self, task: Task) -> List[str]:
        """Identify tests relevant to the fix."""
        # Extract from task context
        operator_name = task.context.get("operator_name", "")
        return [
            f"test/test_v2r1_ops/test_{operator_name}.py",
            "test/test_common/test_basic_ops.py",
        ]

    def _run_single_test(self, test: str, task: Task) -> Dict:
        """Run a single test."""
        # Placeholder - would actually execute pytest
        return {
            "test": test,
            "passed": True,
            "duration": 10,
            "output": "Test passed"
        }
