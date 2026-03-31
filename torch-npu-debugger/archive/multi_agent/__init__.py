# Multi-Agent System for torch_npu Debugging
# Based on workflow/roles design
# All comments in this file are in English per project guidelines

"""
Real multi-agent architecture for torch_npu issue diagnosis and fixing.
Based on workflow/roles: Coordinator, Planner, Executor, Evaluator, Monitor, Archiver

Each agent runs in its own process and communicates via message bus.
"""

__version__ = "2.0.0"

from .core import (
    Agent,
    AgentState,
    AgentCapability,
    RemoteCapableAgent,
    RemoteEnvironmentInfo,
    CoordinatorAgent,
    ProcessManager,
)
from .agents import (
    PlannerAgent,
    ExecutorAgent,
    EvaluatorAgent,
    VerifierAgent,
    MonitorAgent,
    ArchiverAgent,
)
from .messaging import (
    MessageBus,
    Message,
    MessageType,
    create_message_bus,
)
from .config.remote_config import (
    RemoteConfig,
    RemoteConfigLoader,
    get_remote_config,
)

__all__ = [
    # Core
    'Agent',
    'AgentState',
    'AgentCapability',
    'RemoteCapableAgent',
    'RemoteEnvironmentInfo',
    'CoordinatorAgent',
    'ProcessManager',
    # Agents (based on workflow/roles)
    'PlannerAgent',
    'ExecutorAgent',
    'EvaluatorAgent',
    'VerifierAgent',
    'MonitorAgent',
    'ArchiverAgent',
    # Messaging
    'MessageBus',
    'Message',
    'MessageType',
    'create_message_bus',
    # Remote configuration
    'RemoteConfig',
    'RemoteConfigLoader',
    'get_remote_config',
]
