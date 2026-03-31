# Message models for inter-role communication
# All comments in this file are in English per project guidelines

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, Optional
import uuid


class MessageType(Enum):
    """Types of messages between roles."""
    # Task lifecycle
    TASK_ASSIGN = "task_assign"
    TASK_ACCEPT = "task_accept"
    TASK_COMPLETE = "task_complete"
    TASK_REJECT = "task_reject"
    TASK_BLOCK = "task_block"
    TASK_UNBLOCK = "task_unblock"

    # Status and progress
    STATUS_QUERY = "status_query"
    STATUS_REPORT = "status_report"
    PROGRESS_UPDATE = "progress_update"

    # Alerts and notifications
    ALERT = "alert"
    WARNING = "warning"
    INFO = "info"

    # Coordination
    RESOURCE_REQUEST = "resource_request"
    RESOURCE_GRANT = "resource_grant"
    CONFLICT_NOTIFY = "conflict_notify"
    CONFLICT_RESOLVED = "conflict_resolved"

    # Escalation
    ESCALATE = "escalate"
    DEESCALATE = "deescalate"


@dataclass
class Message:
    """Message for inter-role communication."""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: datetime = field(default_factory=datetime.now)
    from_role: str = ""
    to_role: str = ""
    message_type: MessageType = MessageType.INFO
    task_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    requires_response: bool = False
    priority: str = "normal"  # low, normal, high, critical
    correlation_id: Optional[str] = None  # Link to related message

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "message_id": self.message_id,
            "timestamp": self.timestamp.isoformat(),
            "from": self.from_role,
            "to": self.to_role,
            "type": self.message_type.value,
            "task_id": self.task_id,
            "payload": self.payload,
            "requires_response": self.requires_response,
            "priority": self.priority,
            "correlation_id": self.correlation_id,
        }

    @classmethod
    def create_task_assign(
        cls,
        from_role: str,
        to_role: str,
        task_id: str,
        task_data: Dict[str, Any],
        priority: str = "normal"
    ) -> "Message":
        """Create a task assignment message."""
        return cls(
            from_role=from_role,
            to_role=to_role,
            message_type=MessageType.TASK_ASSIGN,
            task_id=task_id,
            payload={"task": task_data},
            requires_response=True,
            priority=priority
        )

    @classmethod
    def create_task_complete(
        cls,
        from_role: str,
        to_role: str,
        task_id: str,
        deliverables: list,
        metrics: Dict[str, Any]
    ) -> "Message":
        """Create a task completion message."""
        return cls(
            from_role=from_role,
            to_role=to_role,
            message_type=MessageType.TASK_COMPLETE,
            task_id=task_id,
            payload={
                "deliverables": deliverables,
                "metrics": metrics
            },
            requires_response=False
        )

    @classmethod
    def create_alert(
        cls,
        from_role: str,
        to_role: str,
        task_id: Optional[str],
        alert_type: str,
        message: str,
        level: str = "warning"
    ) -> "Message":
        """Create an alert message."""
        return cls(
            from_role=from_role,
            to_role=to_role,
            message_type=MessageType.ALERT,
            task_id=task_id,
            payload={
                "alert_type": alert_type,
                "message": message,
                "level": level
            },
            priority="high" if level in ("critical", "high") else "normal"
        )

    @classmethod
    def create_status_report(
        cls,
        from_role: str,
        to_role: str,
        task_id: str,
        status: str,
        progress: float,
        details: Optional[Dict] = None
    ) -> "Message":
        """Create a status report message."""
        return cls(
            from_role=from_role,
            to_role=to_role,
            message_type=MessageType.STATUS_REPORT,
            task_id=task_id,
            payload={
                "status": status,
                "progress": progress,
                "details": details or {}
            },
            requires_response=False
        )
