# Exception classes for remote operations
# All comments in this file are in English per project guidelines


class RemoteError(Exception):
    """Base exception for remote operations."""

    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message)
        self.original_error = original_error


class ConnectionError(RemoteError):
    """Raised when SSH connection fails."""
    pass


class AuthenticationError(ConnectionError):
    """Raised when SSH authentication fails."""
    pass


class CommandError(RemoteError):
    """Raised when remote command execution fails."""

    def __init__(
        self,
        message: str,
        exit_code: int = None,
        stdout: str = "",
        stderr: str = "",
        command: str = "",
        original_error: Exception = None
    ):
        super().__init__(message, original_error)
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.command = command


class TimeoutError(CommandError):
    """Raised when command execution times out."""
    pass


class FileError(RemoteError):
    """Raised when file operation fails."""
    pass


class FileNotFoundError(FileError):
    """Raised when remote file is not found."""
    pass


class PermissionError(FileError):
    """Raised when file access is denied."""
    pass


class GitError(RemoteError):
    """Raised when git operation fails."""
    pass


class EnvironmentError(RemoteError):
    """Raised when environment setup fails."""
    pass


class EnvironmentNotFoundError(EnvironmentError):
    """Raised when required environment script is not found."""
    pass


class VersionMismatchError(EnvironmentError):
    """Raised when version compatibility check fails."""
    pass


class TaskError(RemoteError):
    """Raised when async task operation fails."""
    pass


class TaskNotFoundError(TaskError):
    """Raised when async task is not found."""
    pass


class AnalysisError(RemoteError):
    """Raised when result analysis fails."""
    pass
