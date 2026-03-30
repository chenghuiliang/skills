# SSH utility functions
# All comments in this file are in English per project guidelines

import os
from pathlib import Path
from typing import Optional, Tuple


def parse_ssh_target(target: str) -> Tuple[str, Optional[str], int]:
    """Parse SSH target string.

    Supports formats:
        - user@host
        - user@host:port
        - host (uses current user)

    Args:
        target: SSH target string

    Returns:
        Tuple of (host, user, port)

    Example:
        >>> parse_ssh_target("dev@server")
        ('server', 'dev', 22)
        >>> parse_ssh_target("dev@server:2222")
        ('server', 'dev', 2222)
    """
    user = None
    port = 22

    # Check for port
    if ":" in target:
        host_part, port_part = target.rsplit(":", 1)
        if port_part.isdigit():
            port = int(port_part)
            target = host_part

    # Check for user
    if "@" in target:
        user, host = target.split("@", 1)
    else:
        host = target
        user = None

    return host, user, port


def validate_ssh_key(key_path: str) -> Tuple[bool, Optional[str]]:
    """Validate SSH key file.

    Args:
        key_path: Path to SSH key file

    Returns:
        Tuple of (is_valid, error_message)
    """
    path = Path(key_path).expanduser()

    if not path.exists():
        return False, f"Key file not found: {key_path}"

    if not path.is_file():
        return False, f"Path is not a file: {key_path}"

    # Check permissions (should be 600 or 644)
    stat = path.stat()
    mode = stat.st_mode & 0o777

    if mode & 0o044:  # Group or others can read
        return False, f"Key file has too open permissions: {oct(mode)}"

    return True, None


def find_ssh_key() -> Optional[str]:
    """Find default SSH key.

    Returns:
        str: Path to SSH key or None
    """
    home = Path.home()

    # Common key locations
    key_paths = [
        home / ".ssh" / "id_rsa",
        home / ".ssh" / "id_ed25519",
        home / ".ssh" / "id_ecdsa",
    ]

    for path in key_paths:
        if path.exists():
            return str(path)

    return None


def expand_ssh_path(path: str) -> str:
    """Expand SSH path (handle ~ and environment variables).

    Args:
        path: Path string

    Returns:
        str: Expanded path
    """
    if path.startswith("~/"):
        return os.path.expanduser(path)
    return os.path.expandvars(path)
