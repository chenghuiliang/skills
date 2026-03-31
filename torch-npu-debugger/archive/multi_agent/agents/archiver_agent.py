# Archiver agent for finalizing and storing artifacts
# All comments in this file are in English per project guidelines

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ..core import Agent, AgentCapability, AgentState
from ..messaging import Message, MessageType


class ArchiverAgent(Agent):
    """Archiver agent responsible for finalizing and storing task artifacts.

    Based on workflow/roles/archiver.py design.

    The archiver:
    - Collects all deliverables from workflow
    - Generates summary reports
    - Extracts lessons learned
    - Updates knowledge bases
    """

    def __init__(
        self,
        agent_id: str = "archiver",
        message_bus=None,
        archive_dir: str = ".workflow_archives"
    ):
        """Initialize archiver agent."""
        super().__init__(
            agent_id=agent_id,
            capabilities=[AgentCapability.ARCHIVE],
            message_bus=message_bus
        )
        self.archive_dir = Path(archive_dir)
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        self._register_handlers()

    def _register_handlers(self):
        """Register message handlers."""
        self.register_handler(MessageType.TASK_ASSIGN, self._handle_archive_task)

    def _handle_specialized(self, message: Message):
        """Handle specialized messages."""
        pass

    def _handle_archive_task(self, task_id: str, payload: Dict) -> Dict:
        """Handle archive task."""
        self.logger.info(f"Starting archiving for task {task_id}")
        self.transition_to(AgentState.WORKING, f"Archiving {task_id}")
        self.current_task = task_id

        try:
            deliverables = payload.get("deliverables", [])
            plan = payload.get("plan", {})
            result = payload.get("result", {})

            # Create archive directory
            task_archive_dir = self.archive_dir / task_id
            task_archive_dir.mkdir(parents=True, exist_ok=True)

            self.report_progress(20, "Collecting deliverables")
            collected = self._collect_deliverables(deliverables, task_archive_dir)

            self.report_progress(50, "Generating summary")
            summary = self._generate_summary(task_id, plan, result)
            self._save_summary(summary, task_archive_dir)

            self.report_progress(70, "Extracting lessons")
            lessons = self._extract_lessons(result)
            self._save_lessons(lessons, task_archive_dir)

            self.report_progress(90, "Updating knowledge base")
            self._update_knowledge_base(summary, lessons)

            self.report_progress(100, "Archive complete")

            archive_result = {
                "success": True,
                "archive_dir": str(task_archive_dir),
                "files_archived": len(collected),
                "summary": summary,
                "lessons": lessons,
                "workflow_step": "archive"
            }

            self.send_message(
                recipient="coordinator",
                message_type=MessageType.TASK_COMPLETE,
                payload={
                    "task_id": task_id,
                    "agent_id": self.agent_id,
                    "result": archive_result
                }
            )

            self.metrics.tasks_completed += 1
            self.transition_to(AgentState.IDLE, "Archiving complete")

            return archive_result

        except Exception as e:
            self.logger.error(f"Archiving failed: {e}")
            self.metrics.tasks_failed += 1

            self.send_message(
                recipient="coordinator",
                message_type=MessageType.TASK_FAIL,
                payload={
                    "task_id": task_id,
                    "agent_id": self.agent_id,
                    "error": str(e)
                }
            )

            self.transition_to(AgentState.ERROR, str(e))
            return {"success": False, "error": str(e)}

        finally:
            self.current_task = None

    def _collect_deliverables(self, deliverables: List[Dict], archive_dir: Path) -> List[Path]:
        """Collect and store deliverables."""
        archived = []

        for deliverable in deliverables:
            filename = f"{deliverable.get('name', 'unknown')}.json"
            filepath = archive_dir / filename

            content = {
                "name": deliverable.get("name"),
                "type": deliverable.get("type"),
                "content": deliverable.get("content"),
                "archived_at": datetime.now().isoformat()
            }

            with open(filepath, 'w') as f:
                json.dump(content, f, indent=2, default=str)

            archived.append(filepath)

        return archived

    def _generate_summary(self, task_id: str, plan: Dict, result: Dict) -> Dict:
        """Generate task summary."""
        return {
            "task_id": task_id,
            "goal": plan.get("goal", "Unknown"),
            "status": "completed" if result.get("success") else "failed",
            "completed_at": datetime.now().isoformat(),
            "outcome": "Resolved" if result.get("success") else "Failed",
            "metrics": {
                "duration": result.get("duration", 0),
                "steps_completed": len(result.get("steps", [])),
            }
        }

    def _save_summary(self, summary: Dict, archive_dir: Path):
        """Save summary to file."""
        summary_path = archive_dir / "summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2, default=str)

    def _extract_lessons(self, result: Dict) -> List[Dict]:
        """Extract lessons learned."""
        lessons = []

        # Extract from result
        if result.get("revision_count", 0) > 0:
            lessons.append({
                "type": "process",
                "lesson": f"Required {result['revision_count']} revisions",
                "recommendation": "Enhance initial planning"
            })

        if result.get("success"):
            lessons.append({
                "type": "technical",
                "lesson": "Fix successfully implemented",
                "recommendation": "Document pattern for future use"
            })

        return lessons

    def _save_lessons(self, lessons: List[Dict], archive_dir: Path):
        """Save lessons to file."""
        lessons_path = archive_dir / "lessons_learned.json"
        with open(lessons_path, 'w') as f:
            json.dump(lessons, f, indent=2, default=str)

    def _update_knowledge_base(self, summary: Dict, lessons: List[Dict]):
        """Update knowledge base."""
        kb_path = self.archive_dir / "knowledge_base.json"

        kb = {"cases": [], "lessons": []}
        if kb_path.exists():
            try:
                with open(kb_path, 'r') as f:
                    kb = json.load(f)
            except Exception:
                pass

        # Add case
        kb["cases"].append({
            "id": summary["task_id"],
            "goal": summary["goal"],
            "status": summary["status"],
            "resolved": summary["status"] == "completed"
        })

        # Add lessons
        for lesson in lessons:
            kb["lessons"].append({
                "task_id": summary["task_id"],
                **lesson
            })

        with open(kb_path, 'w') as f:
            json.dump(kb, f, indent=2, default=str)

    def _run(self):
        """Main loop."""
        self.logger.info("Archiver agent started")
        while not self._stop_event.is_set():
            self._stop_event.wait(1)
