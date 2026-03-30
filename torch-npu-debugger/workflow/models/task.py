# Task and workflow data models
# All comments in this file are in English per project guidelines

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional


class TaskState(Enum):
    """States for the main workflow task lifecycle."""
    INIT = "initialized"
    PLANNING = "planning"
    EXECUTING = "executing"
    EVALUATING = "evaluating"
    ACCEPTED = "accepted"
    ARCHIVED = "archived"
    BLOCKED = "blocked"
    REJECTED = "rejected"
    REPLANNING = "replanning"  # When plan needs adjustment
    RETRYING = "retrying"  # When execution needs retry


class RoleState(Enum):
    """States for individual roles."""
    IDLE = "idle"
    WORKING = "working"
    BLOCKED = "blocked"
    WAITING = "waiting"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class TaskMetrics:
    """Metrics for tracking task execution."""
    planned_duration: int = 0  # in seconds
    actual_duration: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    planning_time: int = 0
    execution_time: int = 0
    evaluation_time: int = 0
    revision_count: int = 0  # Number of times sent back for revision
    test_pass_count: int = 0
    test_fail_count: int = 0
    lines_changed: int = 0
    files_modified: int = 0

    @property
    def is_overtime(self) -> bool:
        """Check if task is over planned duration."""
        if self.planned_duration <= 0:
            return False
        return self.actual_duration > self.planned_duration * 1.5

    @property
    def efficiency(self) -> float:
        """Calculate efficiency ratio."""
        if self.planned_duration <= 0:
            return 1.0
        return self.planned_duration / max(self.actual_duration, 1)


@dataclass
class Deliverable:
    """A deliverable item produced by a role."""
    name: str
    file_path: str
    description: str
    produced_by: str  # role name
    produced_at: datetime = field(default_factory=datetime.now)
    verified: bool = False
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None


@dataclass
class StateTransition:
    """Record of a state transition."""
    from_state: TaskState
    to_state: TaskState
    timestamp: datetime
    triggered_by: str  # role name
    reason: str


@dataclass
class ExecutionStep:
    """A single step in the execution plan."""
    step_id: str
    description: str
    role: str  # which role executes this step
    estimated_duration: int  # in seconds
    dependencies: List[str] = field(default_factory=list)
    completed: bool = False
    actual_duration: int = 0
    output: Optional[str] = None


@dataclass
class ExecutionPlan:
    """The complete execution plan for a task."""
    goal: str
    steps: List[ExecutionStep] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    risk_mitigation: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def get_progress(self) -> float:
        """Get completion progress (0-100)."""
        if not self.steps:
            return 0.0
        completed = sum(1 for s in self.steps if s.completed)
        return (completed / len(self.steps)) * 100

    def get_current_step(self) -> Optional[ExecutionStep]:
        """Get the current (first incomplete) step."""
        for step in self.steps:
            if not step.completed:
                return step
        return None


@dataclass
class Task:
    """Main task entity for the workflow."""
    id: str
    title: str
    description: str
    state: TaskState = TaskState.INIT
    current_role: Optional[str] = None
    plan: Optional[ExecutionPlan] = None
    deliverables: List[Deliverable] = field(default_factory=list)
    metrics: TaskMetrics = field(default_factory=TaskMetrics)
    history: List[StateTransition] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    priority: str = "normal"  # low, normal, high, critical
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    blocked_reason: Optional[str] = None
    rejection_reason: Optional[str] = None

    def transition_to(self, new_state: TaskState, triggered_by: str, reason: str):
        """Record a state transition."""
        transition = StateTransition(
            from_state=self.state,
            to_state=new_state,
            timestamp=datetime.now(),
            triggered_by=triggered_by,
            reason=reason
        )
        self.history.append(transition)
        self.state = new_state
        self.updated_at = datetime.now()

    def add_deliverable(self, deliverable: Deliverable):
        """Add a deliverable to the task."""
        self.deliverables.append(deliverable)
        self.updated_at = datetime.now()

    def get_deliverables_by_role(self, role: str) -> List[Deliverable]:
        """Get all deliverables produced by a specific role."""
        return [d for d in self.deliverables if d.produced_by == role]

    def get_current_step_for_role(self, role: str) -> Optional[ExecutionStep]:
        """Get current step assigned to a role."""
        if not self.plan:
            return None
        for step in self.plan.steps:
            if step.role == role and not step.completed:
                return step
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "state": self.state.value,
            "current_role": self.current_role,
            "priority": self.priority,
            "progress": self.plan.get_progress() if self.plan else 0,
            "metrics": {
                "planned_duration": self.metrics.planned_duration,
                "actual_duration": self.metrics.actual_duration,
                "revision_count": self.metrics.revision_count,
                "efficiency": self.metrics.efficiency,
            },
            "deliverables_count": len(self.deliverables),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
