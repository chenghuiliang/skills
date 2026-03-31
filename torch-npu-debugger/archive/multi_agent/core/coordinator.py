# Coordinator agent for multi-agent system
# All comments in this file are in English per project guidelines

import os
import sys
import time
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict
import queue

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ..messaging import Message, MessageType, MessageBus, create_message_bus
from .agent_base import Agent, AgentCapability, AgentState


@dataclass
class TaskAssignment:
    """Assignment of a task to an agent."""
    task_id: str
    agent_id: str
    assigned_at: datetime
    expected_duration: int
    completed: bool = False


@dataclass
class PendingTask:
    """Task waiting to be assigned."""
    task_id: str
    task_type: str
    payload: Dict[str, Any]
    priority: int
    required_capabilities: List[str]
    created_at: datetime


class CoordinatorAgent(Agent):
    """Coordinator agent that orchestrates the multi-agent workflow.

    The coordinator:
    - Maintains registry of all agents and their capabilities
    - Assigns tasks to appropriate agents
    - Monitors task progress and handles failures
    - Manages the overall workflow state
    """

    def __init__(
        self,
        agent_id: str = "coordinator",
        message_bus: Optional[MessageBus] = None,
        heartbeat_timeout: float = 15.0
    ):
        """Initialize coordinator agent.

        Args:
            agent_id: Coordinator identifier.
            message_bus: Message bus for communication.
            heartbeat_timeout: Seconds before considering agent dead.
        """
        super().__init__(
            agent_id=agent_id,
            capabilities=[AgentCapability.COORDINATE, AgentCapability.MONITOR],
            message_bus=message_bus,
            heartbeat_interval=2.0
        )

        self.heartbeat_timeout = heartbeat_timeout

        # Agent registry
        self.registered_agents: Dict[str, Dict[str, Any]] = {}
        self.agent_heartbeats: Dict[str, datetime] = {}
        self.agent_capabilities: Dict[str, Set[str]] = defaultdict(set)

        # Task management
        self.pending_tasks: queue.PriorityQueue = queue.PriorityQueue()
        self.active_assignments: Dict[str, TaskAssignment] = {}
        self.task_history: List[Dict] = []

        # Workflow state
        self.workflow_state: Dict[str, Any] = {}
        self.current_issue: Optional[Dict] = None

        # Register handlers
        self._register_handlers()

    def _register_handlers(self):
        """Register message handlers for coordination."""
        self.register_handler(MessageType.AGENT_REGISTER, self._handle_agent_register)
        self.register_handler(MessageType.AGENT_HEARTBEAT, self._handle_agent_heartbeat)
        self.register_handler(MessageType.TASK_CREATE, self._handle_task_create)
        self.register_handler(MessageType.TASK_COMPLETE, self._handle_task_complete)
        self.register_handler(MessageType.TASK_FAIL, self._handle_task_fail)
        self.register_handler(MessageType.TASK_BLOCK, self._handle_task_block)
        self.register_handler(MessageType.TASK_PROGRESS, self._handle_task_progress)

    def _handle_specialized(self, message: Message):
        """Handle specialized messages not covered by registered handlers."""
        self.logger.debug(f"Unhandled message type: {message.message_type.value}")

    def _handle_agent_register(self, task_id: str, payload: Dict) -> Dict:
        """Handle agent registration."""
        agent_id = payload.get("agent_id")
        capabilities = payload.get("capabilities", [])

        self.registered_agents[agent_id] = {
            "agent_id": agent_id,
            "capabilities": capabilities,
            "registered_at": datetime.now().isoformat(),
            "status": "active"
        }
        self.agent_heartbeats[agent_id] = datetime.now()
        self.agent_capabilities[agent_id] = set(capabilities)

        self.logger.info(f"Agent registered: {agent_id} with capabilities {capabilities}")

        return {"status": "registered", "coordinator": self.agent_id}

    def _handle_agent_heartbeat(self, task_id: str, payload: Dict) -> Dict:
        """Handle agent heartbeat."""
        agent_id = payload.get("agent_id")

        if agent_id in self.registered_agents:
            self.agent_heartbeats[agent_id] = datetime.now()
            self.registered_agents[agent_id]["status"] = payload.get("state", "unknown")
            self.registered_agents[agent_id]["current_task"] = payload.get("current_task")

        return {"received": True}

    def _handle_task_create(self, task_id: str, payload: Dict) -> Dict:
        """Handle new task creation."""
        task_type = payload.get("task_type", "unknown")
        priority = payload.get("priority", 0)
        required_caps = payload.get("required_capabilities", [])

        pending = PendingTask(
            task_id=task_id,
            task_type=task_type,
            payload=payload,
            priority=priority,
            required_capabilities=required_caps,
            created_at=datetime.now()
        )

        # Add to queue (lower priority number = higher priority)
        self.pending_tasks.put((-priority, datetime.now().timestamp(), pending))

        self.logger.info(f"Task created: {task_id} (type={task_type}, priority={priority})")

        # Try to assign immediately
        self._assign_pending_tasks()

        return {"status": "queued", "task_id": task_id}

    def _handle_task_complete(self, task_id: str, payload: Dict) -> Dict:
        """Handle task completion."""
        agent_id = payload.get("agent_id")
        result = payload.get("result", {})

        if task_id in self.active_assignments:
            assignment = self.active_assignments[task_id]
            assignment.completed = True

            self.task_history.append({
                "task_id": task_id,
                "agent_id": agent_id,
                "status": "completed",
                "completed_at": datetime.now().isoformat(),
                "result_summary": str(result)[:200]
            })

            del self.active_assignments[task_id]
            self.logger.info(f"Task completed: {task_id} by {agent_id}")

            # Trigger next step in workflow
            self._trigger_next_step(task_id, result)

        return {"acknowledged": True}

    def _handle_task_fail(self, task_id: str, payload: Dict) -> Dict:
        """Handle task failure."""
        agent_id = payload.get("agent_id")
        error = payload.get("error", "Unknown error")

        self.logger.error(f"Task failed: {task_id} by {agent_id}: {error}")

        if task_id in self.active_assignments:
            assignment = self.active_assignments[task_id]

            self.task_history.append({
                "task_id": task_id,
                "agent_id": agent_id,
                "status": "failed",
                "error": error,
                "failed_at": datetime.now().isoformat()
            })

            del self.active_assignments[task_id]

            # Retry logic
            retry_count = payload.get("retry_count", 0)
            if retry_count < 3:
                self.logger.info(f"Retrying task {task_id} (attempt {retry_count + 1})")
                # Re-queue with higher priority
                self._handle_task_create(task_id, {
                    **payload,
                    "retry_count": retry_count + 1,
                    "priority": 10  # High priority for retries
                })

        return {"acknowledged": True}

    def _handle_task_block(self, task_id: str, payload: Dict) -> Dict:
        """Handle blocked task."""
        agent_id = payload.get("agent_id")
        reason = payload.get("reason", "Unknown")

        self.logger.warning(f"Task blocked: {task_id} by {agent_id}: {reason}")

        # Notify planner or escalate
        self.send_message(
            recipient="planner",
            message_type=MessageType.ESCALATE,
            payload={
                "task_id": task_id,
                "blocked_by": agent_id,
                "reason": reason,
                "action": "replan"
            }
        )

        return {"escalated": True}

    def _handle_task_progress(self, task_id: str, payload: Dict) -> Dict:
        """Handle task progress update."""
        progress = payload.get("progress", 0)
        message = payload.get("message", "")

        self.logger.debug(f"Task {task_id} progress: {progress}% - {message}")

        return {"received": True}

    def _assign_pending_tasks(self):
        """Assign pending tasks to available agents."""
        while not self.pending_tasks.empty():
            try:
                _, _, pending = self.pending_tasks.get_nowait()

                # Find suitable agent
                agent_id = self._find_suitable_agent(pending.required_capabilities)

                if agent_id:
                    self._assign_task_to_agent(pending, agent_id)
                else:
                    # No suitable agent, put back
                    self.pending_tasks.put((-pending.priority, datetime.now().timestamp(), pending))
                    break

            except queue.Empty:
                break

    def _find_suitable_agent(self, required_capabilities: List[str]) -> Optional[str]:
        """Find an agent with required capabilities that is not busy."""
        now = datetime.now()

        for agent_id, capabilities in self.agent_capabilities.items():
            # Check heartbeat
            last_heartbeat = self.agent_heartbeats.get(agent_id)
            if last_heartbeat and (now - last_heartbeat).total_seconds() > self.heartbeat_timeout:
                continue

            # Check capabilities
            if not all(cap in capabilities for cap in required_capabilities):
                continue

            # Check if agent is busy
            agent_info = self.registered_agents.get(agent_id, {})
            if agent_info.get("current_task"):
                continue

            return agent_id

        return None

    def _assign_task_to_agent(self, pending: PendingTask, agent_id: str):
        """Assign a task to an agent."""
        assignment = TaskAssignment(
            task_id=pending.task_id,
            agent_id=agent_id,
            assigned_at=datetime.now(),
            expected_duration=pending.payload.get("estimated_duration", 3600)
        )

        self.active_assignments[pending.task_id] = assignment

        self.send_message(
            recipient=agent_id,
            message_type=MessageType.TASK_ASSIGN,
            payload={
                "task_id": pending.task_id,
                "task_type": pending.task_type,
                "payload": pending.payload
            }
        )

        self.logger.info(f"Assigned task {pending.task_id} to {agent_id}")

    def _trigger_next_step(self, completed_task_id: str, result: Dict):
        """Trigger the next step in the workflow based on completed task."""
        # Determine next step based on workflow
        workflow_step = result.get("workflow_step")

        next_steps = {
            "analysis": ("scoping", [AgentCapability.SCOPE.value]),
            "scoping": ("location", [AgentCapability.LOCATE.value]),
            "location": ("fix", [AgentCapability.FIX.value]),
            "fix": ("verify", [AgentCapability.VERIFY.value]),
            "execution": ("verify", [AgentCapability.VERIFY.value]),  # Executor completion triggers verify
            "verify": ("evaluate", [AgentCapability.EVALUATE.value]),  # Verify triggers evaluate
            "evaluation": ("archive", [AgentCapability.ARCHIVE.value]),  # Evaluate triggers archive
        }

        if workflow_step and workflow_step in next_steps:
            next_step_type, required_caps = next_steps[workflow_step]

            # Create next task
            new_task_id = f"{completed_task_id}_{next_step_type}"

            self.send_message(
                recipient=self.agent_id,
                message_type=MessageType.TASK_CREATE,
                payload={
                    "task_id": new_task_id,
                    "task_type": next_step_type,
                    "previous_result": result,
                    "required_capabilities": required_caps,
                    "priority": 5
                }
            )

            self.logger.info(f"Triggered next step: {next_step_type}")

    def _check_agent_health(self):
        """Check health of all registered agents."""
        now = datetime.now()
        dead_agents = []

        for agent_id, last_heartbeat in self.agent_heartbeats.items():
            if (now - last_heartbeat).total_seconds() > self.heartbeat_timeout:
                self.logger.warning(f"Agent {agent_id} appears dead (no heartbeat)")
                dead_agents.append(agent_id)

        for agent_id in dead_agents:
            self.registered_agents[agent_id]["status"] = "dead"
            # Reassign tasks
            for task_id, assignment in list(self.active_assignments.items()):
                if assignment.agent_id == agent_id and not assignment.completed:
                    self.logger.info(f"Reassigning task {task_id}")
                    # Put back in queue
                    self._handle_task_create(task_id, {
                        "task_type": "reassign",
                        "priority": 10,
                        "original_agent": agent_id
                    })

    def start_debugging_workflow(self, issue: Dict) -> str:
        """Start a new debugging workflow for an issue.

        Args:
            issue: Issue description with title, description, error_log, etc.

        Returns:
            Workflow ID.
        """
        workflow_id = f"debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        self.current_issue = issue
        self.workflow_state[workflow_id] = {
            "issue": issue,
            "status": "started",
            "started_at": datetime.now().isoformat(),
            "steps_completed": [],
            "current_step": "analysis"
        }

        # Create first task - analysis
        self.send_message(
            recipient=self.agent_id,
            message_type=MessageType.TASK_CREATE,
            payload={
                "task_id": f"{workflow_id}_analysis",
                "task_type": "analysis",
                "issue": issue,
                "required_capabilities": [AgentCapability.ANALYZE.value],
                "priority": 5,
                "workflow_id": workflow_id
            }
        )

        self.logger.info(f"Started debugging workflow: {workflow_id}")

        return workflow_id

    def get_workflow_status(self, workflow_id: str) -> Optional[Dict]:
        """Get status of a workflow."""
        return self.workflow_state.get(workflow_id)

    def get_system_status(self) -> Dict:
        """Get overall system status."""
        return {
            "coordinator": self.agent_id,
            "registered_agents": len(self.registered_agents),
            "agents": {
                agent_id: {
                    "capabilities": list(caps),
                    "status": info.get("status"),
                    "current_task": info.get("current_task")
                }
                for agent_id, info in self.registered_agents.items()
                for caps in [self.agent_capabilities.get(agent_id, set())]
            },
            "pending_tasks": self.pending_tasks.qsize(),
            "active_assignments": len(self.active_assignments),
            "completed_tasks": len(self.task_history)
        }

    def _run(self):
        """Main coordinator loop."""
        self.logger.info("Coordinator started, managing agent cluster")

        last_health_check = datetime.now()

        while not self._stop_event.is_set():
            try:
                now = datetime.now()

                # Periodic health check
                if (now - last_health_check).total_seconds() >= 5:
                    self._check_agent_health()
                    self._assign_pending_tasks()
                    last_health_check = now

                self._stop_event.wait(1)

            except Exception as e:
                self.logger.error(f"Coordinator error: {e}")
                self._stop_event.wait(1)

        self.logger.info("Coordinator stopped")
