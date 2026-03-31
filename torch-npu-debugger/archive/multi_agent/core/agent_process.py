# Process management for multi-agent system
# All comments in this file are in English per project guidelines

import os
import sys
import time
import signal
import psutil
from dataclasses import dataclass, field
from datetime import datetime
from multiprocessing import Process
from typing import Any, Dict, List, Optional, Callable, Type
import subprocess
import json

from .agent_base import Agent, AgentState


@dataclass
class ProcessInfo:
    """Information about a running agent process."""
    process_id: str
    agent_type: str
    pid: int
    start_time: datetime
    status: str = "running"
    restart_count: int = 0
    last_heartbeat: Optional[datetime] = None


class AgentProcess:
    """Wrapper for running an agent in a separate process."""

    def __init__(
        self,
        agent_class: Type[Agent],
        agent_id: str,
        agent_kwargs: Optional[Dict] = None,
        auto_restart: bool = True,
        max_restarts: int = 3
    ):
        """Initialize agent process wrapper.

        Args:
            agent_class: The Agent subclass to instantiate.
            agent_id: Unique identifier for the agent.
            agent_kwargs: Arguments to pass to agent constructor.
            auto_restart: Whether to auto-restart on failure.
            max_restarts: Maximum number of restarts.
        """
        self.agent_class = agent_class
        self.agent_id = agent_id
        self.agent_kwargs = agent_kwargs or {}
        self.auto_restart = auto_restart
        self.max_restarts = max_restarts

        self.process: Optional[Process] = None
        self.info = ProcessInfo(
            process_id=agent_id,
            agent_type=agent_class.__name__,
            pid=0,
            start_time=datetime.now()
        )

    def _run_agent(self):
        """Target function for the agent process."""
        try:
            # Remove agent_id from kwargs if present to avoid duplicate
            kwargs = dict(self.agent_kwargs)
            kwargs.pop("agent_id", None)

            agent = self.agent_class(
                agent_id=self.agent_id,
                **kwargs
            )
            agent.run()
        except Exception as e:
            print(f"Agent {self.agent_id} crashed: {e}")
            raise

    def start(self) -> bool:
        """Start the agent process."""
        try:
            self.process = Process(
                target=self._run_agent,
                name=f"Agent-{self.agent_id}",
                daemon=False
            )
            self.process.start()
            self.info.pid = self.process.pid
            self.info.start_time = datetime.now()
            self.info.status = "running"
            return True
        except Exception as e:
            self.info.status = "failed"
            print(f"Failed to start agent {self.agent_id}: {e}")
            return False

    def stop(self, timeout: float = 10.0) -> bool:
        """Stop the agent process gracefully."""
        if not self.process or not self.process.is_alive():
            return True

        try:
            # Try graceful termination first
            self.process.terminate()
            self.process.join(timeout=timeout / 2)

            # Force kill if still alive
            if self.process.is_alive():
                self.process.kill()
                self.process.join(timeout=timeout / 2)

            self.info.status = "stopped"
            return True
        except Exception as e:
            print(f"Error stopping agent {self.agent_id}: {e}")
            return False

    def is_alive(self) -> bool:
        """Check if the agent process is alive."""
        return self.process is not None and self.process.is_alive()

    def restart(self) -> bool:
        """Restart the agent process."""
        if self.info.restart_count >= self.max_restarts:
            print(f"Max restarts reached for {self.agent_id}")
            return False

        self.stop()
        self.info.restart_count += 1
        return self.start()

    def get_status(self) -> Dict[str, Any]:
        """Get current status of the agent process."""
        return {
            "process_id": self.info.process_id,
            "agent_type": self.info.agent_type,
            "pid": self.info.pid,
            "status": "running" if self.is_alive() else self.info.status,
            "start_time": self.info.start_time.isoformat(),
            "restart_count": self.info.restart_count,
            "uptime": (datetime.now() - self.info.start_time).total_seconds()
        }


