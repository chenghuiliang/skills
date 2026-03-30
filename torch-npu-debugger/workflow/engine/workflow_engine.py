# Workflow engine for orchestrating multi-role tasks
from typing import Dict, Any, Optional
from workflow.models.task import Task, TaskState
from workflow.roles.planner import Planner
from workflow.roles.executor import Executor
from workflow.roles.evaluator import Evaluator
from workflow.roles.coordinator import Coordinator
from workflow.roles.monitor import Monitor

class WorkflowEngine:
    """Main workflow engine that orchestrates task execution."""
    def __init__(self):
        self.coordinator = Coordinator(self)
        self.planner = Planner(self.coordinator)
        self.executor = Executor(self.coordinator)
        self.evaluator = Evaluator(self.coordinator)
        self.monitor = Monitor(self.coordinator)
        self.tasks: Dict[str, Task] = {}
        self.coordinator.register_role(self.planner)
        self.coordinator.register_role(self.executor)
        self.coordinator.register_role(self.evaluator)
        self.coordinator.register_role(self.monitor)

    def process_issue(self, title: str, description: str, **kwargs) -> Task:
        """Start processing a new issue."""
        import uuid
        task = Task(
            id=str(uuid.uuid4())[:8],
            title=title,
            description=description,
            context=kwargs
        )
        self.tasks[task.id] = task
        # Start planning
        self.coordinator.assign_task(task, self.planner)
        return task

    def get_status(self, task_id: str) -> Dict[str, Any]:
        """Get task status."""
        task = self.tasks.get(task_id)
        return task.to_dict() if task else {}

    def execute_step(self, task_id: str) -> bool:
        """Execute next step for a task."""
        task = self.tasks.get(task_id)
        if not task:
            return False

        if task.state == TaskState.PLANNING:
            result = self.planner.execute(task)
            if result.get("success"):
                task.plan = result.get("plan")
                task.transition_to(TaskState.EXECUTING, "engine", "Planning complete")
                self.coordinator.assign_task(task, self.executor)
            return result.get("success", False)

        elif task.state == TaskState.EXECUTING:
            result = self.executor.execute(task)
            if result.get("success"):
                task.transition_to(TaskState.EVALUATING, "engine", "Execution complete")
                self.coordinator.assign_task(task, self.evaluator)
            return result.get("success", False)

        elif task.state == TaskState.EVALUATING:
            result = self.evaluator.execute(task)
            return result.get("success", False)

        return False
