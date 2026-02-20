"""
Schemas for Agent Arena SDK.

This module exports all data schemas used for communication between
the game and agent code.
"""

from .decision import Decision
from .objective import MetricDefinition, Objective
from .observation import (
    EntityInfo,
    ExplorationInfo,
    ExploreTarget,
    HazardInfo,
    ItemInfo,
    Observation,
    ResourceInfo,
    StationInfo,
)
from .tools import ToolSchema

__all__ = [
    # Decision
    "Decision",
    # Objective system
    "Objective",
    "MetricDefinition",
    # Observation and related info types
    "Observation",
    "EntityInfo",
    "ResourceInfo",
    "HazardInfo",
    "StationInfo",
    "ItemInfo",
    "ExplorationInfo",
    "ExploreTarget",
    # Tools
    "ToolSchema",
]
