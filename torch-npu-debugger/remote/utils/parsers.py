# Parser utility functions
# All comments in this file are in English per project guidelines

from typing import Optional


def parse_size(size_str: str) -> int:
    """Parse size string to bytes.

    Supports formats:
        - "1024" (bytes)
        - "1K" / "1k" (kilobytes)
        - "1M" / "1m" (megabytes)
        - "1G" / "1g" (gigabytes)
        - "1T" / "1t" (terabytes)

    Args:
        size_str: Size string

    Returns:
        int: Size in bytes

    Example:
        >>> parse_size("1M")
        1048576
        >>> parse_size("1024")
        1024
    """
    size_str = size_str.strip().upper()

    multipliers = {
        'K': 1024,
        'M': 1024 ** 2,
        'G': 1024 ** 3,
        'T': 1024 ** 4,
    }

    # Try to parse with suffix
    for suffix, multiplier in multipliers.items():
        if size_str.endswith(suffix):
            number = size_str[:-1].strip()
            return int(float(number) * multiplier)

    # Plain number
    return int(size_str)


def format_size(size_bytes: int, precision: int = 1) -> str:
    """Format bytes to human readable string.

    Args:
        size_bytes: Size in bytes
        precision: Decimal precision

    Returns:
        str: Formatted size string

    Example:
        >>> format_size(1048576)
        '1.0 MB'
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"

    units = ['KB', 'MB', 'GB', 'TB', 'PB']
    size = size_bytes / 1024.0

    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.{precision}f} {unit}"
        size /= 1024.0

    return f"{size:.{precision}f} PB"


def format_duration(seconds: float, precision: int = 1) -> str:
    """Format duration in seconds to human readable string.

    Args:
        seconds: Duration in seconds
        precision: Decimal precision for sub-minute durations

    Returns:
        str: Formatted duration string

    Example:
        >>> format_duration(65)
        '1m 5s'
        >>> format_duration(3661)
        '1h 1m 1s'
    """
    if seconds < 60:
        return f"{seconds:.{precision}f}s"

    minutes = int(seconds // 60)
    seconds_remainder = seconds % 60

    if minutes < 60:
        if seconds_remainder > 0:
            return f"{minutes}m {seconds_remainder:.0f}s"
        return f"{minutes}m"

    hours = minutes // 60
    minutes_remainder = minutes % 60

    parts = [f"{hours}h"]
    if minutes_remainder > 0:
        parts.append(f"{minutes_remainder}m")
    if seconds_remainder > 0:
        parts.append(f"{seconds_remainder:.0f}s")

    return " ".join(parts)


def parse_time_to_seconds(time_str: str) -> int:
    """Parse time string to seconds.

    Supports formats:
        - "30" (seconds)
        - "30s" (seconds)
        - "5m" (minutes)
        - "2h" (hours)
        - "1d" (days)

    Args:
        time_str: Time string

    Returns:
        int: Time in seconds

    Example:
        >>> parse_time_to_seconds("5m")
        300
        >>> parse_time_to_seconds("2h")
        7200
    """
    time_str = time_str.strip().lower()

    multipliers = {
        's': 1,
        'm': 60,
        'h': 3600,
        'd': 86400,
    }

    for suffix, multiplier in multipliers.items():
        if time_str.endswith(suffix):
            number = time_str[:-1].strip()
            return int(float(number) * multiplier)

    # Plain number (assume seconds)
    return int(time_str)
