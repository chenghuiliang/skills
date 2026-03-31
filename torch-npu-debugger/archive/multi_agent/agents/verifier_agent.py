# Verifier agent for testing and verification
# All comments in this file are in English per project guidelines

import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ..core.remote_agent import RemoteCapableAgent, AgentCapability, AgentState
from ..messaging import Message, MessageType
from ..config.remote_config import RemoteConfig, get_remote_config


class VerifierAgent(RemoteCapableAgent):
    """Agent responsible for verifying fixes on remote Ascend servers.

    This agent uses the remote module to:
    - Apply patches to code on remote server
    - Compile torch_npu on remote server
    - Run tests on NPU hardware
    - Report verification results

    Must be configured with remote server details via:
    - Constructor parameters
    - Environment variables (TORCH_NPU_REMOTE_HOST, etc.)
    - Config file (~/.config/torch-npu-debugger/remote.json)
    """

    def __init__(
        self,
        agent_id: str = "verifier",
        message_bus=None,
        remote_config: Optional[RemoteConfig] = None,
        # Remote connection parameters (if not using remote_config)
        remote_host: Optional[str] = None,
        remote_user: Optional[str] = None,
        remote_key_path: Optional[str] = None,
        env_setup_script: Optional[str] = None,
        remote_work_dir: str = "~/torch_npu",
        test_timeout: int = 600,
        compile_timeout: int = 3600,
        # Docker mode parameters
        use_docker: bool = False,
        docker_container: Optional[str] = None,
        docker_work_dir: str = "/home/lch/work/torch_npu",
        python_version: str = "3.10"
    ):
        """Initialize verifier agent with remote capabilities.

        Args:
            agent_id: Unique identifier for this agent
            message_bus: Message bus for communication
            remote_config: Pre-configured RemoteConfig object
            remote_host: Remote server host (e.g., "user@server")
            remote_user: SSH username
            remote_key_path: Path to SSH private key
            env_setup_script: Environment setup command
            remote_work_dir: Working directory on remote server
            test_timeout: Timeout for test execution in seconds
            compile_timeout: Timeout for compilation in seconds
            use_docker: Whether to use Docker container for compilation
            docker_container: Docker container name (e.g., "lch_test")
            docker_work_dir: Working directory inside Docker container
            python_version: Python version for build (e.g., "3.10")
        """
        # Load or create remote configuration
        if remote_config is not None:
            config = remote_config
        elif remote_host:
            config = get_remote_config(
                host=remote_host,
                user=remote_user,
                key_path=remote_key_path,
                env_script=env_setup_script,
                working_dir=remote_work_dir
            )
        else:
            # Try to load from environment or config file
            try:
                config = RemoteConfig.from_env()
            except ValueError:
                raise ValueError(
                    "Remote configuration required for VerifierAgent. "
                    "Provide remote_config, remote_host parameter, or set "
                    "TORCH_NPU_REMOTE_HOST environment variable."
                )

        # Initialize remote-capable base class
        super().__init__(
            agent_id=agent_id,
            capabilities=[AgentCapability.VERIFY],
            message_bus=message_bus,
            remote_host=config.host,
            remote_user=config.user,
            remote_key_path=config.key_path,
            env_setup_script=config.env_setup_script,
            remote_work_dir=config.working_dir,
            use_docker=use_docker,
            docker_container=docker_container,
            docker_work_dir=docker_work_dir,
            command_timeout=config.command_timeout
        )

        self.config = config
        self.test_timeout = test_timeout
        self.compile_timeout = compile_timeout
        self.python_version = python_version

        self._register_handlers()

    def _register_handlers(self):
        """Register message handlers."""
        self.register_handler(MessageType.FIX_RESULT, self._handle_fix_result)
        self.register_handler(MessageType.TASK_ASSIGN, self._handle_verify_task)

    def _handle_specialized(self, message):
        """Handle specialized messages."""
        pass

    def _handle_fix_result(self, task_id: str, payload: Dict) -> Dict:
        """Handle fix results."""
        verify_task_id = f"{task_id}_verify"

        self.send_message(
            recipient="coordinator",
            message_type=MessageType.TASK_CREATE,
            payload={
                "task_id": verify_task_id,
                "task_type": "verify",
                "fix": payload.get("fix", {}),
                "required_capabilities": [AgentCapability.VERIFY.value],
                "priority": 5
            }
        )

        return {"created": verify_task_id}

    def _handle_verify_task(self, task_id: str, payload: Dict) -> Dict:
        """Handle verification task assignment."""
        self.logger.info(f"Starting verification for task {task_id}")
        self.transition_to(AgentState.WORKING, f"Verifying {task_id}")
        self.current_task = task_id

        try:
            # Verify remote environment first
            self.report_progress(5, "Connecting to remote server...")
            env_info = self.verify_remote_environment()

            if not env_info.connected:
                raise ConnectionError("Failed to connect to remote server")

            self.report_progress(10, f"Connected to {env_info.host}")

            fix = payload.get("fix", {})

            # Perform verification
            verification = self._verify_fix(fix, task_id)

            # Send results
            self.send_message(
                recipient="coordinator",
                message_type=MessageType.VERIFY_RESULT,
                payload={
                    "task_id": task_id,
                    "agent_id": self.agent_id,
                    "verification": verification,
                    "workflow_step": "verify"
                }
            )

            # Complete or fail based on verification
            if verification.get("success"):
                self.send_message(
                    recipient="coordinator",
                    message_type=MessageType.TASK_COMPLETE,
                    payload={
                        "task_id": task_id,
                        "agent_id": self.agent_id,
                        "result": verification,
                        "workflow_step": "verify"
                    }
                )
                self.metrics.tasks_completed += 1
            else:
                self.send_message(
                    recipient="coordinator",
                    message_type=MessageType.TASK_FAIL,
                    payload={
                        "task_id": task_id,
                        "agent_id": self.agent_id,
                        "error": verification.get("error", "Verification failed")
                    }
                )
                self.metrics.tasks_failed += 1

            self.transition_to(AgentState.IDLE, "Verification complete")

            return {"success": verification.get("success"), "verification": verification}

        except Exception as e:
            self.logger.error(f"Verification failed: {e}")
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

    def _verify_fix(self, fix: Dict, task_id: str) -> Dict:
        """Verify the fix by compiling and testing on remote server."""
        verification = {
            "success": False,
            "stages": {},
            "error": None
        }

        # Stage 1: Apply patch
        self.logger.info("Stage 1: Applying patch on remote server")
        self.report_progress(15, "Applying patch on remote server...")

        patch_result = self._apply_patch(fix)
        verification["stages"]["apply_patch"] = patch_result

        if not patch_result.get("success"):
            verification["error"] = f"Patch application failed: {patch_result.get('error')}"
            return verification

        # Stage 2: Compile
        if fix.get("requires_rebuild", True):
            self.logger.info("Stage 2: Compiling on remote server")
            self.report_progress(30, "Compiling on remote server...")

            compile_result = self._compile_code()
            verification["stages"]["compile"] = compile_result

            if not compile_result.get("success"):
                verification["error"] = f"Compilation failed: {compile_result.get('error')}"
                return verification

        # Stage 3: Run tests
        self.logger.info("Stage 3: Running tests on remote server")
        self.report_progress(70, "Running tests on remote server...")

        test_result = self._run_tests(fix)
        verification["stages"]["test"] = test_result

        if not test_result.get("success"):
            verification["error"] = f"Tests failed: {test_result.get('error')}"
            return verification

        # All stages passed
        verification["success"] = True
        self.report_progress(100, "Verification complete")

        return verification

    def _apply_patch(self, fix: Dict) -> Dict:
        """Apply the fix patch on remote server."""
        patches = fix.get("patches", [])

        if not patches:
            self.logger.info("No patches to apply")
            return {"success": True, "patches_applied": 0}

        try:
            # Generate patch content from fix
            patch_content = self._generate_patch_content(fix)

            if not patch_content:
                return {"success": True, "patches_applied": 0}

            self.logger.info(f"Applying patch to {self.remote_work_dir}")

            # Apply patch using remote file manager
            success = self.apply_patch_remote(patch_content, self.remote_work_dir)

            if success:
                return {
                    "success": True,
                    "patches_applied": len(patches)
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to apply patch"
                }

        except Exception as e:
            self.logger.error(f"Patch application failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _generate_patch_content(self, fix: Dict) -> str:
        """Generate git patch content from fix data."""
        patches = fix.get("patches", [])

        if not patches:
            return ""

        # Build patch content
        patch_lines = []

        for patch in patches:
            file_path = patch.get("file", "")
            description = patch.get("description", "")
            changes = patch.get("changes", [])

            if not file_path or not changes:
                continue

            patch_lines.append(f"diff --git a/{file_path} b/{file_path}")
            patch_lines.append(f"--- a/{file_path}")
            patch_lines.append(f"+++ b/{file_path}")
            patch_lines.append(f"@@ -1 +1 @@")
            patch_lines.append(f"# {description}")

            # Add changes
            for change in changes:
                if change.get("type") == "add":
                    patch_lines.append(f"+{change.get('content', '')}")
                elif change.get("type") == "remove":
                    patch_lines.append(f"-{change.get('content', '')}")

        return "\n".join(patch_lines)

    def _compile_code(self) -> Dict:
        """Compile the code on remote server or inside Docker container."""
        if self.use_docker:
            return self._compile_in_docker()
        else:
            return self._compile_on_host()

    def _compile_in_docker(self) -> Dict:
        """Compile inside Docker container using incremental build."""
        self.logger.info(
            f"Starting compilation in Docker container: {self.docker_container}"
        )

        try:
            # Check if container is running
            docker = self.get_docker_executor()
            if not docker.is_container_running():
                self.logger.info(f"Starting container: {self.docker_container}")
                docker.start_container()

            self.report_progress(30, f"Compiling in container {self.docker_container}...")

            # Build compile command with python version
            compile_cmd = f"bash ci/build.sh --python={self.python_version}"

            # Execute compilation synchronously in container
            result = docker.execute_sync(
                command=compile_cmd,
                working_dir=self.docker_work_dir,
                timeout=self.compile_timeout
            )

            # Analyze compile result
            if result.exit_code == 0:
                self.report_progress(70, "Compilation successful")

                # Check build artifacts
                dist_dir = f"{self.docker_work_dir}/dist"

                return {
                    "success": True,
                    "duration": result.execution_time,
                    "output": result.stdout[:1000] if result.stdout else "",
                    "dist_dir": dist_dir,
                    "mode": "docker",
                    "container": self.docker_container
                }
            else:
                # Use result analyzer for detailed error analysis
                analyzer = self.get_result_analyzer()
                analysis = analyzer.analyze_compile_result({
                    "exit_code": result.exit_code,
                    "stdout": result.stdout,
                    "stderr": result.stderr
                })

                return {
                    "success": False,
                    "error": analysis.get("error_summary", "Compilation failed"),
                    "output": result.stdout[:2000] if result.stdout else "",
                    "stderr": result.stderr[:2000] if result.stderr else "",
                    "suggestions": analysis.get("suggestions", []),
                    "mode": "docker",
                    "container": self.docker_container
                }

        except Exception as e:
            self.logger.error(f"Docker compilation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "mode": "docker",
                "container": self.docker_container
            }

    def _compile_on_host(self) -> Dict:
        """Compile directly on remote host (async mode)."""
        self.logger.info("Starting compilation on remote server")

        try:
            # Start async compilation
            task_id = self.execute_remote_async(
                command="bash ci/build.sh",
                working_dir=self.remote_work_dir,
                timeout=self.compile_timeout
            )

            self.logger.info(f"Compilation started with task ID: {task_id}")

            # Wait for completion with progress updates
            last_progress = 30

            def progress_callback(status):
                nonlocal last_progress
                # Simulate progress from 30% to 70%
                if status.state.value == "RUNNING":
                    last_progress = min(last_progress + 2, 70)
                    self.report_progress(last_progress, f"Compiling: {status.message or 'in progress'}")

            result = self.wait_for_async_task(
                task_id=task_id,
                timeout=self.compile_timeout,
                progress_callback=progress_callback
            )

            # Analyze compile result
            if result["exit_code"] == 0:
                return {
                    "success": True,
                    "duration": result.get("execution_time", 0),
                    "output": result.get("stdout", "")[:1000],
                    "mode": "host"
                }
            else:
                # Use result analyzer for detailed error analysis
                analyzer = self.get_result_analyzer()
                analysis = analyzer.analyze_compile_result(result)

                return {
                    "success": False,
                    "error": analysis.get("error_summary", "Compilation failed"),
                    "output": result.get("stdout", ""),
                    "stderr": result.get("stderr", "")[:2000],
                    "suggestions": analysis.get("suggestions", []),
                    "mode": "host"
                }

        except Exception as e:
            self.logger.error(f"Compilation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "mode": "host"
            }

    def _run_tests(self, fix: Dict) -> Dict:
        """Run tests on remote server or inside Docker container."""
        self.logger.info("Running tests")

        try:
            # Determine which tests to run
            operator_name = fix.get("operator_name", "")
            test_files = fix.get("test_files", [])

            if not test_files and operator_name:
                test_files = [f"test/test_v2r1_ops/test_{operator_name}.py"]

            if not test_files:
                test_files = ["test/test_common/"]

            test_command = f"pytest {' '.join(test_files)} -v --tb=short"

            # Execute tests (in Docker or on host)
            if self.use_docker:
                result = self._run_tests_in_docker(test_command)
            else:
                result = self.execute_remote_sync(
                    command=test_command,
                    working_dir=self.remote_work_dir,
                    timeout=self.test_timeout
                )

            # Analyze test results
            analyzer = self.get_result_analyzer()
            analysis = analyzer.analyze_test_result(result)

            if analysis.get("success", result.get("exit_code", -1) == 0):
                return {
                    "success": True,
                    "tests_run": analysis.get("tests_run", 0),
                    "tests_passed": analysis.get("tests_passed", 0),
                    "tests_failed": analysis.get("tests_failed", 0),
                    "output": result.get("stdout", "")[:2000],
                    "mode": "docker" if self.use_docker else "host"
                }
            else:
                return {
                    "success": False,
                    "error": analysis.get("error_summary", "Tests failed"),
                    "tests_run": analysis.get("tests_run", 0),
                    "tests_passed": analysis.get("tests_passed", 0),
                    "tests_failed": analysis.get("tests_failed", 0),
                    "failed_tests": analysis.get("failed_tests", []),
                    "output": result.get("stdout", "")[:2000],
                    "stderr": result.get("stderr", "")[:2000],
                    "mode": "docker" if self.use_docker else "host"
                }

        except Exception as e:
            self.logger.error(f"Test execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "mode": "docker" if self.use_docker else "host"
            }

    def _run_tests_in_docker(self, test_command: str) -> Dict:
        """Run tests inside Docker container."""
        docker = self.get_docker_executor()

        result = docker.execute_sync(
            command=test_command,
            working_dir=self.docker_work_dir,
            timeout=self.test_timeout
        )

        return {
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "execution_time": result.execution_time
            }

    def _run(self):
        """Main agent loop."""
        self.logger.info("Verifier agent started, waiting for tasks")

        while not self._stop_event.is_set():
            self._stop_event.wait(1)

        self.logger.info("Verifier agent stopped")
