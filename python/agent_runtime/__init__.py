"""
Agent Arena - Agent Runtime Module (DEPRECATED)

This module provides the core agent runtime infrastructure for LLM-driven agents.

DEPRECATED: Use agent_arena_sdk for new projects. Shared types (Observation,
EntityInfo, etc.) are re-exported from the SDK. V1-only classes (AgentDecision,
WorldObject, SimpleContext) are still available here.
"""

from .agent import Agent
from .arena import AgentArena
from .reasoning_trace import (
    # Backwards compatibility
    DecisionCapture,
    InspectorEntry,
    InspectorStage,
    PromptInspector,
    ReasoningTrace,
    TraceStep,
    TraceStepName,
    TraceStore,
    get_global_inspector,
    get_global_trace_store,
    set_global_inspector,
    set_global_trace_store,
)
from .runtime import AgentRuntime
from .schemas import (
    AgentDecision,
    EntityInfo,
    HazardInfo,
    ItemInfo,
    MetricDefinition,
    Objective,
    Observation,
    ResourceInfo,
    SimpleContext,
    ToolSchema,
)
from .tool_dispatcher import ToolDispatcher

__all__ = [
    # Core
    "Agent",
    "AgentArena",
    "AgentRuntime",
    "ToolDispatcher",
    # Tracing (new API)
    "TraceStep",
    "ReasoningTrace",
    "TraceStore",
    "TraceStepName",
    "get_global_trace_store",
    "set_global_trace_store",
    # Tracing (backwards compatibility)
    "PromptInspector",
    "DecisionCapture",
    "InspectorEntry",
    "InspectorStage",
    "get_global_inspector",
    "set_global_inspector",
    # Observation/Decision schemas (re-exported from SDK)
    "Observation",
    "AgentDecision",
    "SimpleContext",
    "ToolSchema",
    "EntityInfo",
    "ResourceInfo",
    "HazardInfo",
    "ItemInfo",
    # Objective system (Issue #60)
    "Objective",
    "MetricDefinition",
]
__version__ = "0.1.0"
