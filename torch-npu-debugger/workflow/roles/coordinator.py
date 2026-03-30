# Coordinator role for workflow
# All comments in this file are in English per project guidelines

from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from collections import defaultdict

from workflow.roles.base import Role, RoleState
from workflow.models.task import Task, TaskState
from workflow.models.message import Message, MessageType


class Coordinator:
    """Coordinator manages role interactions and task flow.

    The coordinator is the central hub for:
    - Task assignment to roles
    - Message routing between roles
    - Conflict resolution
    - Resource allocation
    - Exception escalation
    """

    def __init__(self, engine=None):
        """Initialize coordinator."""
        self.engine = engine
        self.roles: Dict[str, Role] = {}
        self.pending_messages: List[Message] = []
        self.message_handlers: Dict[str, Callable] = {}
        self.task_assignments: Dict[str, str] = {}  # task_id -> role_name
        self.conflicts: List[Dict] = []

    def register_role(self, role: Role):
        """Register a role with the coordinator.

        Args:
            role: The role to register
        """
        self.roles[role.name] = role
        role.coordinator = self

    def assign_task(self, task: Task, role: Role) -> bool:
        """Assign a task to a role.

        Args:
            task: The task to assign
            role: The target role

        Returns:
            bool: True if assigned successfully
        """
        if role.name not in self.roles:
            return False

        # Update task tracking
        self.task_assignments[task.id] = role.name

        # Send assignment message
        message = Message.create_task_assign(
            from_role="coordinator",
            to_role=role.name,
            task_id=task.id,
            task_data=task.to_dict(),
            priority=task.priority
        )

        self.route_message(message)

        # Direct assignment
        accepted = role.receive_task(task)

        if accepted:
            task.current_role = role.name
            return True
        else:
            # Role rejected task, handle reassignment
            return self._handle_rejected_assignment(task, role)

    def route_message(self, message: Message):
        """Route a message to its destination.

        Args:
            message: The message to route
        """
        self.pending_messages.append(message)

        # Find target role
        target_role = self.roles.get(message.to_role)

        if target_role:
            # Deliver to role
            self._deliver_message(target_role, message)
        elif message.to_role == "coordinator":
            # Handle coordinator message
            self._handle_coordinator_message(message)
        else:
            # Unknown recipient, log error
            self._log_undelivered(message)

    def _deliver_message(self, role: Role, message: Message):
        """Deliver message to a role."""
        # Role would have message handling logic
        # For now, just track delivery
        message.payload["delivered_at"] = datetime.now().isoformat()

    def _handle_coordinator_message(self, message: Message):
        """Handle messages addressed to coordinator."""
        msg_type = message.message_type

        if msg_type == MessageType.TASK_BLOCK:
            self._handle_blocked_task(message)
        elif msg_type == MessageType.TASK_REJECT:
            self._handle_rejected_task(message)
        elif msg_type == MessageType.RESOURCE_REQUEST:
            self._handle_resource_request(message)
        elif msg_type == MessageType.CONFLICT_NOTIFY:
            self._handle_conflict(message)
        elif msg_type == MessageType.ESCALATE:
            self._handle_escalation(message)
        elif msg_type == MessageType.ALERT:
            self._handle_alert(message)

    def resolve_conflict(
        self,
        conflict: Dict,
        resolution: Optional[str] = None
    ) -> Dict[str, Any]:
        """Resolve a conflict between roles.

        Args:
            conflict: The conflict description
            resolution: Proposed resolution

        Returns:
            Resolution result
        """
        self.conflicts.append(conflict)

        # Simple arbitration logic
        conflict_type = conflict.get("type", "unknown")

        if conflict_type == "resource":
            return self._resolve_resource_conflict(conflict)
        elif conflict_type == "priority":
            return self._resolve_priority_conflict(conflict)
        else:
            return {
                "resolved": True,
                "resolution": resolution or "manual_arbitration_required",
                "action": "notify_user"
            }

    def escalate(self, issue: Dict, level: int = 1):
        """Escalate an issue.

        Args:
            issue: The issue to escalate
            level: Escalation level (1-4)
        """
        escalation_actions = {
            1: self._level1_escalation,
            2: self._level2_escalation,
            3: self._level3_escalation,
            4: self._level4_escalation,
        }

        handler = escalation_actions.get(level)
        if handler:
            handler(issue)

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get current status of a task.

        Args:
            task_id: The task ID

        Returns:
            Task status or None
        """
        if self.engine and task_id in self.engine.tasks:
            return self.engine.tasks[task_id].to_dict()
        return None

    def get_all_roles_status(self) -> Dict[str, Any]:
        """Get status of all registered roles.

        Returns:
            Dict mapping role names to statuses
        """
        return {
            name: role.report_status()
            for name, role in self.roles.items()
        }

    # Internal handlers

    def _handle_rejected_assignment(self, task: Task, role: Role) -> bool:
        """Handle when a role rejects a task assignment."""
        # Try to find alternative role
        for name, alt_role in self.roles.items():
            if name != role.name and alt_role.has_capability("execute"):
                return self.assign_task(task, alt_role)
        return False

    def _handle_blocked_task(self, message: Message):
        """Handle a blocked task."""
        task_id = message.task_id
        reason = message.payload.get("reason", "Unknown")

        # Notify relevant roles
        for role_name in ["planner", "monitor"]:
            if role_name in self.roles:
                self.send_message(
                    from_role="coordinator",
                    to_role=role_name,
                    message_type=MessageType.WARNING,
                    task_id=task_id,
                    payload={
                        "warning": f"Task blocked: {reason}",
                        "blocked_by": message.from_role
                    }
                )

    def _handle_rejected_task(self, message: Message):
        """Handle task rejection from evaluator."""
        task_id = message.task_id
        reason = message.payload.get("reason", "")
        feedback = message.payload.get("feedback", [])

        # Send back to executor for rework
        if "executor" in self.roles:
            self.send_message(
                from_role="coordinator",
                to_role="executor",
                message_type=MessageType.TASK_ASSIGN,
                task_id=task_id,
                payload={
                    "action": "rework",
                    "reason": reason,
                    "feedback": feedback
                },
                priority="high"
            )

    def _handle_resource_request(self, message: Message):
        """Handle resource request."""
        # Grant or deny resource
        resource_type = message.payload.get("resource_type")

        # Simple grant logic
        response = Message(
            from_role="coordinator",
            to_role=message.from_role,
            message_type=MessageType.RESOURCE_GRANT,
            task_id=message.task_id,
            payload={
                "resource_type": resource_type,
                "granted": True,
                "message": "Resource granted"
            },
            correlation_id=message.message_id
        )
        self.route_message(response)

    def _handle_conflict(self, message: Message):
        """Handle conflict notification."""
        conflict = message.payload
        resolution = self.resolve_conflict(conflict)

        # Notify involved parties
        for role_name in conflict.get("involved_roles", []):
            if role_name in self.roles:
                self.send_message(
                    from_role="coordinator",
                    to_role=role_name,
                    message_type=MessageType.CONFLICT_RESOLVED,
                    task_id=message.task_id,
                    payload=resolution
                )

    def _handle_escalation(self, message: Message):
        """Handle escalation message."""
        issue = message.payload
        level = issue.get("level", 1)

        self.escalate(issue, level)

    def _handle_alert(self, message: Message):
        """Handle alert message."""
        alert = message.payload
        severity = alert.get("severity", "warning")

        if severity == "critical":
            # Auto-escalate critical alerts
            self.escalate(alert, level=2)

    def _resolve_resource_conflict(self, conflict: Dict) -> Dict:
        """Resolve resource conflict."""
        # Simple priority-based resolution
        competing = conflict.get("competing_tasks", [])
        if len(competing) >= 2:
            # Higher priority wins
            winner = max(competing, key=lambda x: x.get("priority", 0))
            return {
                "resolved": True,
                "winner": winner["task_id"],
                "resolution": "priority_based"
            }
        return {"resolved": False, "reason": "no_competition"}

    def _resolve_priority_conflict(self, conflict: Dict) -> Dict:
        """Resolve priority conflict."""
        return {
            "resolved": True,
            "resolution": "maintain_existing_priority",
            "message": "First come first served"
        }

    def _level1_escalation(self, issue: Dict):
        """Level 1: Role internal."""
        # Handled within role
        pass

    def _level2_escalation(self, issue: Dict):
        """Level 2: Coordinator intervention."""
        # Coordinator handles
        pass

    def _level3_escalation(self, issue: Dict):
        """Level 3: Planner replanning."""
        task_id = issue.get("task_id")
        if task_id and self.engine:
            task = self.engine.tasks.get(task_id)
            if task and "planner" in self.roles:
                self.assign_task(task, self.roles["planner"])

    def _level4_escalation(self, issue: Dict):
        """Level 4: User notification."""
        # Would notify user
        pass

    def _log_undelivered(self, message: Message):
        """Log undelivered message."""
        print(f"Undelivered message to {message.to_role}: {message.message_type.value}")

    def send_message(
        self,
        from_role: str,
        to_role: str,
        message_type: MessageType,
        task_id: Optional[str] = None,
        payload: Optional[Dict] = None,
        priority: str = "normal"
    ) -> Message:
        """Send a message."""
        message = Message(
            from_role=from_role,
            to_role=to_role,
            message_type=message_type,
            task_id=task_id,
            payload=payload or {},
            priority=priority
        )
        self.route_message(message)
        return message
