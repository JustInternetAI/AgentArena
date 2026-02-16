"""
Observation schema - what the agent receives from the game each tick.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .objective import Objective


@dataclass
class EntityInfo:
    """Information about a visible entity."""

    id: str
    type: str
    position: tuple[float, float, float]
    distance: float
    metadata: dict = field(default_factory=dict)


@dataclass
class ResourceInfo:
    """Information about a nearby resource."""

    name: str
    type: str
    position: tuple[float, float, float]
    distance: float


@dataclass
class HazardInfo:
    """Information about a nearby hazard."""

    name: str
    type: str
    position: tuple[float, float, float]
    distance: float
    damage: float = 0.0


@dataclass
class ItemInfo:
    """Information about an inventory item."""

    id: str
    name: str
    quantity: int = 1


@dataclass
class ExploreTarget:
    """A potential exploration target."""

    direction: str  # "north", "south", "east", "west", etc.
    distance: float
    position: tuple[float, float, float]


@dataclass
class ExplorationInfo:
    """
    Information about world exploration status.

    Tracks what percentage of the world the agent has seen and
    provides information about unexplored frontiers.
    """

    exploration_percentage: float  # 0-100
    total_cells: int
    seen_cells: int
    frontiers_by_direction: dict[str, float]  # direction -> distance to nearest frontier
    explore_targets: list[ExploreTarget] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "ExplorationInfo":
        """Create from dictionary."""
        targets = []
        for t in data.get("explore_targets", []):
            targets.append(
                ExploreTarget(
                    direction=t["direction"],
                    distance=t["distance"],
                    position=tuple(t["position"]),
                )
            )
        return cls(
            exploration_percentage=data.get("exploration_percentage", 0.0),
            total_cells=data.get("total_cells", 0),
            seen_cells=data.get("seen_cells", 0),
            frontiers_by_direction=data.get("frontiers_by_direction", {}),
            explore_targets=targets,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "exploration_percentage": self.exploration_percentage,
            "total_cells": self.total_cells,
            "seen_cells": self.seen_cells,
            "frontiers_by_direction": self.frontiers_by_direction,
            "explore_targets": [
                {
                    "direction": t.direction,
                    "distance": t.distance,
                    "position": list(t.position),
                }
                for t in self.explore_targets
            ],
        }


@dataclass
class Observation:
    """
    What the agent receives from the game each tick.

    This contains all the information the agent needs to make a decision:
    - Agent state (position, health, energy)
    - Nearby entities (resources, hazards, other agents)
    - Inventory contents
    - Exploration status
    - Scenario objective and progress (NEW in LDX refactor)

    Attributes:
        agent_id: Unique identifier for this agent
        tick: Current simulation tick number
        position: Agent's current position (x, y, z)
        rotation: Agent's current rotation (x, y, z) in degrees
        velocity: Agent's current velocity (x, y, z)
        visible_entities: List of nearby entities the agent can see
        nearby_resources: List of resources within perception range
        nearby_hazards: List of hazards within perception range
        inventory: Items currently held by the agent
        health: Current health (0-100)
        energy: Current energy (0-100)
        exploration: World exploration status (optional)
        scenario_name: Name of the current scenario (e.g., "foraging")
        objective: Scenario-defined goal (NEW)
        current_progress: Current values for objective metrics (NEW)
        custom: Custom fields for scenario-specific data
    """

    agent_id: str
    tick: int
    position: tuple[float, float, float]
    rotation: tuple[float, float, float] | None = None
    velocity: tuple[float, float, float] | None = None
    visible_entities: list[EntityInfo] = field(default_factory=list)
    nearby_resources: list[ResourceInfo] = field(default_factory=list)
    nearby_hazards: list[HazardInfo] = field(default_factory=list)
    inventory: list[ItemInfo] = field(default_factory=list)
    health: float = 100.0
    energy: float = 100.0
    exploration: ExplorationInfo | None = None
    # Objective system fields (NEW for LDX refactor)
    scenario_name: str = ""
    objective: "Objective | None" = None
    current_progress: dict[str, float] = field(default_factory=dict)
    custom: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "Observation":
        """
        Create Observation from IPC dictionary.

        Args:
            data: Dictionary from Godot IPC

        Returns:
            Observation instance
        """
        from .objective import Objective

        # Parse position (required)
        position = tuple(data["position"]) if isinstance(data["position"], list) else data["position"]

        # Parse optional rotation
        rotation = None
        if "rotation" in data and data["rotation"] is not None:
            rotation = tuple(data["rotation"]) if isinstance(data["rotation"], list) else data["rotation"]

        # Parse optional velocity
        velocity = None
        if "velocity" in data and data["velocity"] is not None:
            velocity = tuple(data["velocity"]) if isinstance(data["velocity"], list) else data["velocity"]

        # Parse visible entities
        visible_entities = []
        for entity_data in data.get("visible_entities", []):
            entity_pos = (
                tuple(entity_data["position"])
                if isinstance(entity_data["position"], list)
                else entity_data["position"]
            )
            visible_entities.append(
                EntityInfo(
                    id=entity_data["id"],
                    type=entity_data["type"],
                    position=entity_pos,
                    distance=entity_data["distance"],
                    metadata=entity_data.get("metadata", {}),
                )
            )

        # Parse nearby resources
        nearby_resources = []
        for resource_data in data.get("nearby_resources", []):
            resource_pos = (
                tuple(resource_data["position"])
                if isinstance(resource_data["position"], list)
                else resource_data["position"]
            )
            nearby_resources.append(
                ResourceInfo(
                    name=resource_data["name"],
                    type=resource_data["type"],
                    position=resource_pos,
                    distance=resource_data["distance"],
                )
            )

        # Parse nearby hazards
        nearby_hazards = []
        for hazard_data in data.get("nearby_hazards", []):
            hazard_pos = (
                tuple(hazard_data["position"])
                if isinstance(hazard_data["position"], list)
                else hazard_data["position"]
            )
            nearby_hazards.append(
                HazardInfo(
                    name=hazard_data["name"],
                    type=hazard_data["type"],
                    position=hazard_pos,
                    distance=hazard_data["distance"],
                    damage=hazard_data.get("damage", 0.0),
                )
            )

        # Parse inventory
        inventory = []
        for item_data in data.get("inventory", []):
            inventory.append(
                ItemInfo(
                    id=item_data["id"],
                    name=item_data["name"],
                    quantity=item_data.get("quantity", 1),
                )
            )

        # Parse exploration data
        exploration = None
        if "exploration" in data and data["exploration"]:
            exploration = ExplorationInfo.from_dict(data["exploration"])

        # Parse objective (NEW)
        objective = None
        if "objective" in data and data["objective"]:
            objective = Objective.from_dict(data["objective"])

        return cls(
            agent_id=data["agent_id"],
            tick=data["tick"],
            position=position,
            rotation=rotation,
            velocity=velocity,
            visible_entities=visible_entities,
            nearby_resources=nearby_resources,
            nearby_hazards=nearby_hazards,
            inventory=inventory,
            health=data.get("health", 100.0),
            energy=data.get("energy", 100.0),
            exploration=exploration,
            scenario_name=data.get("scenario_name", ""),
            objective=objective,
            current_progress=data.get("current_progress", {}),
            custom=data.get("custom", {}),
        )

    def to_dict(self) -> dict:
        """
        Convert to dictionary for serialization.

        Returns:
            Dictionary representation
        """
        result = {
            "agent_id": self.agent_id,
            "tick": self.tick,
            "position": list(self.position),
            "rotation": list(self.rotation) if self.rotation else None,
            "velocity": list(self.velocity) if self.velocity else None,
            "visible_entities": [
                {
                    "id": e.id,
                    "type": e.type,
                    "position": list(e.position),
                    "distance": e.distance,
                    "metadata": e.metadata,
                }
                for e in self.visible_entities
            ],
            "nearby_resources": [
                {
                    "name": r.name,
                    "type": r.type,
                    "position": list(r.position),
                    "distance": r.distance,
                }
                for r in self.nearby_resources
            ],
            "nearby_hazards": [
                {
                    "name": h.name,
                    "type": h.type,
                    "position": list(h.position),
                    "distance": h.distance,
                    "damage": h.damage,
                }
                for h in self.nearby_hazards
            ],
            "inventory": [
                {
                    "id": i.id,
                    "name": i.name,
                    "quantity": i.quantity,
                }
                for i in self.inventory
            ],
            "health": self.health,
            "energy": self.energy,
            "exploration": self.exploration.to_dict() if self.exploration else None,
            "scenario_name": self.scenario_name,
            "objective": self.objective.to_dict() if self.objective else None,
            "current_progress": self.current_progress,
            "custom": self.custom,
        }
        return result
