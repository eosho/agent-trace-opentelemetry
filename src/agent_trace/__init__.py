"""Agent Trace - OpenTelemetry-based AI code attribution tracking."""

from agent_trace.models import (
    Contributor,
    ContributorType,
    EventType,
    FileRange,
    HookInput,
    TraceEvent,
)
from agent_trace.tracer import AgentTracer, get_tracer

__version__ = "0.1.0"

__all__ = [
    "AgentTracer",
    "Contributor",
    "ContributorType",
    "EventType",
    "FileRange",
    "HookInput",
    "TraceEvent",
    "__version__",
    "get_tracer",
]
