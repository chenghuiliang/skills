#!/usr/bin/env python3
"""
Remote build subAgent helper.
This script is designed to be called by Claude Code's Agent tool to execute
remote compilation and testing, returning only summarized results to avoid
context explosion in the main agent.
"""

import subprocess
import sys
import json
import re
from pathlib import Path


def run_remote_command(host: str, command: str, timeout: int = 600) -> dict:
    """
    Execute a command on remote server via SSH.
    Returns summarized result instead of full output.
    """
    full_cmd = f"ssh {host} \"{command}\""

    result = {
        "success": False,
        "command": command,
        "exit_code": -1,
        "error_summary": None,
        "key_errors": [],
        "warnings": [],
    }

    try:
        proc = subprocess.run(
            full_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        result["exit_code"] = proc.returncode
        result["success"] = proc.returncode == 0

        # Extract key errors from stderr
        if proc.stderr:
            error_lines = proc.stderr.strip().split('\n')
            # Only keep error lines, not full output
            result["key_errors"] = [
                line for line in error_lines
                if any(kw in line.lower() for kw in ['error:', 'failed', 'fatal', 'undefined'])
            ][:10]  # Limit to 10 most relevant errors

            # Extract warnings
            result["warnings"] = [
                line for line in error_lines
                if 'warning:' in line.lower()
            ][:5]

        # For successful builds, just return success status
        if result["success"]:
            result["error_summary"] = "Build completed successfully"
        else:
            # Summarize failure without full log
            result["error_summary"] = f"Build failed with {len(result['key_errors'])} errors"

    except subprocess.TimeoutExpired:
        result["error_summary"] = f"Command timed out after {timeout}s"
    except Exception as e:
        result["error_summary"] = f"Exception: {str(e)}"

    return result


def build_torch_npu(host: str, docker: str, workdir: str) -> dict:
    """Build torch_npu on remote server."""
    cmd = f"docker exec {docker} bash -c 'cd {workdir} && bash ci/build.sh'"
    return run_remote_command(host, cmd, timeout=1200)  # 20 min timeout for build


def run_test(host: str, docker: str, workdir: str, test_path: str) -> dict:
    """Run a specific test on remote server."""
    cmd = f"docker exec {docker} bash -c 'cd {workdir} && pytest {test_path} -v --tb=short'"
    return run_remote_command(host, cmd, timeout=300)


def main():
    """CLI entry point for subAgent usage."""
    if len(sys.argv) < 2:
        print("Usage: remote_build_agent.py <command> [args...]")
        print("Commands: build, test, sync")
        sys.exit(1)

    command = sys.argv[1]

    # Default configuration (can be overridden via env vars)
    host = "root@192.168.9.116"
    docker = "lch_test"
    workdir = "/home/lch/work/torch_npu2"

    if command == "build":
        result = build_torch_npu(host, docker, workdir)
        # Output minimal JSON for main agent
        print(json.dumps(result, indent=2))

    elif command == "test":
        if len(sys.argv) < 3:
            print("Usage: remote_build_agent.py test <test_path>")
            sys.exit(1)
        test_path = sys.argv[2]
        result = run_test(host, docker, workdir, test_path)
        print(json.dumps(result, indent=2))

    elif command == "sync":
        # Sync code to remote server
        sync_script = Path(__file__).parent / "sync-to-server.sh"
        proc = subprocess.run(
            str(sync_script),
            shell=True,
            capture_output=True,
            text=True
        )
        result = {
            "success": proc.returncode == 0,
            "exit_code": proc.returncode,
            "output": proc.stdout[-500:] if proc.stdout else None,  # Last 500 chars
        }
        print(json.dumps(result, indent=2))

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
