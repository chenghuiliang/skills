# Evaluator agent for reviewing and accepting work
# All comments in this file are in English per project guidelines

import os
import sys
from datetime import datetime
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ..core import Agent, AgentCapability, AgentState
from ..messaging import Message, MessageType


class EvaluatorAgent(Agent):
    """Evaluator agent responsible for reviewing deliverables and accepting/rejecting work.

    Based on workflow/roles/evaluator.py design.

    The evaluator:
    - Reviews deliverables from executor
    - Checks acceptance criteria
    - Approves or rejects work with feedback
    - Triggers rework if needed
    """

    def __init__(
        self,
        agent_id: str = "evaluator",
        message_bus=None
    ):
        """Initialize evaluator agent."""
        super().__init__(
            agent_id=agent_id,
            capabilities=[AgentCapability.EVALUATE],
            message_bus=message_bus
        )
        self._register_handlers()

    def _register_handlers(self):
        """Register message handlers."""
        self.register_handler(MessageType.TASK_ASSIGN, self._handle_evaluation_task)

    def _handle_specialized(self, message: Message):
        """Handle specialized messages."""
        pass

    def _handle_evaluation_task(self, task_id: str, payload: Dict) -> Dict:
        """Handle evaluation task."""
        self.logger.info(f"Starting evaluation for task {task_id}")
        self.transition_to(AgentState.WORKING, f"Evaluating {task_id}")
        self.current_task = task_id

        try:
            deliverables = payload.get("deliverables", [])
            criteria = payload.get("acceptance_criteria", [])
            plan = payload.get("plan", {})

            self.report_progress(10, "Starting evaluation")

            # Evaluate each deliverable
            evaluation_results = []
            for i, deliverable in enumerate(deliverables):
                progress = 10 + (i + 1) * 70 // len(deliverables)
                self.report_progress(
                    progress,
                    f"Evaluating: {deliverable.get('name', 'unknown')}"
                )
                result = self._evaluate_deliverable(deliverable, criteria)
                evaluation_results.append(result)

            # Check acceptance criteria
            self.report_progress(90, "Checking acceptance criteria")
            criteria_met = self._check_criteria(criteria, deliverables)

            # Make decision
            passed = all(r["passed"] for r in evaluation_results) and criteria_met

            self.report_progress(100, "Evaluation complete")

            result = {
                "passed": passed,
                "evaluation_results": evaluation_results,
                "criteria_met": criteria_met,
                "workflow_step": "evaluation"
            }

            if passed:
                self.logger.info(f"Task {task_id} PASSED evaluation")
                self.send_message(
                    recipient="coordinator",
                    message_type=MessageType.TASK_COMPLETE,
                    payload={
                        "task_id": task_id,
                        "agent_id": self.agent_id,
                        "result": result
                    }
                )
                self.metrics.tasks_completed += 1
                self.transition_to(AgentState.IDLE, "Evaluation passed")
            else:
                feedback = self._generate_feedback(evaluation_results)
                self.logger.warning(f"Task {task_id} FAILED evaluation: {feedback}")

                # Send back for rework
                self.send_message(
                    recipient="executor",
                    message_type=MessageType.TASK_REJECT,
                    payload={
                        "task_id": task_id,
                        "reason": feedback,
                        "feedback": evaluation_results,
                        "requires_rework": True
                    }
                )
                self.metrics.tasks_failed += 1
                self.transition_to(AgentState.IDLE, "Evaluation failed")

            return {"success": passed, **result}

        except Exception as e:
            self.logger.error(f"Evaluation failed: {e}")
            self.metrics.tasks_failed += 1

            self.send_message(
                recipient="coordinator",
                message_type=MessageType.TASK_FAIL,
                payload={
                    "task_id": task_id,
                    "agent_id": self.agent_id,
                    "error": str(e)
                }
            )

            self.transition_to(AgentState.ERROR, str(e))
            return {"success": False, "error": str(e)}

        finally:
            self.current_task = None

    def _evaluate_deliverable(self, deliverable: Dict, criteria: List[str]) -> Dict:
        """Evaluate a single deliverable."""
        name = deliverable.get("name", "unknown")
        content = deliverable.get("content", {})

        checks = {
            "exists": deliverable is not None,
            "has_content": bool(content),
            "format_correct": self._check_format(deliverable),
            "quality_acceptable": self._check_quality(deliverable)
        }

        return {
            "name": name,
            "passed": all(checks.values()),
            "checks": checks
        }

    def _check_format(self, deliverable: Dict) -> bool:
        """Check if deliverable format is correct."""
        # Basic format check
        return True

    def _check_quality(self, deliverable: Dict) -> bool:
        """Check if deliverable quality is acceptable."""
        # Quality checks based on deliverable type
        content = deliverable.get("content", {})

        # Check for required fields
        if isinstance(content, dict):
            if "error" in content:
                return False

        return True

    def _check_criteria(self, criteria: List[str], deliverables: List[Dict]) -> bool:
        """Check if acceptance criteria are met."""
        # Check each criterion
        for criterion in criteria:
            # Simplified check - in real implementation would be more thorough
            if "test" in criterion.lower():
                # Check if tests are included
                has_tests = any(
                    d.get("name", "").startswith("test")
                    for d in deliverables
                )
                if not has_tests:
                    return False

        return True

    def _generate_feedback(self, results: List[Dict]) -> str:
        """Generate feedback for rejected work."""
        failed = [r for r in results if not r["passed"]]
        return f"Failed checks: {len(failed)} items need attention"

    def _run(self):
        """Main loop."""
        self.logger.info("Evaluator agent started, waiting for tasks")
        while not self._stop_event.is_set():
            self._stop_event.wait(1)
