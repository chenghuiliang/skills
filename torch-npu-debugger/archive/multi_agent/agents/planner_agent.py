# Planner agent for creating execution plans
# All comments in this file are in English per project guidelines

import os
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ..core import Agent, AgentCapability, AgentState
from ..messaging import Message, MessageType


class PlannerAgent(Agent):
    """Planner agent responsible for analyzing problems and creating execution plans.

    Based on workflow/roles/planner.py design.

    The planner:
    - Receives user problems and performs initial analysis
    - Classifies issues by category and priority
    - Creates structured execution plans with steps
    - Defines acceptance criteria
    - Assesses risks and mitigation strategies
    """

    def __init__(
        self,
        agent_id: str = "planner",
        message_bus=None
    ):
        """Initialize planner agent."""
        super().__init__(
            agent_id=agent_id,
            capabilities=[AgentCapability.PLAN],
            message_bus=message_bus
        )
        self._register_handlers()

    def _register_handlers(self):
        """Register message handlers."""
        self.register_handler(MessageType.TASK_CREATE, self._handle_planning_task)

    def _handle_specialized(self, message: Message):
        """Handle specialized messages."""
        pass

    def _handle_planning_task(self, task_id: str, payload: Dict) -> Dict:
        """Handle planning task from coordinator."""
        self.logger.info(f"Starting planning for task {task_id}")
        self.transition_to(AgentState.WORKING, f"Planning {task_id}")
        self.current_task = task_id

        try:
            issue = payload.get("issue", {})

            # Step 1: Analyze problem
            self.report_progress(10, "Analyzing problem")
            analysis = self._analyze_problem(issue)

            # Step 2: Classify issue
            self.report_progress(30, "Classifying issue")
            classification = self._classify_issue(analysis)

            # Step 3: Create execution plan
            self.report_progress(50, "Creating execution plan")
            plan = self._create_execution_plan(analysis, classification)

            # Step 4: Define acceptance criteria
            self.report_progress(70, "Defining acceptance criteria")
            criteria = self._define_acceptance_criteria(classification)

            # Step 5: Assess risks
            self.report_progress(90, "Assessing risks")
            risks = self._assess_risks(analysis, classification)

            # Send plan to coordinator
            result = {
                "analysis": analysis,
                "classification": classification,
                "plan": plan,
                "acceptance_criteria": criteria,
                "risks": risks,
                "workflow_step": "planning"
            }

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
            self.transition_to(AgentState.IDLE, "Planning complete")

            return {"success": True, **result}

        except Exception as e:
            self.logger.error(f"Planning failed: {e}")
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

    def _analyze_problem(self, issue: Dict) -> Dict:
        """Analyze problem from issue description."""
        description = issue.get("description", "")
        error_log = issue.get("error_log", "")

        # Extract error patterns
        error_patterns = self._identify_error_patterns(error_log)

        # Extract affected components
        components = self._identify_components(description, error_log)

        return {
            "problem_summary": self._extract_summary(description),
            "error_patterns": error_patterns,
            "affected_components": components,
            "environment_info": issue.get("environment", {}),
            "timestamp": datetime.now().isoformat()
        }

    def _extract_summary(self, description: str) -> str:
        """Extract brief summary."""
        lines = description.strip().split('\n')
        first_line = lines[0] if lines else description
        return first_line[:200] if len(first_line) > 200 else first_line

    def _identify_error_patterns(self, error_log: str) -> List[Dict]:
        """Identify error patterns."""
        import re
        patterns = []
        log_lower = error_log.lower()

        error_keywords = [
            (r'ACL_ERROR_\w+', 'ACL Error', 'critical'),
            (r'NotImplementedError', 'Missing Implementation', 'high'),
            (r'dispatch.*conflict', 'Dispatch Conflict', 'critical'),
            (r'format mismatch', 'Format Error', 'high'),
            (r'allclose failed', 'Precision Issue', 'medium'),
        ]

        for pattern, label, severity in error_keywords:
            if re.search(pattern, log_lower):
                patterns.append({"pattern": pattern, "label": label, "severity": severity})

        return patterns

    def _identify_components(self, description: str, error_log: str) -> List[str]:
        """Identify affected components."""
        combined = (description + " " + error_log).lower()
        components = []

        component_map = {
            "opapi": "ACLNN Operator",
            "aclops": "ACL Operator",
            "format": "Format Handling",
            "dispatch": "Dispatch System",
            "dtype": "Data Type Handling",
        }

        for keyword, component in component_map.items():
            if keyword in combined:
                components.append(component)

        return components if components else ["Unknown"]

    def _classify_issue(self, analysis: Dict) -> Dict:
        """Classify issue by category and priority."""
        patterns = analysis.get("error_patterns", [])

        # Determine category
        labels = [p["label"] for p in patterns]
        if "ACL Error" in labels:
            category = "ACLNN_LAYER"
        elif "Missing Implementation" in labels:
            category = "REGISTRATION"
        elif "Precision Issue" in labels:
            category = "PRECISION"
        elif "Format Error" in labels:
            category = "FORMAT"
        else:
            category = "GENERAL"

        # Determine priority
        severities = [p["severity"] for p in patterns]
        if "critical" in severities:
            priority = "critical"
        elif "high" in severities:
            priority = "high"
        else:
            priority = "normal"

        return {
            "category": category,
            "priority": priority,
            "patterns": labels,
            "complexity": "high" if len(patterns) > 2 else "medium"
        }

    def _create_execution_plan(self, analysis: Dict, classification: Dict) -> Dict:
        """Create execution plan."""
        category = classification.get("category", "GENERAL")

        # Define steps based on category
        steps = [
            {
                "step_id": "1",
                "description": "Detailed error log analysis",
                "role": "executor.analyzer",
                "estimated_duration": 1800,
                "dependencies": []
            },
            {
                "step_id": "2",
                "description": "Navigate to relevant source code",
                "role": "executor.locator",
                "estimated_duration": 900,
                "dependencies": ["1"]
            },
            {
                "step_id": "3",
                "description": f"Implement fix for {category}",
                "role": "executor.fixer",
                "estimated_duration": 3600,
                "dependencies": ["2"]
            },
            {
                "step_id": "4",
                "description": "Self-test the fix",
                "role": "executor.tester",
                "estimated_duration": 1800,
                "dependencies": ["3"]
            },
            {
                "step_id": "5",
                "description": "Code review and acceptance testing",
                "role": "evaluator",
                "estimated_duration": 1800,
                "dependencies": ["4"]
            }
        ]

        return {
            "goal": f"Fix: {analysis.get('problem_summary', 'Unknown')}",
            "steps": steps,
            "total_estimated_duration": sum(s["estimated_duration"] for s in steps)
        }

    def _define_acceptance_criteria(self, classification: Dict) -> List[str]:
        """Define acceptance criteria."""
        category = classification.get("category", "GENERAL")

        criteria = [
            "Root cause clearly identified and documented",
            "Fix implemented with minimal code changes",
            "Code follows project coding standards",
            "All comments are in English",
        ]

        if category == "PRECISION":
            criteria.extend([
                "NPU results match CPU/GPU within tolerance",
                "All precision test cases pass"
            ])
        elif category == "REGISTRATION":
            criteria.extend([
                "Operator registered correctly",
                "Dispatch works for all input types"
            ])

        criteria.extend([
            "Regression tests pass",
            "New test cases added for the fix"
        ])

        return criteria

    def _assess_risks(self, analysis: Dict, classification: Dict) -> Dict[str, str]:
        """Assess risks and mitigation."""
        risks = {}
        complexity = classification.get("complexity", "medium")

        if complexity == "high":
            risks["High complexity"] = "Break into smaller tasks; engage expert if blocked"

        if classification.get("category") == "PRECISION":
            risks["Precision trade-offs"] = "Document acceptable tolerance"

        return risks

    def _run(self):
        """Main loop."""
        self.logger.info("Planner agent started, waiting for tasks")
        while not self._stop_event.is_set():
            self._stop_event.wait(1)
