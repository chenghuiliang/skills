# Locator agent for source code location
# All comments in this file are in English per project guidelines

import os
import sys
import subprocess
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ..core import Agent, AgentCapability, AgentState
from ..messaging import Message, MessageType


class LocatorAgent(Agent):
    """Agent responsible for locating source code related to issues.

    This agent:
    - Searches for operator implementations based on scoping results
    - Navigates the codebase to find relevant files
    - Produces file locations for fixer agent
    """

    def __init__(
        self,
        agent_id: str = "locator",
        message_bus=None,
        workspace: str = "."
    ):
        """Initialize locator agent."""
        super().__init__(
            agent_id=agent_id,
            capabilities=[AgentCapability.LOCATE],
            message_bus=message_bus
        )
        self.workspace = Path(workspace).resolve()
        self._register_handlers()

    def _register_handlers(self):
        """Register message handlers."""
        self.register_handler(MessageType.SCOPE_RESULT, self._handle_scope_result)
        self.register_handler(MessageType.TASK_ASSIGN, self._handle_locate_task)

    def _handle_specialized(self, message: Message):
        """Handle specialized messages."""
        pass

    def _handle_scope_result(self, task_id: str, payload: Dict) -> Dict:
        """Handle scoping results."""
        scope = payload.get("scope", {})

        locate_task_id = f"{task_id}_locate"

        self.send_message(
            recipient="coordinator",
            message_type=MessageType.TASK_CREATE,
            payload={
                "task_id": locate_task_id,
                "task_type": "location",
                "scope": scope,
                "required_capabilities": [AgentCapability.LOCATE.value],
                "priority": 5
            }
        )

        return {"created": locate_task_id}

    def _handle_locate_task(self, task_id: str, payload: Dict) -> Dict:
        """Handle location task assignment."""
        self.logger.info(f"Starting location for task {task_id}")
        self.transition_to(AgentState.WORKING, f"Locating {task_id}")
        self.current_task = task_id

        try:
            scope = payload.get("scope", {})
            search_paths = scope.get("search_paths", [])
            operator_names = payload.get("operator_names", [])

            # Search for source files
            locations = self._locate_source_files(scope, operator_names)

            # Send results
            self.send_message(
                recipient="coordinator",
                message_type=MessageType.LOCATION_RESULT,
                payload={
                    "task_id": task_id,
                    "agent_id": self.agent_id,
                    "locations": locations,
                    "workflow_step": "location"
                }
            )

            self.send_message(
                recipient="coordinator",
                message_type=MessageType.TASK_COMPLETE,
                payload={
                    "task_id": task_id,
                    "agent_id": self.agent_id,
                    "result": locations,
                    "workflow_step": "location"
                }
            )

            self.metrics.tasks_completed += 1
            self.transition_to(AgentState.IDLE, "Location complete")

            return {"success": True, "locations": locations}

        except Exception as e:
            self.logger.error(f"Location failed: {e}")
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

    def _locate_source_files(
        self,
        scope: Dict,
        operator_names: List[str]
    ) -> List[Dict]:
        """Locate source files based on scope."""
        locations = []
        search_paths = scope.get("search_paths", [])
        issue_layer = scope.get("issue_layer", "unknown")

        # Default paths if none specified
        if not search_paths:
            search_paths = [
                "third_party/op-plugin/op_plugin/ops/",
                "torch_npu/csrc/"
            ]

        # Search for operator implementations
        for op_name in operator_names:
            op_locations = self._search_operator(op_name, search_paths, issue_layer)
            locations.extend(op_locations)

        # If no operators found, search based on layer
        if not locations:
            layer_locations = self._search_by_layer(issue_layer, search_paths)
            locations.extend(layer_locations)

        return locations

    def _search_operator(
        self,
        op_name: str,
        search_paths: List[str],
        issue_layer: str
    ) -> List[Dict]:
        """Search for operator implementation."""
        locations = []

        for search_path in search_paths:
            full_path = self.workspace / search_path
            if not full_path.exists():
                continue

            try:
                # Use ripgrep for searching
                cmd = [
                    "rg", "-l", "-g", "*.cpp", "-g", "*.h", "-g", "*.py",
                    op_name, str(full_path)
                ]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode == 0:
                    for file_path in result.stdout.strip().split('\n')[:10]:
                        if file_path:
                            locations.append({
                                "file": file_path,
                                "operator": op_name,
                                "type": self._get_file_type(file_path),
                                "search_path": search_path
                            })

            except Exception as e:
                self.logger.warning(f"Search failed for {op_name}: {e}")

        return locations

    def _search_by_layer(self, issue_layer: str, search_paths: List[str]) -> List[Dict]:
        """Search for files based on issue layer."""
        locations = []

        layer_patterns = {
            "registration": ["TORCH_LIBRARY", "TORCH_LIBRARY_IMPL", "DispatchStub"],
            "aclnn": ["aclnn", "EXEC_NPU_CMD"],
            "aclops": ["aclnn", "OpCommand"],
            "format": ["FormatHelper", "TransData"],
            "runtime": ["NPUStream", "NPUEvent", "CachingAllocator"],
        }

        patterns = layer_patterns.get(issue_layer, [])

        for search_path in search_paths:
            full_path = self.workspace / search_path
            if not full_path.exists():
                continue

            for pattern in patterns:
                try:
                    cmd = [
                        "rg", "-l", "-g", "*.cpp", "-g", "*.h",
                        pattern, str(full_path)
                    ]
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )

                    if result.returncode == 0:
                        for file_path in result.stdout.strip().split('\n')[:5]:
                            if file_path:
                                locations.append({
                                    "file": file_path,
                                    "pattern": pattern,
                                    "type": self._get_file_type(file_path),
                                    "search_path": search_path
                                })

                except Exception:
                    continue

        return locations

    def _get_file_type(self, file_path: str) -> str:
        """Determine file type."""
        ext = Path(file_path).suffix
        return {
            '.py': 'python',
            '.cpp': 'cpp',
            '.h': 'header',
            '.hpp': 'header',
        }.get(ext, 'unknown')

    def _run(self):
        """Main agent loop."""
        self.logger.info("Locator agent started, waiting for tasks")

        while not self._stop_event.is_set():
            self._stop_event.wait(1)

        self.logger.info("Locator agent stopped")
