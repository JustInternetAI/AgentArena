"""
Agent Arena - Agent Runtime Module

This module provides the core agent runtime infrastructure for LLM-driven agents.
"""

from .agent import Agent
from .arena import AgentArena
from .behavior import AgentBehavior, LLMAgentBehavior, SimpleAgentBehavior
from .local_llm_behavior import LocalLLMBehavior, create_local_llm_behavior
from .memory import AgentMemory, RAGMemory, SlidingWindowMemory, SummarizingMemory
from .runtime import AgentRuntime
from .schemas import (
    AgentDecision,
    Constraint,
    EntityInfo,
    Goal,
    HazardInfo,
    ItemInfo,
    Metric,
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
    # Behaviors
    "AgentBehavior",
    "SimpleAgentBehavior",
    "LLMAgentBehavior",
    "LocalLLMBehavior",
    "create_local_llm_behavior",
    # Memory
    "AgentMemory",
    "SlidingWindowMemory",
    "SummarizingMemory",
    "RAGMemory",
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
]
__version__ = "0.1.0"
