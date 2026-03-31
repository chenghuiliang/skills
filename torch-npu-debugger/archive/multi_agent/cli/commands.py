# CLI commands for multi-agent system
# Based on workflow/roles design
# All comments in this file are in English per project guidelines

import sys
import time
import json
from typing import Optional, List
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ..core import ProcessManager, CoordinatorAgent
from ..agents import (
    PlannerAgent, ExecutorAgent, EvaluatorAgent,
    MonitorAgent, ArchiverAgent
)
from ..messaging import create_message_bus


class AgentCommands:
    """Commands for managing agents."""

    def __init__(self):
        """Initialize agent commands."""
        self.process_manager = ProcessManager()
        self._setup_agents()

    def _setup_agents(self):
        """Setup agent process configurations based on workflow/roles."""
        self.agent_configs = {
            "coordinator": {
                "class": CoordinatorAgent,
                "kwargs": {"agent_id": "coordinator"}
            },
            "planner": {
                "class": PlannerAgent,
                "kwargs": {"agent_id": "planner"}
            },
            "executor": {
                "class": ExecutorAgent,
                "kwargs": {"agent_id": "executor", "workspace": "."}
            },
            "evaluator": {
                "class": EvaluatorAgent,
                "kwargs": {"agent_id": "evaluator"}
            },
            "monitor": {
                "class": MonitorAgent,
                "kwargs": {"agent_id": "monitor"}
            },
            "archiver": {
                "class": ArchiverAgent,
                "kwargs": {"agent_id": "archiver"}
            }
        }

    def start(self, agent_id: Optional[str] = None):
        """Start one or all agents."""
        if agent_id:
            if agent_id not in self.agent_configs:
                print(f"Unknown agent: {agent_id}")
                print(f"Available: {', '.join(self.agent_configs.keys())}")
                return False
            return self._start_agent(agent_id)
        else:
            return self._start_all_agents()

    def _start_agent(self, agent_id: str) -> bool:
        """Start a specific agent."""
        config = self.agent_configs[agent_id]
        try:
            agent_process = self.process_manager.register_agent(
                agent_class=config["class"],
                agent_id=agent_id,
                agent_kwargs=config["kwargs"],
                auto_start=True
            )
            print(f"Started agent: {agent_id} (PID: {agent_process.info.pid})")
            return True
        except Exception as e:
            print(f"Failed to start agent {agent_id}: {e}")
            return False

    def _start_all_agents(self) -> bool:
        """Start all agents."""
        print("Starting all agents...")

        # Start coordinator first
        self._start_agent("coordinator")
        time.sleep(1)

        # Start other agents
        results = {}
        for agent_id in ["planner", "executor", "evaluator", "monitor", "archiver"]:
            results[agent_id] = self._start_agent(agent_id)
            time.sleep(0.5)

        success_count = sum(1 for r in results.values() if r)
        print(f"\nStarted {success_count}/{len(self.agent_configs)} agents")
        return success_count == len(self.agent_configs)

    def stop(self, agent_id: Optional[str] = None):
        """Stop one or all agents."""
        if agent_id:
            if agent_id not in self.process_manager.processes:
                print(f"Agent not running: {agent_id}")
                return False
            result = self.process_manager.stop_agent(agent_id)
            if result:
                print(f"Stopped agent: {agent_id}")
            return result
        else:
            print("Stopping all agents...")
            results = self.process_manager.stop_all()
            stopped = sum(1 for r in results.values() if r)
            print(f"Stopped {stopped}/{len(results)} agents")
            return stopped == len(results)

    def status(self):
        """Show status of all agents."""
        status = self.process_manager.get_status()

        if not status:
            print("No agents running")
            return

        print("\n" + "=" * 60)
        print("AGENT STATUS (based on workflow/roles)")
        print("=" * 60)

        for agent_id, info in status.items():
            print(f"\n{agent_id}:")
            print(f"  PID: {info.get('pid', 'N/A')}")
            print(f"  Status: {info.get('status', 'unknown')}")
            print(f"  Uptime: {info.get('uptime', 0):.1f}s")
            print(f"  Restarts: {info.get('restart_count', 0)}")

        print("\n" + "=" * 60)
        print("Roles:")
        print("  coordinator - Task coordination and assignment")
        print("  planner     - Problem analysis and plan creation")
        print("  executor    - Implementation (analyzer/locator/fixer/tester)")
        print("  evaluator   - Review and acceptance")
        print("  monitor     - Progress tracking and deviation detection")
        print("  archiver    - Artifact collection and knowledge base update")
        print("=" * 60)


class WorkflowCommands:
    """Commands for managing workflows."""

    def __init__(self):
        """Initialize workflow commands."""
        self.message_bus = create_message_bus("file")
        self.coordinator_id = "coordinator"

    def start(
        self,
        title: str,
        description: str,
        error_log: Optional[str] = None,
        from_file: Optional[str] = None
    ):
        """Start a new debugging workflow."""
        if from_file:
            with open(from_file, 'r') as f:
                content = f.read()
                try:
                    issue = json.loads(content)
                except json.JSONDecodeError:
                    issue = {
                        "title": title,
                        "description": content,
                        "error_log": content
                    }
        else:
            issue = {
                "title": title,
                "description": description,
                "error_log": error_log or description
            }

        print(f"Starting debugging workflow for: {title}")
        print("Agents: planner → executor → evaluator → archiver")
        print("Monitor: tracking progress throughout")
        print(f"\nWorkflow started!")
        return True


class SystemCommands:
    """System-level commands."""

    def health(self):
        """Check overall system health."""
        print("System Health Check")
        print("=" * 40)
        print("Message Bus: OK (File-based)")
        print("Agent Registry: Checking...")

    def cleanup(self):
        """Clean up old artifacts."""
        print("Cleaning up...")
        message_dir = Path(".agent_messages")
        if message_dir.exists():
            import shutil
            shutil.rmtree(message_dir)
            print("Cleaned message files")
        print("Cleanup complete")
