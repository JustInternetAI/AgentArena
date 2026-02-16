"""
Agent Arena SDK - Minimal SDK for building AI agents.

This SDK provides only the essential components for communication with
the Agent Arena game. All agent logic (memory, planning, LLM integration)
lives in your code, not hidden in a framework.

Quick Start:
    from agent_arena_sdk import AgentArena, Observation, Decision

    def decide(obs: Observation) -> Decision:
        if obs.nearby_resources:
            resource = obs.nearby_resources[0]
            return Decision(
                tool="move_to",
                params={"target_position": resource.position}
            )
        return Decision.idle()

    arena = AgentArena()
    arena.run(decide)

For complete examples, see the starter templates in the AgentArena repository.
"""

from .arena import AgentArena
from .schemas import (
    Decision,
    EntityInfo,
    ExplorationInfo,
    ExploreTarget,
    HazardInfo,
    ItemInfo,
    MetricDefinition,
    Objective,
    Observation,
    ResourceInfo,
    ToolSchema,
)

__version__ = "0.1.0"

__all__ = [
    # Main API
    "AgentArena",
    # Core schemas
    "Observation",
    "Decision",
    # Objective system
    "Objective",
    "MetricDefinition",
    # Info types
    "EntityInfo",
    "ResourceInfo",
    "HazardInfo",
    "ItemInfo",
    "ExplorationInfo",
    "ExploreTarget",
    # Tools
    "ToolSchema",
]
