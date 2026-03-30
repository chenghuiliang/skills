# Remote server debugging module for torch-npu-debugger
#
# This module provides remote server operation capabilities including:
# - SSH connection management
# - Remote command execution (sync/async)
# - File upload/download and manipulation
# - Git operations on remote servers
# - Compile/test result analysis
#
# Example usage:
#     from remote.core.session_manager import RemoteSessionManager
#     from remote.core.command_executor import RemoteCommandExecutor
#
#     session = RemoteSessionManager("dev@server", key_path="~/.ssh/id_rsa")
#     executor = RemoteCommandExecutor(session)
#     result = executor.execute_sync("ls -la", working_dir="/home/dev")

__version__ = "0.1.0"

from remote.models.data_models import (
    CommandResult,
    AsyncTaskHandle,
    TaskStatus,
    CompileAnalysis,
    TestAnalysis,
    ErrorInfo,
    FileInfo,
    GitStatus,
    CommitInfo,
    NPUDeviceInfo,
)

__all__ = [
    "CommandResult",
    "AsyncTaskHandle",
    "TaskStatus",
    "CompileAnalysis",
    "TestAnalysis",
    "ErrorInfo",
    "FileInfo",
    "GitStatus",
    "CommitInfo",
    "NPUDeviceInfo",
]
