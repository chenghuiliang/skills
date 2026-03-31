# Remote configuration management for multi-agent system
# All comments in this file are in English per project guidelines

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List
from pathlib import Path
import json


@dataclass
class RemoteConfig:
    """Configuration for remote server connections.

    This class holds all parameters needed to connect to and operate
    on remote Ascend NPU servers.

    Attributes:
        host: Remote server hostname or IP
        user: SSH username
        port: SSH port (default: 22)
        key_path: Path to SSH private key
        password: SSH password (not recommended)
        env_setup_script: Environment setup command
        working_dir: Default working directory on remote
        cann_version: Expected CANN version (for validation)
        connection_timeout: SSH connection timeout
        command_timeout: Default command timeout
    """

    host: str = ""
    user: Optional[str] = None
    port: int = 22
    key_path: Optional[str] = None
    password: Optional[str] = None
    env_setup_script: Optional[str] = None
    working_dir: str = "~/torch_npu"
    cann_version: Optional[str] = None
    connection_timeout: int = 30
    command_timeout: int = 300
    compile_timeout: int = 3600  # Longer timeout for compilation
    test_timeout: int = 600      # Timeout for test execution

    # Docker mode configuration
    use_docker: bool = False
    docker_container: Optional[str] = None
    docker_work_dir: str = "/home/lch/work/torch_npu"
    python_version: str = "3.10"

    # Environment script search paths (checked in order)
    env_script_paths: List[str] = field(default_factory=lambda: [
        "~/env_ms.sh",
        "~/work/env_ms.sh",
        "/home/*/work/env_ms.sh",
        "~/ascend_env.sh",
        "~/set_env.sh",
        "~/env.sh",
        "/usr/local/Ascend/ascend-toolkit/set_env.sh",
    ])

    def __post_init__(self):
        """Post-initialization validation and expansion."""
        # Expand ~ in paths
        if self.key_path:
            self.key_path = str(Path(self.key_path).expanduser())

        # Validate required fields
        if not self.host:
            raise ValueError("Remote host is required")

    @classmethod
    def from_env(cls) -> "RemoteConfig":
        """Create configuration from environment variables.

        Environment variables:
            TORCH_NPU_REMOTE_HOST: Remote server host (required)
            TORCH_NPU_REMOTE_USER: SSH username
            TORCH_NPU_REMOTE_PORT: SSH port (default: 22)
            TORCH_NPU_REMOTE_KEY: Path to SSH private key
            TORCH_NPU_REMOTE_PASSWORD: SSH password (not recommended)
            TORCH_NPU_ENV_SCRIPT: Environment setup script
            TORCH_NPU_REMOTE_WORKDIR: Working directory on remote
            TORCH_NPU_CANN_VERSION: Expected CANN version
            TORCH_NPU_CONN_TIMEOUT: Connection timeout
            TORCH_NPU_CMD_TIMEOUT: Command timeout

        Returns:
            RemoteConfig: Configuration from environment

        Raises:
            ValueError: If required variables are missing
        """
        host = os.getenv("TORCH_NPU_REMOTE_HOST")
        if not host:
            raise ValueError(
                "TORCH_NPU_REMOTE_HOST environment variable is required. "
                "Set it to the remote server address (e.g., user@server)."
            )

        return cls(
            host=host,
            user=os.getenv("TORCH_NPU_REMOTE_USER"),
            port=int(os.getenv("TORCH_NPU_REMOTE_PORT", "22")),
            key_path=os.getenv("TORCH_NPU_REMOTE_KEY"),
            password=os.getenv("TORCH_NPU_REMOTE_PASSWORD"),
            env_setup_script=os.getenv("TORCH_NPU_ENV_SCRIPT"),
            working_dir=os.getenv("TORCH_NPU_REMOTE_WORKDIR", "~/torch_npu"),
            cann_version=os.getenv("TORCH_NPU_CANN_VERSION"),
            connection_timeout=int(os.getenv("TORCH_NPU_CONN_TIMEOUT", "30")),
            command_timeout=int(os.getenv("TORCH_NPU_CMD_TIMEOUT", "300")),
            # Docker configuration from environment
            use_docker=os.getenv("TORCH_NPU_USE_DOCKER", "false").lower() == "true",
            docker_container=os.getenv("TORCH_NPU_DOCKER_CONTAINER"),
            docker_work_dir=os.getenv("TORCH_NPU_DOCKER_WORKDIR", "/home/lch/work/torch_npu"),
            python_version=os.getenv("TORCH_NPU_PYTHON_VERSION", "3.10")
        )

    @classmethod
    def from_file(cls, config_path: str) -> "RemoteConfig":
        """Create configuration from JSON file.

        Args:
            config_path: Path to JSON configuration file

        Returns:
            RemoteConfig: Configuration from file

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid
        """
        path = Path(config_path).expanduser()

        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(path, 'r') as f:
            data = json.load(f)

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RemoteConfig":
        """Create configuration from dictionary.

        Args:
            data: Configuration dictionary

        Returns:
            RemoteConfig: Configuration from dict
        """
        # Filter only valid fields
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}

        return cls(**filtered)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.

        Returns:
            Dict with configuration values
        """
        return {
            "host": self.host,
            "user": self.user,
            "port": self.port,
            "key_path": self.key_path,
            "env_setup_script": self.env_setup_script,
            "working_dir": self.working_dir,
            "cann_version": self.cann_version,
            "connection_timeout": self.connection_timeout,
            "command_timeout": self.command_timeout,
            "compile_timeout": self.compile_timeout,
            "test_timeout": self.test_timeout,
            # Docker configuration
            "use_docker": self.use_docker,
            "docker_container": self.docker_container,
            "docker_work_dir": self.docker_work_dir,
            "python_version": self.python_version,
        }

    def to_file(self, config_path: str):
        """Save configuration to JSON file.

        Args:
            config_path: Path to save configuration
        """
        path = Path(config_path).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    def get_connection_string(self) -> str:
        """Get SSH connection string.

        Returns:
            str: Connection string like "user@host:port"
        """
        if self.user:
            return f"{self.user}@{self.host}:{self.port}"
        return f"{self.host}:{self.port}"

    def __str__(self) -> str:
        """String representation (masks password)."""
        return (
            f"RemoteConfig("
            f"host={self.host}, "
            f"user={self.user}, "
            f"port={self.port}, "
            f"working_dir={self.working_dir}, "
            f"cann_version={self.cann_version}"
            f")"
        )


class RemoteConfigLoader:
    """Loads and manages remote configuration with fallback.

    Configuration is loaded in this priority order:
    1. Explicitly provided configuration
    2. Environment variables
    3. Configuration file (default: ~/.config/torch-npu-debugger/remote.json)
    4. Default values (may be incomplete)
    """

    DEFAULT_CONFIG_PATH = "~/.config/torch-npu-debugger/remote.json"

    @classmethod
    def load(
        cls,
        config: Optional[RemoteConfig] = None,
        config_path: Optional[str] = None
    ) -> RemoteConfig:
        """Load configuration with fallback chain.

        Args:
            config: Explicit configuration (highest priority)
            config_path: Path to config file

        Returns:
            RemoteConfig: Loaded configuration

        Raises:
            ValueError: If no valid configuration can be loaded
        """
        # Priority 1: Explicit config
        if config is not None:
            return config

        # Priority 2: Environment variables
        try:
            return RemoteConfig.from_env()
        except ValueError:
            pass  # Continue to next fallback

        # Priority 3: Config file
        path = config_path or cls.DEFAULT_CONFIG_PATH
        try:
            return RemoteConfig.from_file(path)
        except (FileNotFoundError, ValueError):
            pass  # Continue to next fallback

        # Priority 4: Default (will likely fail validation)
        raise ValueError(
            "No valid remote configuration found. "
            "Set TORCH_NPU_REMOTE_HOST environment variable, "
            "create a config file at ~/.config/torch-npu-debugger/remote.json, "
            "or pass config explicitly."
        )

    @classmethod
    def create_default_config(cls, host: str, output_path: Optional[str] = None) -> str:
        """Create a default configuration file.

        Args:
            host: Remote server host
            output_path: Path to save config (default: ~/.config/torch-npu-debugger/remote.json)

        Returns:
            str: Path to created config file
        """
        path = output_path or cls.DEFAULT_CONFIG_PATH
        expanded_path = Path(path).expanduser()

        # Create directory
        expanded_path.parent.mkdir(parents=True, exist_ok=True)

        # Create default config
        config = RemoteConfig(
            host=host,
            key_path="~/.ssh/id_rsa",
            env_setup_script="source ~/work/env_ms.sh",
            working_dir="~/torch_npu"
        )

        config.to_file(str(expanded_path))
        return str(expanded_path)


def get_remote_config(
    host: Optional[str] = None,
    user: Optional[str] = None,
    key_path: Optional[str] = None,
    env_script: Optional[str] = None,
    working_dir: Optional[str] = None
) -> RemoteConfig:
    """Convenience function to get remote configuration.

    Args:
        host: Remote server host (overrides env/config)
        user: SSH username (overrides env/config)
        key_path: SSH key path (overrides env/config)
        env_script: Environment setup script (overrides env/config)
        working_dir: Remote working directory (overrides env/config)

    Returns:
        RemoteConfig: Configuration with overrides applied

    Raises:
        ValueError: If configuration cannot be loaded
    """
    # Try to load base config
    try:
        config = RemoteConfigLoader.load()
    except ValueError:
        # Create minimal config if we have host
        if not host:
            raise ValueError(
                "Remote host is required. Set TORCH_NPU_REMOTE_HOST "
                "or pass host parameter."
            )
        config = RemoteConfig(host=host)

    # Apply overrides
    if host:
        config.host = host
    if user:
        config.user = user
    if key_path:
        config.key_path = key_path
    if env_script:
        config.env_setup_script = env_script
    if working_dir:
        config.working_dir = working_dir

    return config
