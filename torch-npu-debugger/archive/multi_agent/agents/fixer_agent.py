# Fixer agent for implementing fixes
# All comments in this file are in English per project guidelines

import os
import sys
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ..core import Agent, AgentCapability, AgentState
from ..messaging import Message, MessageType


class FixerAgent(Agent):
    """Agent responsible for implementing fixes.

    This agent:
    - Generates fixes based on location results
    - Applies fix patterns from references/fix_patterns.md
    - Produces patches for verifier agent
    """

    def __init__(
        self,
        agent_id: str = "fixer",
        message_bus=None,
        workspace: str = "."
    ):
        """Initialize fixer agent."""
        super().__init__(
            agent_id=agent_id,
            capabilities=[AgentCapability.FIX],
            message_bus=message_bus
        )
        self.workspace = Path(workspace).resolve()
        self._register_handlers()

    def _register_handlers(self):
        """Register message handlers."""
        self.register_handler(MessageType.LOCATION_RESULT, self._handle_location_result)
        self.register_handler(MessageType.TASK_ASSIGN, self._handle_fix_task)

    def _handle_specialized(self, message):
        """Handle specialized messages."""
        pass

    def _handle_location_result(self, task_id: str, payload: Dict) -> Dict:
        """Handle location results."""
        fix_task_id = f"{task_id}_fix"

        self.send_message(
            recipient="coordinator",
            message_type=MessageType.TASK_CREATE,
            payload={
                "task_id": fix_task_id,
                "task_type": "fix",
                "locations": payload.get("locations", []),
                "scope": payload.get("scope", {}),
                "required_capabilities": [AgentCapability.FIX.value],
                "priority": 5
            }
        )

        return {"created": fix_task_id}

    def _handle_fix_task(self, task_id: str, payload: Dict) -> Dict:
        """Handle fix task assignment."""
        self.logger.info(f"Starting fix for task {task_id}")
        self.transition_to(AgentState.WORKING, f"Fixing {task_id}")
        self.current_task = task_id

        try:
            locations = payload.get("locations", [])
            scope = payload.get("scope", {})

            # Generate fix
            fix_result = self._generate_fix(locations, scope, task_id)

            # Send results
            self.send_message(
                recipient="coordinator",
                message_type=MessageType.FIX_RESULT,
                payload={
                    "task_id": task_id,
                    "agent_id": self.agent_id,
                    "fix": fix_result,
                    "workflow_step": "fix"
                }
            )

            self.send_message(
                recipient="coordinator",
                message_type=MessageType.TASK_COMPLETE,
                payload={
                    "task_id": task_id,
                    "agent_id": self.agent_id,
                    "result": fix_result,
                    "workflow_step": "fix"
                }
            )

            self.metrics.tasks_completed += 1
            self.transition_to(AgentState.IDLE, "Fix complete")

            return {"success": True, "fix": fix_result}

        except Exception as e:
            self.logger.error(f"Fix failed: {e}")
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

    def _generate_fix(
        self,
        locations: List[Dict],
        scope: Dict,
        task_id: str
    ) -> Dict:
        """Generate fix based on locations and scope."""
        fix_type = scope.get("suggested_fix_type", "general")

        fix_generators = {
            "dispatch_registration": self._fix_dispatch_registration,
            "aclnn_implementation": self._fix_aclnn_implementation,
            "operator_registration": self._fix_operator_registration,
            "format_handling": self._fix_format_handling,
            "precision_adjustment": self._fix_precision,
            "fallback_implementation": self._fix_fallback,
        }

        generator = fix_generators.get(fix_type, self._fix_general)
        return generator(locations, scope, task_id)

    def _fix_dispatch_registration(
        self,
        locations: List[Dict],
        scope: Dict,
        task_id: str
    ) -> Dict:
        """Generate fix for dispatch registration issues."""
        self.logger.info("Generating dispatch registration fix")

        patches = []
        for loc in locations:
            file_path = loc.get("file", "")
            if "codegen" in file_path or "DispatchStub" in str(loc):
                patches.append({
                    "file": file_path,
                    "description": "Add dispatch key registration",
                    "template": "DISPATCH_KEY_REGISTRATION"
                })

        return {
            "fix_type": "dispatch_registration",
            "patches": patches,
            "requires_rebuild": True,
            "manual_review": True
        }

    def _fix_aclnn_implementation(
        self,
        locations: List[Dict],
        scope: Dict,
        task_id: str
    ) -> Dict:
        """Generate fix for ACLNN implementation issues."""
        self.logger.info("Generating ACLNN implementation fix")

        patches = []
        for loc in locations:
            file_path = loc.get("file", "")
            operator = loc.get("operator", "")

            patches.append({
                "file": file_path,
                "description": f"Fix {operator} ACLNN implementation",
                "template": "ACLNN_FIX_TEMPLATE",
                "operator": operator
            })

        return {
            "fix_type": "aclnn_implementation",
            "patches": patches,
            "requires_rebuild": True,
            "manual_review": True
        }

    def _fix_operator_registration(
        self,
        locations: List[Dict],
        scope: Dict,
        task_id: str
    ) -> Dict:
        """Generate fix for operator registration."""
        self.logger.info("Generating operator registration fix")

        return {
            "fix_type": "operator_registration",
            "patches": [{
                "description": "Add missing operator registration",
                "template": "TORCH_LIBRARY_IMPL_REGISTRATION"
            }],
            "requires_rebuild": True,
            "manual_review": True
        }

    def _fix_format_handling(
        self,
        locations: List[Dict],
        scope: Dict,
        task_id: str
    ) -> Dict:
        """Generate fix for format handling."""
        self.logger.info("Generating format handling fix")

        return {
            "fix_type": "format_handling",
            "patches": [{
                "description": "Fix format conversion",
                "template": "FORMAT_CONVERSION_FIX"
            }],
            "requires_rebuild": True,
            "manual_review": True
        }

    def _fix_precision(
        self,
        locations: List[Dict],
        scope: Dict,
        task_id: str
    ) -> Dict:
        """Generate fix for precision issues."""
        self.logger.info("Generating precision fix")

        return {
            "fix_type": "precision_adjustment",
            "patches": [{
                "description": "Adjust precision handling",
                "template": "PRECISION_FIX_TEMPLATE"
            }],
            "requires_rebuild": True,
            "manual_review": True
        }

    def _fix_fallback(
        self,
        locations: List[Dict],
        scope: Dict,
        task_id: str
    ) -> Dict:
        """Generate fix for fallback implementation."""
        self.logger.info("Generating fallback fix")

        return {
            "fix_type": "fallback_implementation",
            "patches": [{
                "description": "Add DO_COMPATIBILITY fallback",
                "template": "DO_COMPATIBILITY_FALLBACK"
            }],
            "requires_rebuild": True,
            "manual_review": True
        }

    def _fix_general(
        self,
        locations: List[Dict],
        scope: Dict,
        task_id: str
    ) -> Dict:
        """Generate general fix."""
        self.logger.info("Generating general fix")

        return {
            "fix_type": "general",
            "patches": [{
                "description": "General fix based on analysis",
                "files": [loc.get("file") for loc in locations],
                "manual_review": True
            }],
            "requires_rebuild": True,
            "manual_review": True
        }

    def _run(self):
        """Main agent loop."""
        self.logger.info("Fixer agent started, waiting for tasks")

        while not self._stop_event.is_set():
            self._stop_event.wait(1)

        self.logger.info("Fixer agent stopped")
