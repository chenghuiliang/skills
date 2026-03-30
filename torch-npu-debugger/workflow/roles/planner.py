# Planner role for workflow
# All comments in this file are in English per project guidelines

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from workflow.roles.base import Role, RoleCapability
from workflow.models.task import Task, TaskState, RoleState, ExecutionPlan, ExecutionStep
from workflow.models.message import MessageType


class Planner(Role):
    """Planner role responsible for analyzing problems and creating execution plans.

    The planner receives user problems, performs initial analysis,
    classifies the issue, and creates a structured execution plan.
    """

    def __init__(self, coordinator: "Coordinator"):
        """Initialize the planner role."""
        super().__init__("planner", coordinator)
        self.capabilities = [
            RoleCapability.ANALYZE,
            RoleCapability.PLAN,
        ]

    def receive_task(self, task: Task) -> bool:
        """Receive a task for planning.

        Args:
            task: The task to plan

        Returns:
            bool: Always True as planner accepts all new tasks
        """
        self.current_task = task
        self.state = RoleState.WORKING
        task.current_role = self.name
        task.transition_to(TaskState.PLANNING, self.name, "Planning started")
        return True

    def execute(self, task: Task) -> Dict[str, Any]:
        """Execute the planning task.

        Args:
            task: The task to plan

        Returns:
            Dict containing the execution plan
        """
        self.report_progress(10, "Starting problem analysis")

        # Step 1: Analyze the problem
        analysis = self._analyze_problem(task)
        self.report_progress(30, "Problem analysis complete")

        # Step 2: Classify and scope
        classification = self._classify_issue(analysis)
        self.report_progress(50, f"Issue classified as: {classification['category']}")

        # Step 3: Create execution plan
        plan = self._create_execution_plan(task, analysis, classification)
        self.report_progress(70, "Execution plan created")

        # Step 4: Define acceptance criteria
        criteria = self._define_acceptance_criteria(task, classification)
        self.report_progress(90, "Acceptance criteria defined")

        # Step 5: Risk assessment
        risks = self._assess_risks(analysis, classification)
        self.report_progress(100, "Risk assessment complete")

        # Create deliverables
        deliverables = [
            {
                "name": "analysis_report",
                "content": analysis,
                "description": "Problem analysis report"
            },
            {
                "name": "execution_plan",
                "content": plan,
                "description": "Execution plan with steps"
            },
            {
                "name": "acceptance_criteria",
                "content": criteria,
                "description": "Acceptance criteria checklist"
            },
            {
                "name": "risk_assessment",
                "content": risks,
                "description": "Risk assessment and mitigations"
            }
        ]

        # Complete task
        self.complete_task(
            deliverables=deliverables,
            metrics={
                "analysis_time": analysis.get("time_spent", 0),
                "category": classification.get("category"),
                "estimated_steps": len(plan.steps) if plan else 0
            }
        )

        return {
            "success": True,
            "plan": plan,
            "classification": classification,
            "criteria": criteria,
            "risks": risks
        }

    def _analyze_problem(self, task: Task) -> Dict[str, Any]:
        """Analyze the problem from task description.

        Args:
            task: The task containing problem description

        Returns:
            Dict with analysis results
        """
        # Extract information from task
        description = task.description
        context = task.context

        analysis = {
            "problem_summary": self._extract_summary(description),
            "error_patterns": self._identify_error_patterns(description),
            "environment_info": context.get("environment", {}),
            "affected_components": self._identify_components(description),
            "time_spent": 0,
            "timestamp": datetime.now().isoformat()
        }

        return analysis

    def _extract_summary(self, description: str) -> str:
        """Extract a brief summary from problem description."""
        # Simple extraction - first sentence or first 100 chars
        lines = description.strip().split('\n')
        first_line = lines[0] if lines else description
        return first_line[:200] if len(first_line) > 200 else first_line

    def _identify_error_patterns(self, description: str) -> List[str]:
        """Identify error patterns in the description."""
        patterns = []

        # Common error patterns
        error_keywords = [
            ("ACL_ERROR", "ACL error"),
            ("NotImplementedError", "Missing implementation"),
            ("RuntimeError", "Runtime error"),
            ("assertion", "Assertion failure"),
            ("precision", "Precision issue"),
            ("SIGSEGV", "Segmentation fault"),
            ("compile", "Compilation error"),
            ("link", "Linking error"),
        ]

        desc_lower = description.lower()
        for keyword, label in error_keywords:
            if keyword.lower() in desc_lower:
                patterns.append(label)

        return patterns

    def _identify_components(self, description: str) -> List[str]:
        """Identify affected components."""
        components = []

        # Component indicators
        component_map = {
            "opapi": "ACLNN operator",
            "aclops": "ACL operator",
            "op-plugin": "Operator plugin",
            "csrc": "Framework layer",
            "format": "Format handling",
            "dtype": "Data type handling",
        }

        desc_lower = description.lower()
        for keyword, component in component_map.items():
            if keyword in desc_lower:
                components.append(component)

        return components if components else ["Unknown component"]

    def _classify_issue(self, analysis: Dict) -> Dict[str, Any]:
        """Classify the issue based on analysis.

        Args:
            analysis: Problem analysis results

        Returns:
            Dict with classification
        """
        patterns = analysis.get("error_patterns", [])
        components = analysis.get("affected_components", [])

        # Determine category
        if "ACL error" in patterns:
            category = "ACLNN_LAYER"
        elif "Missing implementation" in patterns:
            category = "REGISTRATION"
        elif "Precision issue" in patterns:
            category = "PRECISION"
        elif "Compilation error" in patterns:
            category = "COMPILATION"
        elif "Segmentation fault" in patterns:
            category = "RUNTIME"
        else:
            category = "GENERAL"

        # Determine priority
        if "Segmentation fault" in patterns or "Runtime error" in patterns:
            priority = "critical"
        elif "Precision issue" in patterns:
            priority = "high"
        else:
            priority = "normal"

        return {
            "category": category,
            "priority": priority,
            "patterns": patterns,
            "components": components,
            "complexity": self._estimate_complexity(patterns, components)
        }

    def _estimate_complexity(
        self,
        patterns: List[str],
        components: List[str]
    ) -> str:
        """Estimate issue complexity."""
        if len(patterns) > 2 or len(components) > 2:
            return "high"
        elif len(patterns) > 1 or len(components) > 1:
            return "medium"
        return "low"

    def _create_execution_plan(
        self,
        task: Task,
        analysis: Dict,
        classification: Dict
    ) -> ExecutionPlan:
        """Create an execution plan based on analysis.

        Args:
            task: The task
            analysis: Problem analysis
            classification: Issue classification

        Returns:
            ExecutionPlan
        """
        category = classification.get("category", "GENERAL")
        complexity = classification.get("complexity", "medium")

        # Define steps based on category
        steps = []

        # Always start with detailed analysis
        steps.append(ExecutionStep(
            step_id="1",
            description="Detailed error log analysis and root cause identification",
            role="executor.analyzer",
            estimated_duration=1800,  # 30 min
            dependencies=[]
        ))

        # Source location
        steps.append(ExecutionStep(
            step_id="2",
            description="Navigate to relevant source code files",
            role="executor.locator",
            estimated_duration=900,  # 15 min
            dependencies=["1"]
        ))

        # Fix implementation
        if category == "ACLNN_LAYER":
            steps.append(ExecutionStep(
                step_id="3",
                description="Implement ACLNN operator fix",
                role="executor.fixer",
                estimated_duration=3600 if complexity == "high" else 1800,
                dependencies=["2"]
            ))
        elif category == "REGISTRATION":
            steps.append(ExecutionStep(
                step_id="3",
                description="Add missing operator registration",
                role="executor.fixer",
                estimated_duration=1800,
                dependencies=["2"]
            ))
        elif category == "PRECISION":
            steps.append(ExecutionStep(
                step_id="3",
                description="Fix precision handling in operator",
                role="executor.fixer",
                estimated_duration=2700,
                dependencies=["2"]
            ))
        else:
            steps.append(ExecutionStep(
                step_id="3",
                description="Implement fix based on root cause",
                role="executor.fixer",
                estimated_duration=2700,
                dependencies=["2"]
            ))

        # Self-test
        steps.append(ExecutionStep(
            step_id="4",
            description="Self-test the fix locally",
            role="executor.tester",
            estimated_duration=1800,
            dependencies=["3"]
        ))

        # Evaluation
        steps.append(ExecutionStep(
            step_id="5",
            description="Code review and acceptance testing",
            role="evaluator",
            estimated_duration=1800,
            dependencies=["4"]
        ))

        # Calculate total estimated duration
        total_duration = sum(s.estimated_duration for s in steps)

        plan = ExecutionPlan(
            goal=f"Fix: {analysis.get('problem_summary', 'Unknown issue')}",
            steps=steps,
            acceptance_criteria=[],  # Will be filled separately
            risk_mitigation={}
        )

        # Set task metrics
        task.metrics.planned_duration = total_duration

        return plan

    def _define_acceptance_criteria(
        self,
        task: Task,
        classification: Dict
    ) -> List[str]:
        """Define acceptance criteria for the task.

        Args:
            task: The task
            classification: Issue classification

        Returns:
            List of acceptance criteria
        """
        category = classification.get("category", "GENERAL")

        # Base criteria
        criteria = [
            "Root cause clearly identified and documented",
            "Fix implemented with minimal code changes",
            "Code follows project coding standards",
            "All comments are in English",
        ]

        # Category-specific criteria
        if category == "PRECISION":
            criteria.extend([
                "NPU results match CPU/GPU within tolerance",
                "All precision test cases pass",
                "Boundary values tested",
            ])
        elif category == "COMPILATION":
            criteria.extend([
                "Code compiles without errors or warnings",
                "Linking succeeds",
                "ABI compatibility verified",
            ])
        elif category == "RUNTIME":
            criteria.extend([
                "No crashes or segfaults",
                "Memory usage is stable",
                "Async execution works correctly",
            ])

        # General criteria
        criteria.extend([
            "Regression tests pass",
            "New test cases added for the fix",
            "Documentation updated if needed",
        ])

        return criteria

    def _assess_risks(
        self,
        analysis: Dict,
        classification: Dict
    ) -> Dict[str, str]:
        """Assess risks and define mitigations.

        Args:
            analysis: Problem analysis
            classification: Issue classification

        Returns:
            Dict mapping risks to mitigations
        """
        risks = {}

        complexity = classification.get("complexity", "medium")
        components = classification.get("components", [])

        # Complexity risk
        if complexity == "high":
            risks["High complexity"] = "Break into smaller sub-tasks; engage expert if blocked"

        # Multi-component risk
        if len(components) > 1:
            risks["Cross-component impact"] = "Test all affected components thoroughly"

        # Precision risk
        if classification.get("category") == "PRECISION":
            risks["Precision trade-offs"] = "Document acceptable tolerance; test on multiple devices"

        # Compilation risk
        if classification.get("category") == "COMPILATION":
            risks["Version compatibility"] = "Test on all supported CANN/PyTorch versions"

        return risks

    def replan(self, task: Task, reason: str) -> ExecutionPlan:
        """Replan a task when the original plan needs adjustment.

        Args:
            task: The task to replan
            reason: Reason for replanning

        Returns:
            New execution plan
        """
        task.transition_to(TaskState.REPLANNING, self.name, reason)

        # Analyze current progress
        if task.plan:
            completed_steps = [s for s in task.plan.steps if s.completed]
            remaining_steps = [s for s in task.plan.steps if not s.completed]

        # Create adjusted plan
        analysis = self._analyze_problem(task)
        classification = self._classify_issue(analysis)

        # Adjust based on previous attempts
        task.metrics.revision_count += 1
        classification["complexity"] = "high"  # Increase complexity due to retry

        new_plan = self._create_execution_plan(task, analysis, classification)

        return new_plan
