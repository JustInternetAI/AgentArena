"""
Spatial memory schemas for Agent Arena SDK.

Defines data structures for spatial memory system that tracks objects
(resources, hazards, entities) by their position in the world.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .observation import EntityInfo, HazardInfo, ResourceInfo


@dataclass
class WorldObject:
    """A remembered object in the world map.

    Used by SpatialMemory to track resources, hazards, and entities
    that the agent has seen, even when they're out of line-of-sight.
    """

    name: str
    object_type: str  # "resource", "hazard", "entity"
    subtype: str  # e.g., "berry", "fire", "agent"
    position: tuple[float, float, float]
    last_seen_tick: int
    status: str = "active"  # "active", "collected", "destroyed", "unknown"
    damage: float = 0.0  # For hazards
    metadata: dict = field(default_factory=dict)

    def distance_to(self, pos: tuple[float, float, float]) -> float:
        """Calculate distance to another position."""
        import math

        return math.sqrt(
            (self.position[0] - pos[0]) ** 2
            + (self.position[1] - pos[1]) ** 2
            + (self.position[2] - pos[2]) ** 2
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "object_type": self.object_type,
            "subtype": self.subtype,
            "position": list(self.position),
            "last_seen_tick": self.last_seen_tick,
            "status": self.status,
            "damage": self.damage,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorldObject":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            object_type=data["object_type"],
            subtype=data["subtype"],
            position=tuple(data["position"]),
            last_seen_tick=data["last_seen_tick"],
            status=data.get("status", "active"),
            damage=data.get("damage", 0.0),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_resource(cls, resource: "ResourceInfo", tick: int) -> "WorldObject":
        """Create from ResourceInfo."""
        return cls(
            name=resource.name,
            object_type="resource",
            subtype=resource.type,
            position=resource.position,
            last_seen_tick=tick,
        )

    @classmethod
    def from_hazard(cls, hazard: "HazardInfo", tick: int) -> "WorldObject":
        """Create from HazardInfo."""
        return cls(
            name=hazard.name,
            object_type="hazard",
            subtype=hazard.type,
            position=hazard.position,
            last_seen_tick=tick,
            damage=hazard.damage,
        )

    @classmethod
    def from_entity(cls, entity: "EntityInfo", tick: int) -> "WorldObject":
        """Create from EntityInfo."""
        return cls(
            name=entity.id,
            object_type="entity",
            subtype=entity.type,
            position=entity.position,
            last_seen_tick=tick,
            metadata=entity.metadata,
        )


@dataclass
class ExperienceEvent:
    """A significant event the agent experienced.

    Used by SpatialMemory to track collisions, damage, and other
    experiences so the LLM can learn from past mistakes.
    """

    tick: int
    event_type: str  # "collision", "damage", "trapped", "collected"
    description: str
    position: tuple[float, float, float]
    object_name: str | None = None
    damage_taken: float = 0.0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "tick": self.tick,
            "event_type": self.event_type,
            "description": self.description,
            "position": list(self.position),
            "object_name": self.object_name,
            "damage_taken": self.damage_taken,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ExperienceEvent":
        """Create from dictionary."""
        return cls(
            tick=data["tick"],
            event_type=data["event_type"],
            description=data["description"],
            position=tuple(data["position"]),
            object_name=data.get("object_name"),
            damage_taken=data.get("damage_taken", 0.0),
            metadata=data.get("metadata", {}),
        )


@dataclass
class SpatialQueryResult:
    """Result from a spatial memory query."""

    obj: WorldObject
    distance: float  # Distance from query position
    score: float  # Semantic similarity score (if semantic query)
    staleness: int  # Ticks since last seen
