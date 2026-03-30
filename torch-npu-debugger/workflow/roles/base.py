# Base class for workflow roles
# All comments in this file are in English per project guidelines

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from workflow.models.task import Task, RoleState, TaskState
from workflow.models.message import Message, MessageType


class RoleCapability:
    """Capabilities that a role can have."""
    ANALYZE = "analyze"
    PLAN = "plan"
    EXECUTE = "execute"
    EVALUATE = "evaluate"
    ARCHIVE = "archive"
    MONITOR = "monitor"
    COORDINATE = "coordinate"


class Role(ABC):
    """Abstract base class for workflow roles.

    All roles in the workflow system must inherit from this class
    and implement the required abstract methods.
    """

    def __init__(self, name: str, coordinator: "Coordinator"):
        """Initialize the role.

        Args:
            name: Unique name for this role instance
            coordinator: Reference to the coordinator for messaging
        """
        self.name = name
        self.coordinator = coordinator
        self.state = RoleState.IDLE
        self.current_task: Optional[Task] = None
        self.capabilities: List[str] = []
        self.metrics: Dict[str, Any] = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "total_work_time": 0,
        }

    @abstractmethod
    def receive_task(self, task: Task) -> bool:
        """Receive a task for execution.

        Args:
            task: The task to execute

        Returns:
            bool: True if task was accepted, False otherwise
        """
        pass

    @abstractmethod
    def execute(self, task: Task) -> Dict[str, Any]:
        """Execute the assigned task.

        Args:
            task: The task to execute

        Returns:
            Dict containing execution results
        """
        pass

    def report_status(self) -> Dict[str, Any]:
        """Report current status.

        Returns:
            Dict containing status information
        """
        return {
            "role": self.name,
            "state": self.state.value,
            "current_task": self.current_task.id if self.current_task else None,
            "capabilities": self.capabilities,
            "metrics": self.metrics,
        }

    def send_message(
        self,
        to_role: str,
        message_type: MessageType,
        payload: Dict[str, Any],
        requires_response: bool = False,
        priority: str = "normal"
    ) -> Message:
        """Send a message to another role via coordinator.

        Args:
            to_role: Name of the target role
            message_type: Type of message
            payload: Message payload
            requires_response: Whether a response is required
            priority: Message priority

        Returns:
            The sent message
        """
        message = Message(
            from_role=self.name,
            to_role=to_role,
            message_type=message_type,
            task_id=self.current_task.id if self.current_task else None,
            payload=payload,
            requires_response=requires_response,
            priority=priority
        )
        self.coordinator.route_message(message)
        return message

    def request_resource(self, resource_type: str, details: Dict[str, Any]) -> bool:
        """Request a resource from the coordinator.

        Args:
            resource_type: Type of resource needed
            details: Resource details

        Returns:
            bool: True if resource was granted
        """
        message = self.send_message(
            to_role="coordinator",
            message_type=MessageType.RESOURCE_REQUEST,
            payload={
                "resource_type": resource_type,
                "details": details
            },
            requires_response=True
        )
        # In async implementation, would wait for response
        return True

    def report_block(self, reason: str, details: Optional[Dict] = None):
        """Report that the role is blocked.

        Args:
            reason: Reason for being blocked
            details: Additional details
        """
        self.state = RoleState.BLOCKED
        if self.current_task:
            self.current_task.blocked_reason = reason
            self.current_task.transition_to(
                TaskState.BLOCKED,
                self.name,
                reason
            )

        self.send_message(
            to_role="coordinator",
            message_type=MessageType.TASK_BLOCK,
            payload={
                "reason": reason,
                "details": details or {}
            },
            priority="high"
        )

    def report_progress(self, progress: float, message: str = ""):
        """Report progress on current task.

        Args:
            progress: Progress percentage (0-100)
            message: Progress message
        """
        self.send_message(
            to_role="coordinator",
            message_type=MessageType.PROGRESS_UPDATE,
            payload={
                "progress": progress,
                "message": message,
                "timestamp": datetime.now().isoformat()
            }
        )

    def complete_task(self, deliverables: List[Dict], metrics: Dict[str, Any]):
        """Complete the current task.

        Args:
            deliverables: List of deliverables produced
            metrics: Task metrics
        """
        if not self.current_task:
            return

        self.state = RoleState.COMPLETED
        self.metrics["tasks_completed"] += 1

        # Send completion message
        self.send_message(
            to_role="coordinator",
            message_type=MessageType.TASK_COMPLETE,
            payload={
                "deliverables": deliverables,
                "metrics": metrics
            }
        )

    def has_capability(self, capability: str) -> bool:
        """Check if role has a specific capability.

        Args:
            capability: Capability to check

        Returns:
            bool: True if role has the capability
        """
        return capability in self.capabilities

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', state={self.state.value})"
