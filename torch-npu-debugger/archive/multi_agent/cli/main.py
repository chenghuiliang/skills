#!/usr/bin/env python3
"""
Multi-Agent CLI for torch_npu debugging.

This CLI manages a cluster of specialized agents for end-to-end
issue diagnosis and fixing.
"""

import sys
import argparse
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from .commands import AgentCommands, WorkflowCommands, SystemCommands


def create_parser():
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        prog="torch-npu-agents",
        description="Multi-agent system for torch_npu debugging"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Agent commands
    agent_parser = subparsers.add_parser("agent", help="Manage agents")
    agent_subparsers = agent_parser.add_subparsers(dest="agent_command")

    # agent start
    start_parser = agent_subparsers.add_parser("start", help="Start agents")
    start_parser.add_argument(
        "agent_id",
        nargs="?",
        help="Agent to start (or omit for all)"
    )

    # agent stop
    stop_parser = agent_subparsers.add_parser("stop", help="Stop agents")
    stop_parser.add_argument(
        "agent_id",
        nargs="?",
        help="Agent to stop (or omit for all)"
    )

    # agent status
    agent_subparsers.add_parser("status", help="Show agent status")

    # agent restart
    restart_parser = agent_subparsers.add_parser("restart", help="Restart an agent")
    restart_parser.add_argument("agent_id", help="Agent to restart")

    # Workflow commands
    workflow_parser = subparsers.add_parser("workflow", help="Manage workflows")
    workflow_subparsers = workflow_parser.add_subparsers(dest="workflow_command")

    # workflow start
    wf_start = workflow_subparsers.add_parser("start", help="Start debugging workflow")
    wf_start.add_argument("--title", "-t", required=True, help="Issue title")
    wf_start.add_argument("--description", "-d", help="Issue description")
    wf_start.add_argument("--error-log", "-e", help="Error log content")
    wf_start.add_argument("--file", "-f", help="File containing issue description")

    # workflow status
    wf_status = workflow_subparsers.add_parser("status", help="Check workflow status")
    wf_status.add_argument("workflow_id", help="Workflow ID")

    # workflow list
    workflow_subparsers.add_parser("list", help="List active workflows")

    # System commands
    sys_parser = subparsers.add_parser("system", help="System operations")
    sys_subparsers = sys_parser.add_subparsers(dest="system_command")

    sys_subparsers.add_parser("health", help="Check system health")
    sys_subparsers.add_parser("cleanup", help="Clean up artifacts")

    return parser


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        if args.command == "agent":
            return handle_agent_command(args)
        elif args.command == "workflow":
            return handle_workflow_command(args)
        elif args.command == "system":
            return handle_system_command(args)
        else:
            parser.print_help()
            return 1

    except KeyboardInterrupt:
        print("\nInterrupted")
        return 130
    except Exception as e:
        print(f"Error: {e}")
        return 1


def handle_agent_command(args) -> int:
    """Handle agent commands."""
    commands = AgentCommands()

    if not args.agent_command:
        print("Available agent commands: start, stop, status, restart")
        return 1

    if args.agent_command == "start":
        success = commands.start(args.agent_id)
        return 0 if success else 1

    elif args.agent_command == "stop":
        success = commands.stop(args.agent_id)
        return 0 if success else 1

    elif args.agent_command == "status":
        commands.status()
        return 0

    elif args.agent_command == "restart":
        if not args.agent_id:
            print("Agent ID required")
            return 1
        success = commands.restart(args.agent_id)
        return 0 if success else 1

    return 0


def handle_workflow_command(args) -> int:
    """Handle workflow commands."""
    commands = WorkflowCommands()

    if not args.workflow_command:
        print("Available workflow commands: start, status, list")
        return 1

    if args.workflow_command == "start":
        success = commands.start(
            title=args.title,
            description=args.description,
            error_log=args.error_log,
            from_file=args.file
        )
        return 0 if success else 1

    elif args.workflow_command == "status":
        commands.status(args.workflow_id)
        return 0

    elif args.workflow_command == "list":
        commands.list_active()
        return 0

    return 0


def handle_system_command(args) -> int:
    """Handle system commands."""
    commands = SystemCommands()

    if not args.system_command:
        print("Available system commands: health, cleanup")
        return 1

    if args.system_command == "health":
        commands.health()
        return 0

    elif args.system_command == "cleanup":
        commands.cleanup()
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
