# Base agent class for multi-agent system
# All comments in this file are in English per project guidelines

import os
import sys
import time
import signal
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set
from multiprocessing import Process, Queue as MPQueue
from threading import Thread, Lock, Event
import queue

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ..messaging import MessageBus, Message, MessageType, create_message_bus


class AgentState(Enum):
    """States for agent lifecycle."""
    INIT = "initialized"
    STARTING = "starting"
    IDLE = "idle"
    WORKING = "working"
    BLOCKED = "blocked"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class AgentCapability(Enum):
    """Capabilities that agents can have."""
    ANALYZE = "analyze"
    SCOPE = "scope"
    LOCATE = "locate"
    FIX = "fix"
    VERIFY = "verify"
    ARCHIVE = "archive"
    COORDINATE = "coordinate"
    MONITOR = "monitor"
    PLAN = "plan"
    EXECUTE = "execute"
    EVALUATE = "evaluate"


@dataclass
class AgentMetrics:
    """Metrics for agent performance tracking."""
    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_blocked: int = 0
    total_work_time: float = 0.0
    messages_sent: int = 0
    messages_received: int = 0
    errors: List[Dict] = field(default_factory=list)
    start_time: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None


class Agent(ABC):
    """Abstract base class for all agents in the multi-agent system.

    Each agent runs in its own process and communicates via message bus.
    """

    def __init__(
        self,
        agent_id: str,
        capabilities: List[AgentCapability],
        message_bus: Optional[MessageBus] = None,
        heartbeat_interval: float = 5.0
    ):
        """Initialize agent.

        Args:
            agent_id: Unique identifier for this agent.
            capabilities: List of capabilities this agent has.
            message_bus: Message bus for communication (created if None).
            heartbeat_interval: Seconds between heartbeats.
        """
        self.agent_id = agent_id
        self.capabilities = set(capabilities)
        self.message_bus = message_bus or create_message_bus("file")
        self.heartbeat_interval = heartbeat_interval

        self.state = AgentState.INIT
        self.metrics = AgentMetrics()
        self.current_task: Optional[str] = None
        self.task_history: List[str] = []

        # Internal state
        self._lock = Lock()
        self._stop_event = Event()
        self._heartbeat_thread: Optional[Thread] = None
        self._message_thread: Optional[Thread] = None
        self._message_queue: queue.Queue = queue.Queue()

        # Task handlers
        self._task_handlers: Dict[str, Callable[[str, Dict], Dict]] = {}
        self._register_default_handlers()

        # Setup logging
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Setup agent-specific logger."""
        logger = logging.getLogger(f"Agent.{self.agent_id}")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                f'[%(asctime)s] [{self.agent_id}] %(levelname)s: %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def _register_default_handlers(self):
        """Register default message handlers."""
        self._task_handlers[MessageType.AGENT_SHUTDOWN.value] = self._handle_shutdown
        self._task_handlers[MessageType.QUERY.value] = self._handle_query

    def _handle_shutdown(self, task_id: str, payload: Dict) -> Dict:
        """Handle shutdown request."""
        self.logger.info("Received shutdown request")
        self.stop()
        return {"status": "shutting_down"}

    def _handle_query(self, task_id: str, payload: Dict) -> Dict:
        """Handle status query."""
        return {
            "agent_id": self.agent_id,
            "state": self.state.value,
            "capabilities": [c.value for c in self.capabilities],
            "current_task": self.current_task,
            "metrics": {
                "tasks_completed": self.metrics.tasks_completed,
                "tasks_failed": self.metrics.tasks_failed,
                "uptime": self._get_uptime(),
            }
        }

    def _get_uptime(self) -> float:
        """Get agent uptime in seconds."""
        if self.metrics.start_time:
            return (datetime.now() - self.metrics.start_time).total_seconds()
        return 0.0

    def _on_message(self, message: Message):
        """Callback for incoming messages."""
        self.metrics.messages_received += 1

        # Filter messages not intended for this agent
        if message.recipient and message.recipient != self.agent_id:
            return

        self._message_queue.put(message)

    def _process_messages(self):
        """Process messages from queue."""
        while not self._stop_event.is_set():
            try:
                message = self._message_queue.get(timeout=0.5)
                self._handle_message(message)
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error processing message: {e}")
                self._record_error("message_processing", str(e))

    def _handle_message(self, message: Message):
        """Handle a single message."""
        handler = self._task_handlers.get(message.message_type.value)

        if handler:
            try:
                self.logger.debug(f"Handling {message.message_type.value} from {message.sender}")
                result = handler(message.payload.get("task_id", ""), message.payload)

                # Send response if requested
                if message.correlation_id:
                    self.send_message(
                        recipient=message.sender,
                        message_type=MessageType.RESPONSE,
                        payload={
                            "correlation_id": message.correlation_id,
                            "result": result
                        }
                    )
            except Exception as e:
                self.logger.error(f"Handler error: {e}")
                self._record_error("handler", str(e))
        else:
            # Try specialized handler
            self._handle_specialized(message)

    @abstractmethod
    def _handle_specialized(self, message: Message):
        """Handle agent-specific messages. Override in subclasses."""
        pass

    def _record_error(self, error_type: str, message: str):
        """Record an error."""
        with self._lock:
            self.metrics.errors.append({
                "type": error_type,
                "message": message,
                "timestamp": datetime.now().isoformat()
            })

    def _send_heartbeat(self):
        """Send heartbeat message."""
        while not self._stop_event.is_set():
            try:
                self.message_bus.broadcast(
                    sender=self.agent_id,
                    message_type=MessageType.AGENT_HEARTBEAT,
                    payload={
                        "agent_id": self.agent_id,
                        "state": self.state.value,
                        "capabilities": [c.value for c in self.capabilities],
                        "current_task": self.current_task,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                self.metrics.last_heartbeat = datetime.now()
                self._stop_event.wait(self.heartbeat_interval)
            except Exception as e:
                self.logger.error(f"Heartbeat error: {e}")
                self._stop_event.wait(1)

    def send_message(
        self,
        recipient: str,
        message_type: MessageType,
        payload: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> bool:
        """Send a message to another agent."""
        try:
            message = Message(
                sender=self.agent_id,
                recipient=recipient,
                message_type=message_type,
                payload=payload,
                correlation_id=correlation_id
            )
            result = self.message_bus.publish(message)
            if result:
                self.metrics.messages_sent += 1
            return result
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            return False

    def register_handler(self, message_type: MessageType, handler: Callable[[str, Dict], Dict]):
        """Register a handler for a specific message type."""
        self._task_handlers[message_type.value] = handler

    def report_progress(self, progress: float, message: str = ""):
        """Report task progress.

        Args:
            progress: Progress percentage (0-100)
            message: Progress message
        """
        self.logger.info(f"Progress: {progress:.1f}% - {message}")

        # Send progress message if we have a current task
        if self.current_task:
            self.send_message(
                recipient="coordinator",
                message_type=MessageType.TASK_PROGRESS,
                payload={
                    "agent_id": self.agent_id,
                    "task_id": self.current_task,
                    "progress": progress,
                    "message": message
                }
            )

    def report_block(self, reason: str, details: Dict = None):
        """Report task blockage.

        Args:
            reason: Reason for blockage
            details: Additional details
        """
        self.logger.warning(f"Task blocked: {reason}")

        if self.current_task:
            self.send_message(
                recipient="coordinator",
                message_type=MessageType.TASK_BLOCK,
                payload={
                    "agent_id": self.agent_id,
                    "task_id": self.current_task,
                    "reason": reason,
                    "details": details or {}
                }
            )

    def start(self) -> bool:
        """Start the agent."""
        try:
            self.logger.info(f"Starting agent {self.agent_id}")
            self.state = AgentState.STARTING

            # Start message bus
            self.message_bus.start()

            # Subscribe to messages
            self.message_bus.subscribe(self.agent_id, self._on_message)

            # Start heartbeat thread
            self._heartbeat_thread = Thread(target=self._send_heartbeat, daemon=True)
            self._heartbeat_thread.start()

            # Start message processing thread
            self._message_thread = Thread(target=self._process_messages, daemon=True)
            self._message_thread.start()

            # Register with coordinator
            self.message_bus.broadcast(
                sender=self.agent_id,
                message_type=MessageType.AGENT_REGISTER,
                payload={
                    "agent_id": self.agent_id,
                    "capabilities": [c.value for c in self.capabilities]
                }
            )

            self.metrics.start_time = datetime.now()
            self.state = AgentState.IDLE
            self.logger.info(f"Agent {self.agent_id} started successfully")

            return True
        except Exception as e:
            self.logger.error(f"Failed to start agent: {e}")
            self.state = AgentState.ERROR
            return False

    def stop(self):
        """Stop the agent."""
        self.logger.info(f"Stopping agent {self.agent_id}")
        self.state = AgentState.STOPPING
        self._stop_event.set()

        # Stop threads
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=2)

        if self._message_thread and self._message_thread.is_alive():
            self._message_thread.join(timeout=2)

        # Stop message bus
        self.message_bus.stop()

        self.state = AgentState.STOPPED
        self.logger.info(f"Agent {self.agent_id} stopped")

    def run(self):
        """Main run loop. Blocks until stopped."""
        if not self.start():
            return False

        try:
            # Run agent-specific logic
            self._run()
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        finally:
            self.stop()

        return True

    @abstractmethod
    def _run(self):
        """Agent-specific run logic. Override in subclasses."""
        # Default: just wait for stop signal
        while not self._stop_event.is_set():
            self._stop_event.wait(1)

    def transition_to(self, new_state: AgentState, reason: str = ""):
        """Transition to a new state."""
        old_state = self.state
        self.state = new_state
        self.logger.info(f"State transition: {old_state.value} -> {new_state.value} ({reason})")

    def __repr__(self) -> str:
        return f"Agent({self.agent_id}, state={self.state.value}, capabilities={[c.value for c in self.capabilities]})"
