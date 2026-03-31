#!/usr/bin/env python3
"""Workflow checkpoint guard - ensures mandatory steps are completed."""

import json
import sys
from pathlib import Path
from datetime import datetime

CHECKPOINTS = {
    "problem_analyzed": {"required": True, "order": 1},
    "scope_identified": {"required": True, "order": 2},
    "code_located": {"required": True, "order": 3},
    "fix_applied": {"required": True, "order": 4},
    "regression_verified": {"required": True, "order": 5, "mandatory": True},
    "test_added": {"required": True, "order": 6, "mandatory": True},
    "artifacts_archived": {"required": True, "order": 7, "mandatory": True},
}


class WorkflowGuard:
    def __init__(self, state_dir=".workflow"):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(exist_ok=True)
        self.state_file = self.state_dir / "checkpoints.json"
        self.load_state()

    def load_state(self):
        if self.state_file.exists():
            self.state = json.loads(self.state_file.read_text())
        else:
            self.state = {"checkpoints": {}, "started_at": datetime.now().isoformat()}

    def save_state(self):
        self.state_file.write_text(json.dumps(self.state, indent=2))

    def mark_checkpoint(self, name: str, evidence: dict):
        """Mark a checkpoint as completed with evidence."""
        if name not in CHECKPOINTS:
            raise ValueError(f"Unknown checkpoint: {name}")

        self.state["checkpoints"][name] = {
            "completed_at": datetime.now().isoformat(),
            "evidence": evidence
        }
        self.save_state()
        print(f"✓ Checkpoint '{name}' completed")

    def verify_can_proceed(self, to_checkpoint: str) -> bool:
        """Verify all prerequisites are met before proceeding."""
        target_order = CHECKPOINTS[to_checkpoint]["order"]

        for name, config in CHECKPOINTS.items():
            if config["order"] < target_order and config["required"]:
                if name not in self.state["checkpoints"]:
                    print(f"✗ Cannot proceed: checkpoint '{name}' not completed")
                    return False
        return True

    def get_status(self) -> dict:
        """Get current workflow status."""
        completed = set(self.state["checkpoints"].keys())
        mandatory = {k for k, v in CHECKPOINTS.items() if v.get("mandatory")}
        missing_mandatory = mandatory - completed

        return {
            "completed": list(completed),
            "missing_mandatory": list(missing_mandatory),
            "is_complete": len(missing_mandatory) == 0
        }

    def require_completion(self):
        """Block if mandatory checkpoints are missing."""
        status = self.get_status()
        if not status["is_complete"]:
            print("\n" + "="*60)
            print("⚠️  WORKFLOW INCOMPLETE")
            print("="*60)
            print("Missing mandatory checkpoints:")
            for cp in status["missing_mandatory"]:
                print(f"  ✗ {cp}")
            print("\nYou must complete these steps before closing the task.")
            print("="*60)
            raise SystemExit(1)

    def reset(self):
        """Reset workflow state."""
        if self.state_file.exists():
            self.state_file.unlink()
        self.state = {"checkpoints": {}, "started_at": datetime.now().isoformat()}
        print("✓ Workflow state reset")


def main():
    if len(sys.argv) < 2:
        print("Usage: workflow_guard.py [mark|verify|status|require|reset]")
        sys.exit(1)

    guard = WorkflowGuard()
    cmd = sys.argv[1]

    if cmd == "mark":
        if len(sys.argv) < 3:
            print("Usage: workflow_guard.py mark <checkpoint> [evidence_json]")
            sys.exit(1)
        checkpoint = sys.argv[2]
        evidence = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
        guard.mark_checkpoint(checkpoint, evidence)

    elif cmd == "verify":
        if len(sys.argv) < 3:
            print("Usage: workflow_guard.py verify <checkpoint>")
            sys.exit(1)
        checkpoint = sys.argv[2]
        if guard.verify_can_proceed(checkpoint):
            print(f"✓ Can proceed to {checkpoint}")
        else:
            sys.exit(1)

    elif cmd == "status":
        status = guard.get_status()
        print(json.dumps(status, indent=2))

    elif cmd == "require":
        guard.require_completion()

    elif cmd == "reset":
        guard.reset()

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
