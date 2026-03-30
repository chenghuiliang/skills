# Monitor role for workflow
# All comments in this file are in English per project guidelines

import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable

from workflow.roles.base import Role, RoleCapability
from workflow.models.task import Task, TaskState, RoleState
from workflow.models.message import Message, MessageType


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Deviation:
    """A detected deviation from plan."""
    task_id: str
    deviation_type: str  # "progress", "quality", "scope"
    severity: AlertLevel
    message: str
    detected_at: datetime = field(default_factory=datetime.now)
    metric_value: float = 0.0
    threshold: float = 0.0


class Monitor(Role):
    """Monitor role responsible for tracking task execution and detecting deviations.

    The monitor continuously observes task progress, quality metrics, and scope,
    triggering alerts when deviations are detected.
    """

    def __init__(self, coordinator):
        """Initialize the monitor role."""
        super().__init__("monitor", coordinator)
        self.capabilities = [RoleCapability.MONITOR]
        self.monitored_tasks: Dict[str, Task] = {}
        self.alert_history: List[Dict] = []
        self.monitoring_interval: int = 30  # seconds
        self.deviation_handlers: Dict[str, Callable] = {
            "progress": self._handle_progress_deviation,
            "quality": self._handle_quality_deviation,
            "scope": self._handle_scope_deviation,
        }
        # Thresholds
        self.thresholds = {
            "progress_ratio": 1.5,  # actual/planned
            "revision_count": 2,
            "test_pass_rate": 0.9,
            "lines_changed": 500,
            "scope_creep_ratio": 1.5,
        }

    def receive_task(self, task: Task) -> bool:
        """Start monitoring a task.

        Args:
            task: The task to monitor

        Returns:
            bool: Always True
        """
        self.monitored_tasks[task.id] = task
        return True

    def execute(self, task: Task) -> Dict[str, Any]:
        """Execute monitoring (one cycle).

        Args:
            task: The task to monitor

        Returns:
            Dict with monitoring results
        """
        deviations = self.check_deviation(task)

        for deviation in deviations:
            self._trigger_alert(deviation)
            handler = self.deviation_handlers.get(deviation.deviation_type)
            if handler:
                handler(deviation)

        return {
            "success": True,
            "deviations_found": len(deviations),
            "deviations": [self._deviation_to_dict(d) for d in deviations]
        }

    def check_deviation(self, task: Task) -> List[Deviation]:
        """Check for deviations in a task.

        Args:
            task: The task to check

        Returns:
            List of detected deviations
        """
        deviations = []

        # Check progress deviation
        progress_dev = self._check_progress_deviation(task)
        if progress_dev:
            deviations.append(progress_dev)

        # Check quality deviation
        quality_dev = self._check_quality_deviation(task)
        if quality_dev:
            deviations.append(quality_dev)

        # Check scope deviation
        scope_dev = self._check_scope_deviation(task)
        if scope_dev:
            deviations.append(scope_dev)

        return deviations

    def _check_progress_deviation(self, task: Task) -> Optional[Deviation]:
        """Check for progress-related deviations."""
        metrics = task.metrics

        if metrics.planned_duration <= 0:
            return None

        ratio = metrics.actual_duration / metrics.planned_duration

        if ratio > self.thresholds["progress_ratio"] * 2:
            return Deviation(
                task_id=task.id,
                deviation_type="progress",
                severity=AlertLevel.CRITICAL,
                message=f"Severe overtime: {ratio:.1f}x planned duration",
                metric_value=ratio,
                threshold=self.thresholds["progress_ratio"]
            )
        elif ratio > self.thresholds["progress_ratio"]:
            return Deviation(
                task_id=task.id,
                deviation_type="progress",
                severity=AlertLevel.WARNING,
                message=f"Overtime detected: {ratio:.1f}x planned duration",
                metric_value=ratio,
                threshold=self.thresholds["progress_ratio"]
            )

        return None

    def _check_quality_deviation(self, task: Task) -> Optional[Deviation]:
        """Check for quality-related deviations."""
        metrics = task.metrics

        # Check revision count
        if metrics.revision_count > self.thresholds["revision_count"]:
            return Deviation(
                task_id=task.id,
                deviation_type="quality",
                severity=AlertLevel.CRITICAL,
                message=f"Excessive revisions: {metrics.revision_count}",
                metric_value=metrics.revision_count,
                threshold=self.thresholds["revision_count"]
            )

        # Check test pass rate
        total_tests = metrics.test_pass_count + metrics.test_fail_count
        if total_tests > 0:
            pass_rate = metrics.test_pass_count / total_tests
            if pass_rate < self.thresholds["test_pass_rate"]:
                return Deviation(
                    task_id=task.id,
                    deviation_type="quality",
                    severity=AlertLevel.WARNING,
                    message=f"Low test pass rate: {pass_rate:.1%}",
                    metric_value=pass_rate,
                    threshold=self.thresholds["test_pass_rate"]
                )

        # Check code change size
        if metrics.lines_changed > self.thresholds["lines_changed"]:
            return Deviation(
                task_id=task.id,
                deviation_type="quality",
                severity=AlertLevel.WARNING,
                message=f"Large code change: {metrics.lines_changed} lines",
                metric_value=metrics.lines_changed,
                threshold=self.thresholds["lines_changed"]
            )

        return None

    def _check_scope_deviation(self, task: Task) -> Optional[Deviation]:
        """Check for scope-related deviations."""
        # Check if deliverables exceed plan
        if task.plan and task.plan.steps:
            planned_steps = len(task.plan.steps)
            completed_steps = sum(1 for s in task.plan.steps if s.completed)

            # Check for scope creep (new unplanned deliverables)
            extra_deliverables = len([
                d for d in task.deliverables
                if d.name not in ["execution_plan", "analysis_report"]
            ])

            if extra_deliverables > planned_steps * 0.5:
                return Deviation(
                    task_id=task.id,
                    deviation_type="scope",
                    severity=AlertLevel.WARNING,
                    message=f"Scope creep detected: {extra_deliverables} extra deliverables",
                    metric_value=extra_deliverables,
                    threshold=planned_steps * 0.5
                )

        return None

    def _trigger_alert(self, deviation: Deviation):
        """Trigger an alert for a deviation."""
        alert = {
            "timestamp": deviation.detected_at.isoformat(),
            "task_id": deviation.task_id,
            "type": deviation.deviation_type,
            "severity": deviation.severity.value,
            "message": deviation.message,
            "metric": deviation.metric_value,
            "threshold": deviation.threshold
        }
        self.alert_history.append(alert)

        # Send alert message
        self.send_message(
            to_role="coordinator",
            message_type=MessageType.ALERT,
            payload=alert,
            priority="high" if deviation.severity == AlertLevel.CRITICAL else "normal"
        )

    def _handle_progress_deviation(self, deviation: Deviation):
        """Handle progress deviation."""
        task = self.monitored_tasks.get(deviation.task_id)
        if not task:
            return

        if deviation.severity == AlertLevel.CRITICAL:
            # Escalate to planner for replanning
            self.send_message(
                to_role="planner",
                message_type=MessageType.ESCALATE,
                payload={
                    "task_id": task.id,
                    "reason": deviation.message,
                    "action": "replan"
                },
                priority="critical"
            )
        else:
            # Notify coordinator
            self.send_message(
                to_role="coordinator",
                message_type=MessageType.WARNING,
                payload={
                    "task_id": task.id,
                    "warning": deviation.message,
                    "suggestion": "Consider adding resources or adjusting scope"
                }
            )

    def _handle_quality_deviation(self, deviation: Deviation):
        """Handle quality deviation."""
        task = self.monitored_tasks.get(deviation.task_id)
        if not task:
            return

        # Send feedback to executor
        self.send_message(
            to_role="executor",
            message_type=MessageType.WARNING,
            payload={
                "task_id": task.id,
                "issue": deviation.message,
                "recommendation": "Review and improve before submission"
            }
        )

    def _handle_scope_deviation(self, deviation: Deviation):
        """Handle scope deviation."""
        self.send_message(
            to_role="planner",
            message_type=MessageType.WARNING,
            payload={
                "task_id": deviation.task_id,
                "warning": deviation.message,
                "recommendation": "Reassess scope or create new task"
            }
        )

    def _deviation_to_dict(self, deviation: Deviation) -> Dict:
        """Convert deviation to dictionary."""
        return {
            "task_id": deviation.task_id,
            "type": deviation.deviation_type,
            "severity": deviation.severity.value,
            "message": deviation.message,
            "detected_at": deviation.detected_at.isoformat(),
            "metric_value": deviation.metric_value,
            "threshold": deviation.threshold
        }

    def get_alert_history(
        self,
        task_id: Optional[str] = None,
        severity: Optional[AlertLevel] = None
    ) -> List[Dict]:
        """Get alert history with optional filtering.

        Args:
            task_id: Filter by task ID
            severity: Filter by severity level

        Returns:
            List of alerts
        """
        alerts = self.alert_history

        if task_id:
            alerts = [a for a in alerts if a["task_id"] == task_id]

        if severity:
            alerts = [a for a in alerts if a["severity"] == severity.value]

        return alerts

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of monitoring metrics."""
        return {
            "monitored_tasks": len(self.monitored_tasks),
            "total_alerts": len(self.alert_history),
            "alerts_by_severity": {
                "critical": len([a for a in self.alert_history if a["severity"] == "critical"]),
                "warning": len([a for a in self.alert_history if a["severity"] == "warning"]),
                "info": len([a for a in self.alert_history if a["severity"] == "info"])
            },
            "thresholds": self.thresholds
        }
