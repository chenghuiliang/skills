# Remote command executor with sync/async support
# All comments in this file are in English per project guidelines

import hashlib
import json
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

from remote.core.exceptions import CommandError, TimeoutError
from remote.core.session_manager import RemoteSessionManager
from remote.models.data_models import (
    CommandResult,
    AsyncTaskHandle,
    TaskState,
    TaskStatus,
)


class RemoteCommandExecutor:
    """Executes commands on remote servers.

    Supports both synchronous and asynchronous execution modes,
    with environment setup and timeout handling.

    Example:
        session = RemoteSessionManager("dev@server")
        executor = RemoteCommandExecutor(session)

        # Synchronous execution
        result = executor.execute_sync("ls -la", working_dir="/home/dev")

        # Asynchronous execution
        task = executor.execute_async("bash ci/build.sh", timeout=3600)
        status = executor.get_async_status(task.task_id)
    """

    # Default remote directory for async task tracking
    DEFAULT_TASK_DIR = ".remote_tasks"

    def __init__(
        self,
        session: RemoteSessionManager,
        default_env_setup: Optional[str] = None,
        default_working_dir: Optional[str] = None
    ):
        """Initialize command executor.

        Args:
            session: Connected SSH session manager
            default_env_setup: Default environment setup command (e.g., "source env.sh")
            default_working_dir: Default working directory for commands
        """
        self.session = session
        self.default_env_setup = default_env_setup
        self.default_working_dir = default_working_dir
        self._active_tasks: Dict[str, AsyncTaskHandle] = {}

    def _build_command(
        self,
        command: str,
        working_dir: Optional[str] = None,
        env_setup: Optional[str] = None
    ) -> str:
        """Build full command with environment setup and working directory.

        Args:
            command: Original command
            working_dir: Working directory (uses default if not specified)
            env_setup: Environment setup (uses default if not specified)

        Returns:
            str: Full command with setup
        """
        work_dir = working_dir or self.default_working_dir
        env_cmd = env_setup if env_setup is not None else self.default_env_setup

        parts = []

        # Change to working directory first
        if work_dir:
            parts.append(f"cd {work_dir}")

        # Source environment setup
        if env_cmd:
            parts.append(env_cmd)

        # Add the actual command
        parts.append(command)

        # Join with && to ensure early exit on failure
        return " && ".join(parts)

    def execute_sync(
        self,
        command: str,
        working_dir: Optional[str] = None,
        env_setup: Optional[str] = None,
        timeout: int = 300,
        streaming_callback: Optional[Callable[[str, str], None]] = None
    ) -> CommandResult:
        """Execute command synchronously.

        Args:
            command: Command to execute
            working_dir: Working directory for command
            env_setup: Environment setup command
            timeout: Timeout in seconds
            streaming_callback: Callback for streaming output (channel, data)

        Returns:
            CommandResult: Execution result

        Raises:
            CommandError: If command execution fails
            TimeoutError: If command times out
        """
        full_command = self._build_command(command, working_dir, env_setup)

        start_time = time.time()

        try:
            if streaming_callback:
                exit_code, stdout, stderr = self.session.execute_command_streaming(
                    full_command,
                    timeout=timeout,
                    output_callback=streaming_callback
                )
            else:
                exit_code, stdout, stderr = self.session.execute_command(
                    full_command,
                    timeout=timeout
                )

            execution_time = time.time() - start_time

            result = CommandResult(
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                execution_time=execution_time,
                command=command,
                working_dir=working_dir or self.default_working_dir or ""
            )

            if exit_code != 0:
                raise CommandError(
                    message=f"Command failed with exit code {exit_code}",
                    exit_code=exit_code,
                    stdout=stdout,
                    stderr=stderr,
                    command=command
                )

            return result

        except Exception as e:
            if isinstance(e, CommandError):
                raise

            # Check if it's a timeout
            if "timeout" in str(e).lower():
                raise TimeoutError(
                    message=f"Command timed out after {timeout}s: {command}",
                    command=command
                ) from e

            raise CommandError(
                message=f"Command execution failed: {e}",
                command=command,
                original_error=e
            ) from e

    def execute_async(
        self,
        command: str,
        working_dir: Optional[str] = None,
        env_setup: Optional[str] = None,
        timeout: Optional[int] = None,
        task_id: Optional[str] = None
    ) -> AsyncTaskHandle:
        """Execute command asynchronously using nohup.

        Args:
            command: Command to execute
            working_dir: Working directory for command
            env_setup: Environment setup command
            timeout: Maximum execution time (optional)
            task_id: Custom task ID (auto-generated if not provided)

        Returns:
            AsyncTaskHandle: Handle to track the async task
        """
        task_id = task_id or str(uuid.uuid4())[:8]
        work_dir = working_dir or self.default_working_dir or "~"

        # Create task directory on remote
        task_dir = f"{self.DEFAULT_TASK_DIR}/{task_id}"
        log_file = f"{task_dir}/output.log"
        status_file = f"{task_dir}/status.json"
        pid_file = f"{task_dir}/pid"

        # Build the command
        full_command = self._build_command(command, working_dir, env_setup)

        # Wrap with nohup and capture output
        nohup_command = f"""
        mkdir -p {task_dir} && \
        echo '{{"state": "PENDING", "start_time": null}}' > {status_file} && \
        nohup bash -c '{full_command}' > {log_file} 2>&1 & \
        echo $! > {pid_file} && \
        echo '{{"state": "RUNNING", "start_time": $(date +%s)}}' > {status_file}
        """

        # Execute the setup command synchronously
        setup_result = self.execute_sync(
            nohup_command,
            timeout=30  # Short timeout for setup
        )

        if setup_result.exit_code != 0:
            raise CommandError(
                message=f"Failed to start async task: {setup_result.stderr}",
                command=command
            )

        # Create task handle
        handle = AsyncTaskHandle(
            task_id=task_id,
            command=command,
            working_dir=work_dir,
            state=TaskState.RUNNING,
            log_file=log_file,
            status_file=status_file
        )

        self._active_tasks[task_id] = handle
        return handle

    def get_async_status(self, task_id: str) -> TaskStatus:
        """Get current status of an async task.

        Args:
            task_id: Task identifier

        Returns:
            TaskStatus: Current task status
        """
        status_file = f"{self.DEFAULT_TASK_DIR}/{task_id}/status.json"
        log_file = f"{self.DEFAULT_TASK_DIR}/{task_id}/output.log"
        pid_file = f"{self.DEFAULT_TASK_DIR}/{task_id}/pid"

        try:
            # Read status file
            result = self.execute_sync(f"cat {status_file}", timeout=10)
            status_data = json.loads(result.stdout)

            # Check if process is still running
            pid_result = self.execute_sync(f"cat {pid_file}", timeout=5)
            pid = pid_result.stdout.strip()

            # Check process status
            check_result = self.execute_sync(
                f"ps -p {pid} > /dev/null 2>&1 && echo 'running' || echo 'stopped'",
                timeout=5
            )
            is_running = check_result.stdout.strip() == "running"

            # Get last output
            last_output = ""
            try:
                log_result = self.execute_sync(
                    f"tail -c 4096 {log_file}",
                    timeout=5
                )
                last_output = log_result.stdout
            except CommandError:
                pass

            # Determine state
            state_str = status_data.get("state", "UNKNOWN")
            state = TaskState[state_str] if hasattr(TaskState, state_str) else TaskState.FAILED

            if not is_running and state == TaskState.RUNNING:
                # Process stopped but state not updated
                state = TaskState.COMPLETED

            return TaskStatus(
                task_id=task_id,
                state=state,
                progress=status_data.get("progress"),
                message=status_data.get("message"),
                last_output=last_output
            )

        except Exception as e:
            return TaskStatus(
                task_id=task_id,
                state=TaskState.FAILED,
                message=f"Failed to get status: {e}"
            )

    def wait_for_async(
        self,
        task_id: str,
        timeout: Optional[int] = None,
        poll_interval: int = 5,
        progress_callback: Optional[Callable[[TaskStatus], None]] = None
    ) -> CommandResult:
        """Wait for async task to complete.

        Args:
            task_id: Task identifier
            timeout: Maximum wait time in seconds
            poll_interval: Seconds between status checks
            progress_callback: Callback for progress updates

        Returns:
            CommandResult: Final execution result
        """
        start_time = time.time()

        while True:
            status = self.get_async_status(task_id)

            if progress_callback:
                progress_callback(status)

            if status.state in (TaskState.COMPLETED, TaskState.CANCELLED, TaskState.TIMEOUT):
                break

            if status.state == TaskState.FAILED:
                raise CommandError(
                    message=f"Async task {task_id} failed: {status.message}",
                    command=self._active_tasks.get(task_id, AsyncTaskHandle(task_id, "", "")).command
                )

            if timeout and (time.time() - start_time) > timeout:
                self.cancel_async(task_id)
                raise TimeoutError(
                    message=f"Async task {task_id} timed out after {timeout}s",
                    command=self._active_tasks.get(task_id, AsyncTaskHandle(task_id, "", "")).command
                )

            time.sleep(poll_interval)

        # Get final result
        log_file = f"{self.DEFAULT_TASK_DIR}/{task_id}/output.log"
        log_result = self.execute_sync(f"cat {log_file}", timeout=30)

        # Get exit code from status
        status_result = self.execute_sync(
            f"cat {self.DEFAULT_TASK_DIR}/{task_id}/status.json",
            timeout=5
        )
        status_data = json.loads(status_result.stdout)
        exit_code = status_data.get("exit_code", -1)

        return CommandResult(
            exit_code=exit_code,
            stdout=log_result.stdout,
            stderr="",  # Combined in nohup
            execution_time=time.time() - start_time,
            command=self._active_tasks.get(task_id, AsyncTaskHandle(task_id, "", "")).command,
            working_dir=self._active_tasks.get(task_id, AsyncTaskHandle(task_id, "", "")).working_dir
        )

    def cancel_async(self, task_id: str) -> bool:
        """Cancel an async task.

        Args:
            task_id: Task identifier

        Returns:
            bool: True if cancelled successfully
        """
        pid_file = f"{self.DEFAULT_TASK_DIR}/{task_id}/pid"
        status_file = f"{self.DEFAULT_TASK_DIR}/{task_id}/status.json"

        try:
            # Get PID
            result = self.execute_sync(f"cat {pid_file}", timeout=5)
            pid = result.stdout.strip()

            # Kill the process and its children
            self.execute_sync(f"kill -TERM {pid} 2>/dev/null || true", timeout=5)
            time.sleep(1)
            self.execute_sync(f"kill -KILL {pid} 2>/dev/null || true", timeout=5)

            # Update status
            self.execute_sync(
                f"echo '{{\"state\": \"CANCELLED\", \"cancelled_at\": $(date +%s)}}' > {status_file}",
                timeout=5
            )

            if task_id in self._active_tasks:
                self._active_tasks[task_id].state = TaskState.CANCELLED

            return True

        except CommandError:
            return False

    def stream_async_output(
        self,
        task_id: str,
        follow: bool = True,
        tail_lines: int = 100
    ):
        """Stream async task output.

        Args:
            task_id: Task identifier
            follow: Whether to follow new output (like tail -f)
            tail_lines: Number of lines to start with

        Yields:
            str: Lines of output
        """
        log_file = f"{self.DEFAULT_TASK_DIR}/{task_id}/output.log"

        if follow:
            # Use tail -f equivalent
            command = f"tail -n {tail_lines} -f {log_file}"
            # This would need a streaming implementation
            # For now, just yield current content
            result = self.execute_sync(command, timeout=30)
            for line in result.stdout.splitlines():
                yield line
        else:
            result = self.execute_sync(f"tail -n {tail_lines} {log_file}", timeout=30)
            for line in result.stdout.splitlines():
                yield line

    def cleanup_task(self, task_id: str) -> bool:
        """Clean up task files.

        Args:
            task_id: Task identifier

        Returns:
            bool: True if cleaned successfully
        """
        task_dir = f"{self.DEFAULT_TASK_DIR}/{task_id}"

        try:
            self.execute_sync(f"rm -rf {task_dir}", timeout=10)

            if task_id in self._active_tasks:
                del self._active_tasks[task_id]

            return True
        except CommandError:
            return False

    def list_active_tasks(self) -> List[AsyncTaskHandle]:
        """List all active (non-completed) tasks.

        Returns:
            List[AsyncTaskHandle]: Active task handles
        """
        active = []
        for task_id, handle in self._active_tasks.items():
            status = self.get_async_status(task_id)
            if status.state in (TaskState.PENDING, TaskState.RUNNING):
                active.append(handle)
        return active
