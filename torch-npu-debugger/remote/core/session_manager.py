# SSH session manager for remote connections
# All comments in this file are in English per project guidelines

import os
import socket
import time
from pathlib import Path
from typing import Optional, Tuple

from remote.core.exceptions import ConnectionError, AuthenticationError

# Try to import paramiko, provide fallback if not available
try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False


class RemoteSessionManager:
    """Manages SSH connections to remote servers.

    This class handles SSH connection establishment, authentication,
    and provides a reusable connection pool for remote operations.

    Example:
        session = RemoteSessionManager("dev@server", key_path="~/.ssh/id_rsa")
        session.connect()
        # Use the session...
        session.disconnect()
    """

    def __init__(
        self,
        host: str,
        user: Optional[str] = None,
        port: int = 22,
        key_path: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 30,
        keep_alive_interval: int = 30
    ):
        """Initialize the session manager.

        Args:
            host: Remote host address (can include user like "user@host")
            user: SSH username (extracted from host if not provided)
            port: SSH port (default: 22)
            key_path: Path to SSH private key
            password: SSH password (not recommended, use key instead)
            timeout: Connection timeout in seconds
            keep_alive_interval: SSH keepalive interval in seconds
        """
        # Parse user@host format
        if "@" in host and user is None:
            user, host = host.split("@", 1)

        self.host = host
        self.user = user or os.getenv("USER", "root")
        self.port = port
        self.key_path = key_path
        self.password = password
        self.timeout = timeout
        self.keep_alive_interval = keep_alive_interval

        self._client: Optional["paramiko.SSHClient"] = None
        self._sftp: Optional["paramiko.SFTPClient"] = None
        self._connected = False
        self._last_activity = 0.0

    def connect(self) -> "paramiko.SSHClient":
        """Establish SSH connection to remote server.

        Returns:
            paramiko.SSHClient: Connected SSH client

        Raises:
            ConnectionError: If connection fails
            AuthenticationError: If authentication fails
            ImportError: If paramiko is not installed
        """
        if not PARAMIKO_AVAILABLE:
            raise ImportError(
                "paramiko is required for SSH connections. "
                "Install with: pip install paramiko"
            )

        if self._connected and self._client:
            # Check if connection is still alive
            if self._is_connection_alive():
                return self._client
            else:
                self.disconnect()

        try:
            self._client = paramiko.SSHClient()
            self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Load private key if provided
            pkey = None
            if self.key_path:
                key_path = Path(self.key_path).expanduser()
                if key_path.exists():
                    pkey = paramiko.RSAKey.from_private_key_file(str(key_path))

            # Connect to server
            self._client.connect(
                hostname=self.host,
                port=self.port,
                username=self.user,
                password=self.password,
                pkey=pkey,
                timeout=self.timeout,
                look_for_keys=True
            )

            # Setup keepalive
            transport = self._client.get_transport()
            if transport:
                transport.set_keepalive(self.keep_alive_interval)

            self._connected = True
            self._last_activity = time.time()

            return self._client

        except paramiko.AuthenticationException as e:
            raise AuthenticationError(
                f"Authentication failed for {self.user}@{self.host}: {e}"
            ) from e
        except paramiko.SSHException as e:
            raise ConnectionError(
                f"SSH connection failed to {self.host}: {e}"
            ) from e
        except socket.error as e:
            raise ConnectionError(
                f"Network error connecting to {self.host}: {e}"
            ) from e

    def disconnect(self) -> None:
        """Close SSH connection."""
        if self._sftp:
            try:
                self._sftp.close()
            except Exception:
                pass
            self._sftp = None

        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None

        self._connected = False

    def is_connected(self) -> bool:
        """Check if connection is active.

        Returns:
            bool: True if connected and alive
        """
        if not self._connected or not self._client:
            return False
        return self._is_connection_alive()

    def _is_connection_alive(self) -> bool:
        """Check if the underlying connection is alive."""
        if not self._client:
            return False

        transport = self._client.get_transport()
        if not transport:
            return False

        return transport.is_active()

    def get_client(self) -> "paramiko.SSHClient":
        """Get SSH client, connecting if necessary.

        Returns:
            paramiko.SSHClient: Connected SSH client
        """
        if not self.is_connected():
            return self.connect()
        return self._client

    def get_sftp(self) -> "paramiko.SFTPClient":
        """Get SFTP client, creating if necessary.

        Returns:
            paramiko.SFTPClient: SFTP client
        """
        if not self._sftp or not self._sftp.get_channel().get_transport().is_active():
            client = self.get_client()
            self._sftp = client.open_sftp()
        return self._sftp

    def execute_command(
        self,
        command: str,
        timeout: Optional[int] = None,
        get_pty: bool = False,
        environment: Optional[dict] = None
    ) -> Tuple[int, str, str]:
        """Execute a command on remote server.

        Args:
            command: Command to execute
            timeout: Command timeout in seconds
            get_pty: Whether to allocate pseudo-terminal
            environment: Environment variables to set

        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        client = self.get_client()

        stdin, stdout, stderr = client.exec_command(
            command,
            timeout=timeout,
            get_pty=get_pty,
            environment=environment
        )

        exit_code = stdout.channel.recv_exit_status()
        stdout_str = stdout.read().decode("utf-8", errors="replace")
        stderr_str = stderr.read().decode("utf-8", errors="replace")

        self._last_activity = time.time()

        return exit_code, stdout_str, stderr_str

    def execute_command_streaming(
        self,
        command: str,
        timeout: Optional[int] = None,
        get_pty: bool = False,
        output_callback: Optional[callable] = None
    ) -> Tuple[int, str, str]:
        """Execute a command with streaming output.

        Args:
            command: Command to execute
            timeout: Command timeout in seconds
            get_pty: Whether to allocate pseudo-terminal
            output_callback: Callback function for each line of output

        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        client = self.get_client()

        transport = client.get_transport()
        channel = transport.open_session()

        if get_pty:
            channel.get_pty()

        channel.exec_command(command)

        stdout_lines = []
        stderr_lines = []

        while not channel.exit_status_ready():
            if channel.recv_ready():
                line = channel.recv(1024).decode("utf-8", errors="replace")
                stdout_lines.append(line)
                if output_callback:
                    output_callback("stdout", line)

            if channel.recv_stderr_ready():
                line = channel.recv_stderr(1024).decode("utf-8", errors="replace")
                stderr_lines.append(line)
                if output_callback:
                    output_callback("stderr", line)

            time.sleep(0.01)

        # Get remaining output
        while channel.recv_ready():
            line = channel.recv(1024).decode("utf-8", errors="replace")
            stdout_lines.append(line)
            if output_callback:
                output_callback("stdout", line)

        while channel.recv_stderr_ready():
            line = channel.recv_stderr(1024).decode("utf-8", errors="replace")
            stderr_lines.append(line)
            if output_callback:
                output_callback("stderr", line)

        exit_code = channel.recv_exit_status()
        channel.close()

        self._last_activity = time.time()

        return exit_code, "".join(stdout_lines), "".join(stderr_lines)

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
        return False

    def __repr__(self) -> str:
        """String representation."""
        return f"RemoteSessionManager({self.user}@{self.host}:{self.port})"
