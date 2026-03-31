# Monitor agent for tracking execution and detecting deviations
# All comments in this file are in English per project guidelines

import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ..core import Agent, AgentCapability, AgentState
from ..messaging import Message, MessageType


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


class MonitorAgent(Agent):
    """Monitor agent responsible for tracking task execution and detecting deviations.

    Based on workflow/roles/monitor.py design.

    The monitor:
    - Continuously observes task progress
    - Tracks quality metrics
    - Detects scope creep
    - Triggers alerts when deviations detected
    - Escalates critical issues
    """

    def __init__(
        self,
        agent_id: str = "monitor",
        message_bus=None,
        monitoring_interval: int = 5
    ):
        """Initialize monitor agent."""
        super().__init__(
            agent_id=agent_id,
            capabilities=[AgentCapability.MONITOR],
            message_bus=message_bus,
            heartbeat_interval=2.0
        )
        self.monitoring_interval = monitoring_interval
        self.monitored_tasks: Dict[str, Dict] = {}
        self.alert_history: List[Deviation] = []

        # Thresholds
        self.thresholds = {
            "progress_ratio": 1.5,  # actual/planned
            "revision_count": 2,
            "test_pass_rate": 0.9,
            "lines_changed": 500,
        }

        self._register_handlers()

    def _register_handlers(self):
        """Register message handlers."""
        self.register_handler(MessageType.TASK_START, self._handle_task_start)
        self.register_handler(MessageType.TASK_PROGRESS, self._handle_progress)
        self.register_handler(MessageType.TASK_COMPLETE, self._handle_complete)

    def _handle_specialized(self, message: Message):
        """Handle specialized messages."""
        pass

    def _handle_task_start(self, task_id: str, payload: Dict) -> Dict:
        """Handle task start notification."""
        self.monitored_tasks[task_id] = {
            "task_id": task_id,
            "started_at": datetime.now(),
            "planned_duration": payload.get("planned_duration", 3600),
            "progress_updates": [],
            "revision_count": 0
        }
        self.logger.info(f"Started monitoring task {task_id}")
        return {"monitored": True}

    def _handle_progress(self, task_id: str, payload: Dict) -> Dict:
        """Handle progress update."""
        if task_id not in self.monitored_tasks:
            return {"error": "Task not monitored"}

        update = {
            "progress": payload.get("progress", 0),
            "message": payload.get("message", ""),
            "timestamp": datetime.now(),
            "agent_id": payload.get("agent_id", "unknown")
        }

        self.monitored_tasks[task_id]["progress_updates"].append(update)

        # Check for deviations
        deviations = self._check_deviations(task_id)
        for deviation in deviations:
            self._trigger_alert(deviation)

        return {"received": True, "deviations": len(deviations)}

    def _handle_complete(self, task_id: str, payload: Dict) -> Dict:
        """Handle task completion."""
        if task_id in self.monitored_tasks:
            self.monitored_tasks[task_id]["completed_at"] = datetime.now()
            self.logger.info(f"Task {task_id} completed, stopped monitoring")

        return {"acknowledged": True}

    def _check_deviations(self, task_id: str) -> List[Deviation]:
        """Check for deviations in a task."""
        deviations = []
        task = self.monitored_tasks.get(task_id)

        if not task:
            return deviations

        # Check progress deviation
        progress_dev = self._check_progress_deviation(task)
        if progress_dev:
            deviations.append(progress_dev)

        # Check quality deviation
        quality_dev = self._check_quality_deviation(task)
        if quality_dev:
            deviations.append(quality_dev)

        return deviations

    def _check_progress_deviation(self, task: Dict) -> Optional[Deviation]:
        """Check for progress-related deviations."""
        planned_duration = task.get("planned_duration", 3600)
        started_at = task.get("started_at")

        if not started_at:
            return None

        elapsed = (datetime.now() - started_at).total_seconds()
        ratio = elapsed / planned_duration if planned_duration > 0 else 0

        if ratio > self.thresholds["progress_ratio"] * 2:
            return Deviation(
                task_id=task["task_id"],
                deviation_type="progress",
                severity=AlertLevel.CRITICAL,
                message=f"Severe overtime: {ratio:.1f}x planned duration",
                metric_value=ratio,
                threshold=self.thresholds["progress_ratio"]
            )
        elif ratio > self.thresholds["progress_ratio"]:
            return Deviation(
                task_id=task["task_id"],
                deviation_type="progress",
                severity=AlertLevel.WARNING,
                message=f"Overtime detected: {ratio:.1f}x planned duration",
                metric_value=ratio,
                threshold=self.thresholds["progress_ratio"]
            )

        return None

    def _check_quality_deviation(self, task: Dict) -> Optional[Deviation]:
        """Check for quality-related deviations."""
        revision_count = task.get("revision_count", 0)

        if revision_count > self.thresholds["revision_count"]:
            return Deviation(
                task_id=task["task_id"],
                deviation_type="quality",
                severity=AlertLevel.CRITICAL,
                message=f"Excessive revisions: {revision_count}",
                metric_value=revision_count,
                threshold=self.thresholds["revision_count"]
            )

        return None

    def _trigger_alert(self, deviation: Deviation):
        """Trigger an alert for a deviation."""
        self.alert_history.append(deviation)

        alert_payload = {
            "task_id": deviation.task_id,
            "type": deviation.deviation_type,
            "severity": deviation.severity.value,
            "message": deviation.message,
            "metric": deviation.metric_value,
            "threshold": deviation.threshold
        }

        # Send alert to coordinator
        self.send_message(
            recipient="coordinator",
            message_type=MessageType.ALERT,
            payload=alert_payload,
            priority=10 if deviation.severity == AlertLevel.CRITICAL else 5
        )

        self.logger.warning(
            f"Alert [{deviation.severity.value}]: {deviation.message}"
        )

        # Escalate critical alerts
        if deviation.severity == AlertLevel.CRITICAL:
            self._escalate(deviation)

    def _escalate(self, deviation: Deviation):
        """Escalate critical deviation."""
        self.send_message(
            recipient="planner",
            message_type=MessageType.ESCALATE,
            payload={
                "task_id": deviation.task_id,
                "reason": deviation.message,
                "action": "replan"
            }
        )

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get monitoring metrics summary."""
        return {
            "monitored_tasks": len(self.monitored_tasks),
            "total_alerts": len(self.alert_history),
            "alerts_by_severity": {
                "critical": len([a for a in self.alert_history if a.severity == AlertLevel.CRITICAL]),
                "warning": len([a for a in self.alert_history if a.severity == AlertLevel.WARNING]),
                "info": len([a for a in self.alert_history if a.severity == AlertLevel.INFO])
            }
        }

    def _run(self):
        """Main monitoring loop."""
        self.logger.info("Monitor agent started")

        last_check = datetime.now()

        while not self._stop_event.is_set():
            try:
                now = datetime.now()

                # Periodic monitoring check
                if (now - last_check).total_seconds() >= self.monitoring_interval:
                    for task_id, task in self.monitored_tasks.items():
                        if "completed_at" not in task:
                            deviations = self._check_deviations(task_id)
                            for deviation in deviations:
                                self._trigger_alert(deviation)

                    last_check = now

                self._stop_event.wait(1)

            except Exception as e:
                self.logger.error(f"Monitor error: {e}")
                self._stop_event.wait(1)

        self.logger.info("Monitor agent stopped")
