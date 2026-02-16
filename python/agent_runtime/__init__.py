"""
Agent Arena - Agent Runtime Module

This module provides the core agent runtime infrastructure for LLM-driven agents.

NOTE: After LDX refactor (Issue #60), behavior base classes and memory systems
have been moved to starter templates. Use agent-arena-sdk for new projects.
"""

from .agent import Agent
from .arena import AgentArena
from .reasoning_trace import (
    ReasoningTrace,
    TraceStep,
    TraceStore,
    # Backwards compatibility
    DecisionCapture,
    InspectorEntry,
    InspectorStage,
    PromptInspector,
    TraceStepName,
    get_global_inspector,
    get_global_trace_store,
    set_global_inspector,
    set_global_trace_store,
)
from .runtime import AgentRuntime
from .schemas import (
    AgentDecision,
    Constraint,
    EntityInfo,
    Goal,
    HazardInfo,
    ItemInfo,
    Metric,
    MetricDefinition,
    Objective,
    Observation,
    ResourceInfo,
    ScenarioDefinition,
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
    # Observation/Decision schemas
    "Observation",
    "AgentDecision",
    "SimpleContext",
    "ToolSchema",
    "EntityInfo",
    "ResourceInfo",
    "HazardInfo",
    "ItemInfo",
    # Scenario schemas
    "ScenarioDefinition",
    "Goal",
    "Constraint",
    "Metric",
    # Objective system (Issue #60)
    "Objective",
    "MetricDefinition",
]
__version__ = "0.1.0"
