# Scoping agent for issue boundary determination
# All comments in this file are in English per project guidelines

import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ..core import Agent, AgentCapability, AgentState
from ..messaging import Message, MessageType


class ScopingAgent(Agent):
    """Agent responsible for determining the scope/boundary of issues.

    This agent:
    - Analyzes analysis results to determine which layer has the issue
    - Uses decision tree from issue_patterns.md
    - Produces scoping conclusion for locator agent
    """

    def __init__(
        self,
        agent_id: str = "scoping",
        message_bus=None
    ):
        """Initialize scoping agent."""
        super().__init__(
            agent_id=agent_id,
            capabilities=[AgentCapability.SCOPE],
            message_bus=message_bus
        )
        self._register_handlers()

    def _register_handlers(self):
        """Register message handlers."""
        self.register_handler(MessageType.ANALYSIS_RESULT, self._handle_analysis_result)
        self.register_handler(MessageType.TASK_ASSIGN, self._handle_scoping_task)

    def _handle_specialized(self, message: Message):
        """Handle specialized messages."""
        pass

    def _handle_analysis_result(self, task_id: str, payload: Dict) -> Dict:
        """Handle analysis results from analyzer."""
        analysis = payload.get("analysis", {})

        # Create scoping task
        scoping_task_id = f"{task_id}_scope"

        self.send_message(
            recipient="coordinator",
            message_type=MessageType.TASK_CREATE,
            payload={
                "task_id": scoping_task_id,
                "task_type": "scoping",
                "analysis": analysis,
                "required_capabilities": [AgentCapability.SCOPE.value],
                "priority": 5
            }
        )

        return {"created": scoping_task_id}

    def _handle_scoping_task(self, task_id: str, payload: Dict) -> Dict:
        """Handle scoping task assignment."""
        self.logger.info(f"Starting scoping for task {task_id}")
        self.transition_to(AgentState.WORKING, f"Scoping {task_id}")
        self.current_task = task_id

        try:
            analysis = payload.get("analysis", {})
            error_patterns = analysis.get("error_patterns", [])
            components = analysis.get("affected_components", [])

            # Perform scoping
            scope = self._determine_scope(error_patterns, components, analysis)

            # Send results
            self.send_message(
                recipient="coordinator",
                message_type=MessageType.SCOPE_RESULT,
                payload={
                    "task_id": task_id,
                    "agent_id": self.agent_id,
                    "scope": scope,
                    "workflow_step": "scoping"
                }
            )

            self.send_message(
                recipient="coordinator",
                message_type=MessageType.TASK_COMPLETE,
                payload={
                    "task_id": task_id,
                    "agent_id": self.agent_id,
                    "result": scope,
                    "workflow_step": "scoping"
                }
            )

            self.metrics.tasks_completed += 1
            self.transition_to(AgentState.IDLE, "Scoping complete")

            return {"success": True, "scope": scope}

        except Exception as e:
            self.logger.error(f"Scoping failed: {e}")
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

    def _determine_scope(
        self,
        error_patterns: List[Dict],
        components: List[str],
        analysis: Dict
    ) -> Dict:
        """Determine the scope of the issue.

        Returns:
            Scope determination with layer, priority, and search paths.
        """
        scope = {
            "issue_layer": "unknown",
            "priority": "normal",
            "search_paths": [],
            "suggested_fix_type": "unknown",
            "reasoning": []
        }

        # Extract labels from patterns
        labels = [p.get("label", "") for p in error_patterns]
        severities = [p.get("severity", "low") for p in error_patterns]

        # Determine layer based on error patterns
        if "Dispatch Key Conflict" in labels:
            scope["issue_layer"] = "registration"
            scope["priority"] = "critical"
            scope["search_paths"] = [
                "third_party/op-plugin/codegen/",
                "torch_npu/csrc/aten/",
            ]
            scope["suggested_fix_type"] = "dispatch_registration"
            scope["reasoning"].append("Dispatch key conflict detected")

        elif "ACL Error" in labels or "ACLNN API Error" in labels:
            scope["issue_layer"] = "aclnn"
            scope["priority"] = "high"
            scope["search_paths"] = [
                "third_party/op-plugin/op_plugin/ops/opapi/",
            ]
            scope["suggested_fix_type"] = "aclnn_implementation"
            scope["reasoning"].append("ACLNN layer error detected")

        elif "Missing Implementation" in labels:
            scope["issue_layer"] = "registration"
            scope["priority"] = "high"
            scope["search_paths"] = [
                "third_party/op-plugin/op_plugin/ops/",
                "third_party/op-plugin/codegen/",
            ]
            scope["suggested_fix_type"] = "operator_registration"
            scope["reasoning"].append("Operator not implemented")

        elif "Format Conversion Error" in labels:
            scope["issue_layer"] = "format"
            scope["priority"] = "high"
            scope["search_paths"] = [
                "torch_npu/csrc/framework/FormatHelper.cpp",
                "torch_npu/csrc/aten/",
            ]
            scope["suggested_fix_type"] = "format_handling"
            scope["reasoning"].append("Format conversion issue detected")

        elif "Precision Issue" in labels:
            scope["issue_layer"] = "precision"
            scope["priority"] = "medium"
            scope["search_paths"] = [
                "third_party/op-plugin/op_plugin/ops/opapi/",
                "third_party/op-plugin/op_plugin/ops/aclops/",
            ]
            scope["suggested_fix_type"] = "precision_adjustment"
            scope["reasoning"].append("Precision mismatch detected")

        elif "Runtime Crash" in labels:
            scope["issue_layer"] = "runtime"
            scope["priority"] = "critical"
            scope["search_paths"] = [
                "torch_npu/csrc/core/npu/",
                "torch_npu/csrc/framework/",
            ]
            scope["suggested_fix_type"] = "runtime_fix"
            scope["reasoning"].append("Runtime crash detected")

        elif "Compatibility Fallback" in labels:
            scope["issue_layer"] = "fallback"
            scope["priority"] = "medium"
            scope["search_paths"] = [
                "third_party/op-plugin/op_plugin/ops/opapi/",
                "third_party/op-plugin/op_plugin/ops/aclops/",
            ]
            scope["suggested_fix_type"] = "fallback_implementation"
            scope["reasoning"].append("DO_COMPATIBILITY fallback detected")

        else:
            # Default based on components
            if "ACLNN Operator" in components:
                scope["issue_layer"] = "aclnn"
                scope["search_paths"] = ["third_party/op-plugin/op_plugin/ops/opapi/"]
            elif "ACL Operator" in components:
                scope["issue_layer"] = "aclops"
                scope["search_paths"] = ["third_party/op-plugin/op_plugin/ops/aclops/"]
            elif "Format Handling" in components:
                scope["issue_layer"] = "format"
                scope["search_paths"] = ["torch_npu/csrc/framework/"]
            else:
                scope["issue_layer"] = "unknown"
                scope["search_paths"] = [
                    "third_party/op-plugin/",
                    "torch_npu/csrc/"
                ]

        # Adjust priority based on severity
        if "critical" in severities:
            scope["priority"] = "critical"
        elif "high" in severities:
            scope["priority"] = "high"

        scope["timestamp"] = datetime.now().isoformat()
        return scope

    def _run(self):
        """Main agent loop."""
        self.logger.info("Scoping agent started, waiting for tasks")

        while not self._stop_event.is_set():
            self._stop_event.wait(1)

        self.logger.info("Scoping agent stopped")
