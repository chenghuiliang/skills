# Archiver role for workflow
# All comments in this file are in English per project guidelines

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from workflow.roles.base import Role, RoleCapability
from workflow.models.task import Task, TaskState, RoleState, Deliverable
from workflow.models.message import MessageType


class Archiver(Role):
    """Archiver role responsible for finalizing and storing task artifacts.

    The archiver collects all deliverables, generates summary reports,
    updates knowledge bases, and stores lessons learned.
    """

    def __init__(self, coordinator):
        """Initialize the archiver role."""
        super().__init__("archiver", coordinator)
        self.capabilities = [RoleCapability.ARCHIVE]
        self.archive_dir = Path(".workflow_archives")

    def receive_task(self, task: Task) -> bool:
        """Receive a task for archiving.

        Args:
            task: The task to archive

        Returns:
            bool: True if task was accepted
        """
        if task.state != TaskState.ACCEPTED:
            return False

        self.current_task = task
        self.state = RoleState.WORKING
        task.current_role = self.name
        return True

    def execute(self, task: Task) -> Dict[str, Any]:
        """Execute the archiving task.

        Args:
            task: The task to archive

        Returns:
            Dict containing archive results
        """
        self.report_progress(10, "Starting archive process")

        # Create archive directory
        task_archive_dir = self.archive_dir / task.id
        task_archive_dir.mkdir(parents=True, exist_ok=True)

        # Step 1: Collect all deliverables
        self.report_progress(30, "Collecting deliverables")
        collected = self._collect_deliverables(task, task_archive_dir)

        # Step 2: Generate summary report
        self.report_progress(50, "Generating summary report")
        summary = self._generate_summary(task)
        self._save_summary(summary, task_archive_dir)

        # Step 3: Extract lessons learned
        self.report_progress(70, "Extracting lessons learned")
        lessons = self._extract_lessons_learned(task)
        self._save_lessons(lessons, task_archive_dir)

        # Step 4: Update knowledge base
        self.report_progress(90, "Updating knowledge base")
        self._update_knowledge_base(task, lessons)

        # Complete archiving
        self.report_progress(100, "Archive complete")

        task.transition_to(TaskState.ARCHIVED, self.name, "Archiving complete")

        self.complete_task(
            deliverables=[{
                "name": "archive_manifest",
                "content": {
                    "archive_dir": str(task_archive_dir),
                    "files_archived": len(collected),
                    "summary": summary
                }
            }],
            metrics={
                "files_archived": len(collected),
                "archive_size_kb": self._calculate_archive_size(task_archive_dir)
            }
        )

        return {
            "success": True,
            "archive_dir": str(task_archive_dir),
            "files_archived": len(collected),
            "summary": summary
        }

    def _collect_deliverables(
        self,
        task: Task,
        archive_dir: Path
    ) -> List[Path]:
        """Collect and store all task deliverables.

        Args:
            task: The task
            archive_dir: Archive directory

        Returns:
            List of archived file paths
        """
        archived = []

        # Save each deliverable
        for deliverable in task.deliverables:
            filename = f"{deliverable.name}.json"
            filepath = archive_dir / filename

            content = {
                "name": deliverable.name,
                "description": deliverable.description,
                "produced_by": deliverable.produced_by,
                "produced_at": deliverable.produced_at.isoformat(),
                "content": deliverable.content if isinstance(deliverable.content, (dict, list)) else str(deliverable.content)
            }

            with open(filepath, 'w') as f:
                json.dump(content, f, indent=2, default=str)

            archived.append(filepath)

        # Save task metadata
        metadata_path = archive_dir / "task_metadata.json"
        metadata = {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "state": task.state.value,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
            "metrics": {
                "planned_duration": task.metrics.planned_duration,
                "actual_duration": task.metrics.actual_duration,
                "revision_count": task.metrics.revision_count
            }
        }

        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)

        archived.append(metadata_path)

        return archived

    def _generate_summary(self, task: Task) -> Dict[str, Any]:
        """Generate task summary report.

        Args:
            task: The task

        Returns:
            Dict with summary information
        """
        return {
            "task_id": task.id,
            "title": task.title,
            "executive_summary": self._create_executive_summary(task),
            "problem": task.description[:200] + "..." if len(task.description) > 200 else task.description,
            "solution_approach": self._extract_solution_approach(task),
            "outcome": "Resolved" if task.state == TaskState.ARCHIVED else "Pending",
            "timeline": {
                "created": task.created_at.isoformat(),
                "completed": task.updated_at.isoformat(),
                "duration_seconds": task.metrics.actual_duration
            },
            "metrics": {
                "revisions": task.metrics.revision_count,
                "lines_changed": task.metrics.lines_changed,
                "files_modified": task.metrics.files_modified,
                "tests_added": task.metrics.test_pass_count
            },
            "deliverables_summary": [
                {"name": d.name, "by": d.produced_by}
                for d in task.deliverables
            ]
        }

    def _create_executive_summary(self, task: Task) -> str:
        """Create executive summary."""
        parts = [
            f"Issue: {task.title}",
            f"Status: {task.state.value}",
            f"Duration: {task.metrics.actual_duration // 60} minutes",
            f"Revisions: {task.metrics.revision_count}"
        ]
        return " | ".join(parts)

    def _extract_solution_approach(self, task: Task) -> str:
        """Extract solution approach from deliverables."""
        for d in task.deliverables:
            if d.name == "execution_plan":
                return f"Planned approach by {d.produced_by}"
            if d.name == "root_cause":
                return "Root cause identified and fixed"
        return "Standard debugging workflow"

    def _save_summary(self, summary: Dict, archive_dir: Path):
        """Save summary to file."""
        summary_path = archive_dir / "summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2, default=str)

    def _extract_lessons_learned(self, task: Task) -> List[Dict]:
        """Extract lessons learned from task.

        Args:
            task: The task

        Returns:
            List of lessons
        """
        lessons = []

        # Extract from revision count
        if task.metrics.revision_count > 0:
            lessons.append({
                "type": "process",
                "lesson": f"Required {task.metrics.revision_count} revisions - consider more thorough planning for similar issues",
                "recommendation": "Enhance initial analysis phase"
            })

        # Extract from duration
        if task.metrics.planned_duration > 0:
            ratio = task.metrics.actual_duration / task.metrics.planned_duration
            if ratio > 1.5:
                lessons.append({
                    "type": "estimation",
                    "lesson": f"Actual time ({task.metrics.actual_duration}s) exceeded estimate ({task.metrics.planned_duration}s) by {ratio:.1f}x",
                    "recommendation": "Adjust estimation for similar complexity issues"
                })

        # Extract from error patterns
        classification = task.context.get("classification", {})
        if classification.get("category"):
            lessons.append({
                "type": "technical",
                "lesson": f"Issue category: {classification['category']}",
                "recommendation": f"Check {classification.get('components', ['relevant docs'])} for patterns"
            })

        return lessons

    def _save_lessons(self, lessons: List[Dict], archive_dir: Path):
        """Save lessons learned to file."""
        lessons_path = archive_dir / "lessons_learned.json"
        with open(lessons_path, 'w') as f:
            json.dump(lessons, f, indent=2, default=str)

    def _update_knowledge_base(self, task: Task, lessons: List[Dict]):
        """Update knowledge base with new lessons.

        Args:
            task: The task
            lessons: Lessons learned
        """
        kb_path = self.archive_dir / "knowledge_base.json"

        # Load existing knowledge base
        kb = {"cases": [], "patterns": [], "lessons": []}
        if kb_path.exists():
            try:
                with open(kb_path, 'r') as f:
                    kb = json.load(f)
            except Exception:
                pass

        # Add new case
        case = {
            "id": task.id,
            "title": task.title,
            "category": task.context.get("classification", {}).get("category", "unknown"),
            "components": task.context.get("classification", {}).get("components", []),
            "complexity": task.context.get("classification", {}).get("complexity", "unknown"),
            "resolved": True,
            "lessons": [l["lesson"] for l in lessons]
        }
        kb["cases"].append(case)

        # Add lessons
        for lesson in lessons:
            lesson_entry = {
                "task_id": task.id,
                "type": lesson["type"],
                "lesson": lesson["lesson"],
                "recommendation": lesson["recommendation"]
            }
            kb["lessons"].append(lesson_entry)

        # Save updated knowledge base
        kb_path.parent.mkdir(parents=True, exist_ok=True)
        with open(kb_path, 'w') as f:
            json.dump(kb, f, indent=2, default=str)

    def _calculate_archive_size(self, archive_dir: Path) -> int:
        """Calculate archive size in KB."""
        total_size = 0
        for file in archive_dir.rglob("*"):
            if file.is_file():
                total_size += file.stat().st_size
        return total_size // 1024
