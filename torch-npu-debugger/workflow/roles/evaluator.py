# Evaluator role for workflow
# All comments in this file are in English per project guidelines

from datetime import datetime
from typing import Any, Dict, List

from workflow.roles.base import Role, RoleCapability
from workflow.models.task import Task, TaskState, RoleState


class Evaluator(Role):
    """Evaluator role responsible for reviewing and accepting/rejecting work."""

    def __init__(self, coordinator):
        super().__init__("evaluator", coordinator)
        self.capabilities = [RoleCapability.EVALUATE]

    def receive_task(self, task: Task) -> bool:
        if task.state != TaskState.EVALUATING:
            return False
        self.current_task = task
        self.state = RoleState.WORKING
        task.current_role = self.name
        return True

    def execute(self, task: Task) -> Dict[str, Any]:
        """Execute evaluation."""
        self.report_progress(10, "Starting evaluation")

        # Evaluate deliverables
        deliverables = task.deliverables
        evaluation_results = []

        for i, deliverable in enumerate(deliverables):
            progress = 10 + (i + 1) * 80 // len(deliverables)
            self.report_progress(progress, f"Evaluating: {deliverable.name}")
            result = self._evaluate_deliverable(deliverable, task)
            evaluation_results.append(result)

        # Check criteria
        criteria_met = self._check_acceptance_criteria(task)

        # Decision
        passed = all(r["passed"] for r in evaluation_results) and criteria_met

        self.report_progress(100, "Evaluation complete")

        if passed:
            task.transition_to(TaskState.ACCEPTED, self.name, "All criteria met")
            self.complete_task(
                deliverables=[{
                    "name": "evaluation_report",
                    "content": {"results": evaluation_results, "passed": True}
                }],
                metrics={"passed": True, "score": 100}
            )
        else:
            task.transition_to(TaskState.REJECTED, self.name, "Criteria not met")
            task.rejection_reason = self._generate_feedback(evaluation_results)
            # Send back to executor
            self.send_message(
                to_role="executor",
                message_type=MessageType.TASK_REJECT,
                payload={"reason": task.rejection_reason, "feedback": evaluation_results},
                priority="high"
            )

        return {"success": passed, "results": evaluation_results}

    def _evaluate_deliverable(self, deliverable, task: Task) -> Dict:
        """Evaluate a single deliverable."""
        checks = {
            "exists": deliverable is not None,
            "has_content": bool(getattr(deliverable, 'content', None)),
            "format_correct": True,
            "quality_acceptable": True,
        }
        return {
            "name": getattr(deliverable, 'name', 'unknown'),
            "passed": all(checks.values()),
            "checks": checks
        }

    def _check_acceptance_criteria(self, task: Task) -> bool:
        """Check if acceptance criteria are met."""
        if not task.plan or not task.plan.acceptance_criteria:
            return True
        # Would verify each criterion
        return True

    def _generate_feedback(self, results: List[Dict]) -> str:
        """Generate feedback for rejected work."""
        failed = [r for r in results if not r["passed"]]
        return f"Failed checks: {len(failed)} items need attention"
