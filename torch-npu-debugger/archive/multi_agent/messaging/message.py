# Message definitions for multi-agent system
# All comments in this file are in English per project guidelines

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional
import json
import uuid


class MessageType(Enum):
    """Types of messages between agents."""
    # Task lifecycle
    TASK_CREATE = "task.create"
    TASK_ASSIGN = "task.assign"
    TASK_START = "task.start"
    TASK_PROGRESS = "task.progress"
    TASK_COMPLETE = "task.complete"
    TASK_FAIL = "task.fail"
    TASK_BLOCK = "task.block"

    # Agent coordination
    AGENT_REGISTER = "agent.register"
    AGENT_HEARTBEAT = "agent.heartbeat"
    AGENT_STATUS = "agent.status"
    AGENT_SHUTDOWN = "agent.shutdown"

    # Data exchange
    ANALYSIS_RESULT = "data.analysis"
    SCOPE_RESULT = "data.scope"
    LOCATION_RESULT = "data.location"
    FIX_RESULT = "data.fix"
    VERIFY_RESULT = "data.verify"
    ARCHIVE_RESULT = "data.archive"

    # Control
    COMMAND = "control.command"
    QUERY = "control.query"
    RESPONSE = "control.response"

    # Remote operations
    REMOTE_STATUS = "remote.status"
    REMOTE_PROGRESS = "remote.progress"
    ENV_INFO = "remote.env_info"


@dataclass
class Message:
    """Base message class for inter-agent communication."""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message_type: MessageType = MessageType.COMMAND
    sender: str = ""
    recipient: str = ""  # Empty for broadcast
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None
    priority: int = 0  # Higher = more urgent

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "message_id": self.message_id,
            "message_type": self.message_type.value,
            "sender": self.sender,
            "recipient": self.recipient,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "priority": self.priority,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create message from dictionary."""
        return cls(
            message_id=data["message_id"],
            message_type=MessageType(data["message_type"]),
            sender=data["sender"],
            recipient=data["recipient"],
            payload=data["payload"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            correlation_id=data.get("correlation_id"),
            priority=data.get("priority", 0),
        )

    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_json(cls, json_str: str) -> 'Message':
        """Deserialize from JSON."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class TaskMessage(Message):
    """Specialized message for task-related communication."""
    task_id: str = ""
    task_state: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert task message to dictionary."""
        base = super().to_dict()
        base["task_id"] = self.task_id
        base["task_state"] = self.task_state
        return base

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskMessage':
        """Create task message from dictionary."""
        msg = cls(
            message_id=data["message_id"],
            message_type=MessageType(data["message_type"]),
            sender=data["sender"],
            recipient=data["recipient"],
            payload=data["payload"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            correlation_id=data.get("correlation_id"),
            priority=data.get("priority", 0),
            task_id=data.get("task_id", ""),
            task_state=data.get("task_state", ""),
        )
        return msg


class MessageHandler:
    """Interface for message handlers."""

    def can_handle(self, message: Message) -> bool:
        """Check if this handler can process the message."""
        raise NotImplementedError

    def handle(self, message: Message) -> Optional[Message]:
        """Handle the message and optionally return a response."""
        raise NotImplementedError