class ProcessManager:
    """Manages multiple agent processes."""

    def __init__(self, state_file: str = ".agent_processes.json"):
        """Initialize process manager.

        Args:
            state_file: File to persist process state.
        """
        self.processes: Dict[str, AgentProcess] = {}
        self.state_file = state_file

    def register_agent(
        self,
        agent_class: Type[Agent],
        agent_id: str,
        agent_kwargs: Optional[Dict] = None,
        auto_start: bool = True
    ) -> AgentProcess:
        """Register an agent for management.

        Args:
            agent_class: The Agent subclass.
            agent_id: Unique identifier.
            agent_kwargs: Constructor arguments.
            auto_start: Whether to start immediately.

        Returns:
            The AgentProcess wrapper.
        """
        if agent_id in self.processes:
            raise ValueError(f"Agent {agent_id} already registered")

        agent_process = AgentProcess(
            agent_class=agent_class,
            agent_id=agent_id,
            agent_kwargs=agent_kwargs
        )

        self.processes[agent_id] = agent_process

        if auto_start:
            agent_process.start()

        self._save_state()
        return agent_process

    def unregister_agent(self, agent_id: str, stop: bool = True) -> bool:
        """Unregister an agent.

        Args:
            agent_id: Agent identifier.
            stop: Whether to stop the process.

        Returns:
            True if unregistered successfully.
        """
        if agent_id not in self.processes:
            return False

        agent_process = self.processes[agent_id]

        if stop:
            agent_process.stop()

        del self.processes[agent_id]
        self._save_state()
        return True

    def start_agent(self, agent_id: str) -> bool:
        """Start a specific agent."""
        if agent_id not in self.processes:
            return False
        return self.processes[agent_id].start()

    def stop_agent(self, agent_id: str, timeout: float = 10.0) -> bool:
        """Stop a specific agent."""
        if agent_id not in self.processes:
            return False
        return self.processes[agent_id].stop(timeout)

    def restart_agent(self, agent_id: str) -> bool:
        """Restart a specific agent."""
        if agent_id not in self.processes:
            return False
        return self.processes[agent_id].restart()

    def start_all(self) -> Dict[str, bool]:
        """Start all registered agents."""
        results = {}
        for agent_id, agent_process in self.processes.items():
            results[agent_id] = agent_process.start()
        return results

    def stop_all(self, timeout: float = 10.0) -> Dict[str, bool]:
        """Stop all agents."""
        results = {}
        for agent_id, agent_process in self.processes.items():
            results[agent_id] = agent_process.stop(timeout)
        return results

    def check_health(self) -> Dict[str, Dict]:
        """Check health of all agents."""
        health = {}
        for agent_id, agent_process in self.processes.items():
            status = agent_process.get_status()
            is_alive = agent_process.is_alive()

            health[agent_id] = {
                **status,
                "healthy": is_alive,
                "needs_restart": not is_alive and agent_process.auto_restart
            }

            # Auto-restart if needed
            if not is_alive and agent_process.auto_restart:
                print(f"Auto-restarting agent {agent_id}")
                agent_process.restart()

        return health

    def get_status(self) -> Dict[str, Dict]:
        """Get status of all agents."""
        return {
            agent_id: agent_process.get_status()
            for agent_id, agent_process in self.processes.items()
        }

    def _save_state(self):
        """Save process state to file."""
        state = {
            "processes": {
                agent_id: {
                    "agent_type": proc.agent_class.__name__,
                    "agent_id": proc.agent_id,
                    "auto_restart": proc.auto_restart,
                    "max_restarts": proc.max_restarts,
                }
                for agent_id, proc in self.processes.items()
            },
            "timestamp": datetime.now().isoformat()
        }
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"Failed to save state: {e}")

    def load_state(self) -> bool:
        """Load process state from file."""
        try:
            if not os.path.exists(self.state_file):
                return False

            with open(self.state_file, 'r') as f:
                state = json.load(f)

            # Note: This only restores state info, not actual processes
            # Agent classes would need to be dynamically imported
            return True
        except Exception as e:
            print(f"Failed to load state: {e}")
            return False

    def cleanup(self):
        """Clean up resources and stop all agents."""
        self.stop_all()
        self.processes.clear()
        if os.path.exists(self.state_file):
            os.remove(self.state_file)
