# Analyzer agent for problem analysis
# All comments in this file are in English per project guidelines

import os
import sys
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ..core import Agent, AgentCapability, AgentState
from ..messaging import Message, MessageType


class AnalyzerAgent(Agent):
    """Agent responsible for analyzing torch_npu issues.

    This agent:
    - Extracts error information from logs
    - Identifies error patterns and categories
    - Gathers environment information
    - Produces structured analysis for downstream agents
    """

    def __init__(
        self,
        agent_id: str = "analyzer",
        message_bus=None,
        references_dir: str = "references"
    ):
        """Initialize analyzer agent.

        Args:
            agent_id: Agent identifier.
            message_bus: Message bus for communication.
            references_dir: Directory containing reference documentation.
        """
        super().__init__(
            agent_id=agent_id,
            capabilities=[AgentCapability.ANALYZE],
            message_bus=message_bus
        )
        self.references_dir = references_dir
        self._register_handlers()

    def _register_handlers(self):
        """Register message handlers."""
        self.register_handler(MessageType.TASK_ASSIGN, self._handle_analysis_task)

    def _handle_specialized(self, message: Message):
        """Handle specialized messages."""
        pass

    def _handle_analysis_task(self, task_id: str, payload: Dict) -> Dict:
        """Handle analysis task assignment."""
        self.logger.info(f"Starting analysis for task {task_id}")
        self.transition_to(AgentState.WORKING, f"Analyzing {task_id}")
        self.current_task = task_id

        try:
            issue = payload.get("issue", {})

            # Perform analysis
            analysis = self._analyze_issue(issue)

            # Report progress
            self.report_progress(50, "Analysis complete, sending results")

            # Send results to coordinator
            self.send_message(
                recipient="coordinator",
                message_type=MessageType.ANALYSIS_RESULT,
                payload={
                    "task_id": task_id,
                    "agent_id": self.agent_id,
                    "analysis": analysis,
                    "workflow_step": "analysis"
                }
            )

            # Complete task
            self.send_message(
                recipient="coordinator",
                message_type=MessageType.TASK_COMPLETE,
                payload={
                    "task_id": task_id,
                    "agent_id": self.agent_id,
                    "result": analysis,
                    "workflow_step": "analysis"
                }
            )

            self.metrics.tasks_completed += 1
            self.transition_to(AgentState.IDLE, "Analysis complete")

            return {"success": True, "analysis": analysis}

        except Exception as e:
            self.logger.error(f"Analysis failed: {e}")
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

    def _analyze_issue(self, issue: Dict) -> Dict:
        """Perform comprehensive issue analysis.

        Args:
            issue: Issue description with error logs, environment, etc.

        Returns:
            Structured analysis result.
        """
        error_log = issue.get("error_log", "")
        description = issue.get("description", "")

        analysis = {
            "problem_summary": self._extract_summary(description),
            "error_patterns": self._identify_error_patterns(error_log),
            "environment_info": self._extract_environment(issue),
            "affected_components": self._identify_components(error_log, description),
            "extracted_info": self._extract_key_info(error_log),
            "timestamp": datetime.now().isoformat()
        }

        return analysis

    def _extract_summary(self, description: str) -> str:
        """Extract brief problem summary."""
        lines = description.strip().split('\n')
        first_line = lines[0] if lines else description
        return first_line[:200] if len(first_line) > 200 else first_line

    def _identify_error_patterns(self, error_log: str) -> List[Dict]:
        """Identify error patterns in the log."""
        patterns = []
        log_lower = error_log.lower()

        # Pattern definitions
        error_patterns = [
            (r'ACL_ERROR_\w+', 'ACL Error', 'critical'),
            (r'acl[nN]n\w+', 'ACLNN API Error', 'high'),
            (r'NotImplementedError', 'Missing Implementation', 'high'),
            (r'expected_k._equalsBoxedAndUnboxed', 'Dispatch Key Conflict', 'critical'),
            (r'DO_COMPATIBILITY', 'Compatibility Fallback', 'medium'),
            (r'OpCommand', 'OpCommand Error', 'high'),
            (r'format mismatch', 'Format Conversion Error', 'high'),
            (r'allclose failed', 'Precision Issue', 'medium'),
            (r'SIGSEGV|segmentation fault', 'Runtime Crash', 'critical'),
            (r'HCCL|EJ0001', 'Distributed Communication Error', 'high'),
            (r'undefined symbol', 'Symbol Resolution Error', 'high'),
        ]

        for pattern, label, severity in error_patterns:
            matches = re.findall(pattern, error_log)
            if matches:
                patterns.append({
                    "pattern": pattern,
                    "label": label,
                    "severity": severity,
                    "matches": list(set(matches))[:5]  # Limit matches
                })

        return patterns

    def _extract_environment(self, issue: Dict) -> Dict:
        """Extract environment information."""
        return {
            "torch_npu_version": issue.get("torch_npu_version", "unknown"),
            "cann_version": issue.get("cann_version", "unknown"),
            "pytorch_version": issue.get("pytorch_version", "unknown"),
            "device_model": issue.get("device_model", "unknown"),
            "python_version": issue.get("python_version", "unknown"),
            "os": issue.get("os", "unknown"),
        }

    def _identify_components(self, error_log: str, description: str) -> List[str]:
        """Identify affected components."""
        components = []
        combined = (error_log + " " + description).lower()

        component_map = {
            "opapi": "ACLNN Operator",
            "aclops": "ACL Operator",
            "op-plugin": "Operator Plugin",
            "op_command": "OpCommand Framework",
            "formathelper": "Format Handling",
            "dtype": "Data Type Handling",
            "dispatch": "Dispatch System",
            "registration": "Operator Registration",
            "hccl": "Distributed Communication",
            "atb": "ATB Operator",
        }

        for keyword, component in component_map.items():
            if keyword in combined:
                components.append(component)

        return components if components else ["Unknown Component"]

    def _extract_key_info(self, error_log: str) -> Dict:
        """Extract key information from error log."""
        info = {
            "operator_names": [],
            "file_paths": [],
            "line_numbers": [],
            "error_codes": []
        }

        # Extract operator names
        op_pattern = r'at::(\w+)|torch\.(\w+)|aclnn(\w+)'
        op_matches = re.findall(op_pattern, error_log)
        info["operator_names"] = list(set([
            m[0] or m[1] or m[2] for m in op_matches if any(m)
        ]))[:10]

        # Extract file paths
        file_pattern = r'([\w/]+\.(?:py|cpp|h|hpp))'
        info["file_paths"] = list(set(re.findall(file_pattern, error_log)))[:5]

        # Extract error codes
        code_pattern = r'(ACL_ERROR_\w+|0x[0-9a-fA-F]+|\d{6})'
        info["error_codes"] = list(set(re.findall(code_pattern, error_log)))[:5]

        return info

    def _run(self):
        """Main agent loop."""
        self.logger.info("Analyzer agent started, waiting for tasks")

        while not self._stop_event.is_set():
            self._stop_event.wait(1)

        self.logger.info("Analyzer agent stopped")
