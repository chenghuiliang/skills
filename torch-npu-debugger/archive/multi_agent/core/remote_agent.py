# Remote-capable agent base class
# All comments in this file are in English per project guidelines

import os
import sys
from abc import abstractmethod
from typing import Any, Dict, Optional
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .agent_base import Agent, AgentCapability, AgentState
from ..messaging import Message, MessageType

# Import remote module components
try:
    from remote.core.session_manager import RemoteSessionManager
    from remote.core.command_executor import RemoteCommandExecutor
    from remote.core.file_manager import RemoteFileManager
    from remote.core.docker_executor import DockerExecutor
    from remote.environment.detector import EnvironmentDetector
    from remote.analysis.result_analyzer import ResultAnalyzer
    REMOTE_AVAILABLE = True
except ImportError:
    REMOTE_AVAILABLE = False


@dataclass
class RemoteEnvironmentInfo:
    """Information about remote environment."""
    host: str
    cann_version: Optional[str]
    python_version: Optional[str]
    torch_version: Optional[str]
    torch_npu_version: Optional[str]
    npu_devices: list
    env_setup_script: Optional[str]
    working_dir: str
    connected: bool = False


class RemoteCapableAgent(Agent):
    """Base class for agents that need remote server access.

    This class wraps remote module functionality and provides:
    - SSH connection management
    - Remote command execution (sync/async)
    - File transfer and patch application
    - Environment detection
    - Result analysis

    Agents that need to interact with Ascend NPU servers should inherit
    from this class instead of Agent.

    Example:
        class VerifierAgent(RemoteCapableAgent):
            def __init__(self, ...):
                super().__init__(
                    agent_id="verifier",
                    capabilities=[AgentCapability.VERIFY],
                    remote_host="user@server",
                    remote_key_path="~/.ssh/id_rsa",
                    env_setup_script="source ~/work/env_ms.sh",
                    remote_work_dir="~/torch_npu"
                )
    """

    def __init__(
        self,
        agent_id: str,
        capabilities: list,
        message_bus=None,
        heartbeat_interval: float = 5.0,
        # Remote connection parameters
        remote_host: Optional[str] = None,
        remote_user: Optional[str] = None,
        remote_port: int = 22,
        remote_key_path: Optional[str] = None,
        remote_password: Optional[str] = None,
        env_setup_script: Optional[str] = None,
        remote_work_dir: str = "~/torch_npu",
        # Docker mode parameters
        use_docker: bool = False,
        docker_container: Optional[str] = None,
        docker_work_dir: Optional[str] = None,
        # Timeouts
        connection_timeout: int = 30,
        command_timeout: int = 300
    ):
        """Initialize remote-capable agent.

        Args:
            agent_id: Unique identifier for this agent
            capabilities: List of capabilities this agent has
            message_bus: Message bus for communication
            heartbeat_interval: Seconds between heartbeats
            remote_host: Remote server host (e.g., "user@server" or "server")
            remote_user: SSH username (extracted from host if not provided)
            remote_port: SSH port (default: 22)
            remote_key_path: Path to SSH private key
            remote_password: SSH password (not recommended, use key instead)
            env_setup_script: Environment setup command (e.g., "source ~/env.sh")
            remote_work_dir: Default working directory on remote server
            use_docker: Whether to use Docker container for commands
            docker_container: Docker container name
            docker_work_dir: Working directory inside Docker container
            connection_timeout: SSH connection timeout in seconds
            command_timeout: Default command timeout in seconds
        """
        super().__init__(
            agent_id=agent_id,
            capabilities=capabilities,
            message_bus=message_bus,
            heartbeat_interval=heartbeat_interval
        )

        if not REMOTE_AVAILABLE:
            raise ImportError(
                "Remote module is required for RemoteCapableAgent. "
                "Ensure remote/ module is in PYTHONPATH."
            )

        # Remote configuration
        self.remote_host = remote_host
        self.remote_user = remote_user
        self.remote_port = remote_port
        self.remote_key_path = remote_key_path
        self.remote_password = remote_password
        self.env_setup_script = env_setup_script
        self.remote_work_dir = remote_work_dir
        self.connection_timeout = connection_timeout
        self.command_timeout = command_timeout

        # Docker configuration
        self.use_docker = use_docker
        self.docker_container = docker_container
        self.docker_work_dir = docker_work_dir or "/home/lch/work/torch_npu"

        # Remote session and utilities (lazy initialization)
        self._remote_session: Optional[RemoteSessionManager] = None
        self._command_executor: Optional[RemoteCommandExecutor] = None
        self._file_manager: Optional[RemoteFileManager] = None
        self._docker_executor: Optional[DockerExecutor] = None
        self._env_detector: Optional[EnvironmentDetector] = None
        self._result_analyzer: Optional[ResultAnalyzer] = None

        # Environment info cache
        self._env_info: Optional[RemoteEnvironmentInfo] = None

    def ensure_remote_session(self) -> RemoteSessionManager:
        """Ensure remote session is connected.

        Returns:
            RemoteSessionManager: Connected session

        Raises:
            ConnectionError: If connection fails
            ValueError: If remote_host is not configured
        """
        if not self.remote_host:
            raise ValueError(
                "Remote host not configured. "
                "Set remote_host parameter when creating agent."
            )

        if self._remote_session is not None and self._remote_session.is_connected():
            return self._remote_session

        self.logger.info(f"Connecting to remote server: {self.remote_host}")

        self._remote_session = RemoteSessionManager(
            host=self.remote_host,
            user=self.remote_user,
            port=self.remote_port,
            key_path=self.remote_key_path,
            password=self.remote_password,
            timeout=self.connection_timeout
        )

        self._remote_session.connect()
        self.logger.info("Remote connection established")

        return self._remote_session

    def get_command_executor(self) -> RemoteCommandExecutor:
        """Get remote command executor.

        Returns:
            RemoteCommandExecutor: Configured executor
        """
        if self._command_executor is None:
            session = self.ensure_remote_session()
            self._command_executor = RemoteCommandExecutor(
                session=session,
                default_env_setup=self.env_setup_script,
                default_working_dir=self.remote_work_dir
            )
        return self._command_executor

    def get_file_manager(self) -> RemoteFileManager:
        """Get remote file manager.

        Returns:
            RemoteFileManager: Configured file manager
        """
        if self._file_manager is None:
            session = self.ensure_remote_session()
            self._file_manager = RemoteFileManager(session)
        return self._file_manager

    def get_docker_executor(self) -> DockerExecutor:
        """Get Docker executor for container operations.

        Returns:
            DockerExecutor: Configured executor

        Raises:
            ValueError: If docker_container is not configured
        """
        if not self.docker_container:
            raise ValueError(
                "Docker container name not configured. "
                "Set docker_container parameter when creating agent."
            )

        if self._docker_executor is None:
            session = self.ensure_remote_session()
            self._docker_executor = DockerExecutor(
                session=session,
                container_name=self.docker_container,
                default_working_dir=self.docker_work_dir,
                default_env_setup=self.env_setup_script
            )
        return self._docker_executor

    def get_environment_detector(self) -> EnvironmentDetector:
        """Get environment detector.

        Returns:
            EnvironmentDetector: Configured detector
        """
        if self._env_detector is None:
            session = self.ensure_remote_session()
            self._env_detector = EnvironmentDetector(session)
        return self._env_detector

    def get_result_analyzer(self) -> ResultAnalyzer:
        """Get result analyzer.

        Returns:
            ResultAnalyzer: Configured analyzer
        """
        if self._result_analyzer is None:
            self._result_analyzer = ResultAnalyzer()
        return self._result_analyzer

    def verify_remote_environment(self) -> RemoteEnvironmentInfo:
        """Verify and cache remote environment information.

        Returns:
            RemoteEnvironmentInfo: Environment details

        Raises:
            ConnectionError: If cannot connect to remote
            EnvironmentError: If environment detection fails
        """
        if self._env_info is not None:
            return self._env_info

        self.logger.info("Detecting remote environment...")

        try:
            detector = self.get_environment_detector()

            # Detect environment
            cann_version = detector.detect_cann_version()
            python_version = detector.detect_python_version()
            torch_version = detector.detect_pytorch_version()
            torch_npu_version = detector.detect_torch_npu_version()
            npu_devices = detector.detect_npu_devices()
            env_script = detector.find_env_setup_script()

            self._env_info = RemoteEnvironmentInfo(
                host=self.remote_host,
                cann_version=cann_version,
                python_version=python_version,
                torch_version=torch_version,
                torch_npu_version=torch_npu_version,
                npu_devices=npu_devices,
                env_setup_script=env_script or self.env_setup_script,
                working_dir=self.remote_work_dir,
                connected=True
            )

            self.logger.info(
                f"Environment detected: CANN={cann_version}, "
                f"Python={python_version}, NPU devices={len(npu_devices)}"
            )

            # Send environment info message
            self.send_message(
                recipient="coordinator",
                message_type=MessageType.TASK_PROGRESS,
                payload={
                    "agent_id": self.agent_id,
                    "progress_type": "env_info",
                    "env_info": {
                        "host": self.remote_host,
                        "cann_version": cann_version,
                        "python_version": python_version,
                        "torch_version": torch_version,
                        "npu_devices": len(npu_devices)
                    }
                }
            )

            return self._env_info

        except Exception as e:
            self.logger.error(f"Environment detection failed: {e}")
            raise

    def execute_remote_sync(
        self,
        command: str,
        working_dir: Optional[str] = None,
        timeout: Optional[int] = None,
        use_docker: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Execute command on remote server (synchronous).

        Args:
            command: Command to execute
            working_dir: Working directory on remote (uses default if None)
            timeout: Timeout in seconds (uses default if None)
            use_docker: Whether to execute inside Docker container
                       (defaults to self.use_docker if not specified)

        Returns:
            Dict with exit_code, stdout, stderr, execution_time
        """
        should_use_docker = use_docker if use_docker is not None else self.use_docker

        if should_use_docker:
            executor = self.get_docker_executor()
            result = executor.execute_sync(
                command=command,
                working_dir=working_dir or self.docker_work_dir,
                timeout=timeout or self.command_timeout
            )
        else:
            executor = self.get_command_executor()
            result = executor.execute_sync(
                command=command,
                working_dir=working_dir,
                timeout=timeout or self.command_timeout
            )

        return {
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "execution_time": result.execution_time,
            "command": result.command
        }

    def execute_remote_async(
        self,
        command: str,
        working_dir: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> str:
        """Execute command on remote server (asynchronous).

        Args:
            command: Command to execute
            working_dir: Working directory on remote
            timeout: Maximum execution time

        Returns:
            str: Task ID for tracking
        """
        executor = self.get_command_executor()

        handle = executor.execute_async(
            command=command,
            working_dir=working_dir,
            timeout=timeout
        )

        return handle.task_id

    def get_async_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of async remote task.

        Args:
            task_id: Task identifier

        Returns:
            Dict with state, progress, message, output
        """
        executor = self.get_command_executor()
        status = executor.get_async_status(task_id)

        return {
            "task_id": task_id,
            "state": status.state.value,
            "progress": status.progress,
            "message": status.message,
            "last_output": status.last_output
        }

    def wait_for_async_task(
        self,
        task_id: str,
        timeout: Optional[int] = None,
        progress_callback=None
    ) -> Dict[str, Any]:
        """Wait for async task to complete.

        Args:
            task_id: Task identifier
            timeout: Maximum wait time
            progress_callback: Optional callback for progress updates

        Returns:
            Dict with exit_code, stdout, stderr, execution_time
        """
        executor = self.get_command_executor()

        result = executor.wait_for_async(
            task_id=task_id,
            timeout=timeout,
            progress_callback=progress_callback
        )

        return {
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "execution_time": result.execution_time,
            "command": result.command
        }

    def apply_patch_remote(self, patch_content: str, working_dir: Optional[str] = None) -> bool:
        """Apply git patch on remote server.

        Args:
            patch_content: Git patch content
            working_dir: Working directory on remote

        Returns:
            bool: True if applied successfully
        """
        file_mgr = self.get_file_manager()
        target_dir = working_dir or self.remote_work_dir

        return file_mgr.apply_patch(patch_content, target_dir)

    def upload_file(self, local_path: str, remote_path: str) -> None:
        """Upload file to remote server.

        Args:
            local_path: Local file path
            remote_path: Remote destination path
        """
        file_mgr = self.get_file_manager()
        file_mgr.upload(local_path, remote_path)

    def download_file(self, remote_path: str, local_path: str) -> None:
        """Download file from remote server.

        Args:
            remote_path: Remote file path
            local_path: Local destination path
        """
        file_mgr = self.get_file_manager()
        file_mgr.download(remote_path, local_path)

    def disconnect_remote(self):
        """Disconnect from remote server."""
        if self._remote_session is not None:
            self._remote_session.disconnect()
            self._remote_session = None
            self._command_executor = None
            self._file_manager = None
            self._env_detector = None
            self.logger.info("Remote session disconnected")

    def stop(self):
        """Stop the agent and disconnect remote."""
        self.disconnect_remote()
        super().stop()

    @abstractmethod
    def _handle_specialized(self, message: Message):
        """Handle agent-specific messages. Override in subclasses."""
        pass
