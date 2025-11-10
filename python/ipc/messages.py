"""
Message schemas for IPC communication between Godot and Python.

These define the structure of data exchanged during simulation ticks.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PerceptionMessage:
    """
    Perception data sent from Godot to Python for a single agent.

    Contains all observations the agent receives from the simulation.
    """

    agent_id: str
    tick: int
    position: list[float]  # [x, y, z]
    rotation: list[float]  # [x, y, z] euler angles
    velocity: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    visible_entities: list[dict[str, Any]] = field(default_factory=list)
    inventory: list[dict[str, Any]] = field(default_factory=list)
    health: float = 100.0
    energy: float = 100.0
    custom_data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PerceptionMessage":
        """Create PerceptionMessage from dictionary."""
        return cls(
            agent_id=data["agent_id"],
            tick=data["tick"],
            position=data.get("position", [0.0, 0.0, 0.0]),
            rotation=data.get("rotation", [0.0, 0.0, 0.0]),
            velocity=data.get("velocity", [0.0, 0.0, 0.0]),
            visible_entities=data.get("visible_entities", []),
            inventory=data.get("inventory", []),
            health=data.get("health", 100.0),
            energy=data.get("energy", 100.0),
            custom_data=data.get("custom_data", {}),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "agent_id": self.agent_id,
            "tick": self.tick,
            "position": self.position,
            "rotation": self.rotation,
            "velocity": self.velocity,
            "visible_entities": self.visible_entities,
            "inventory": self.inventory,
            "health": self.health,
            "energy": self.energy,
            "custom_data": self.custom_data,
        }


@dataclass
class ActionMessage:
    """
    Action decision sent from Python to Godot for a single agent.

    Contains the tool call and parameters for the agent to execute.
    """

    agent_id: str
    tick: int
    tool: str
    params: dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""  # Optional explanation of decision

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ActionMessage":
        """Create ActionMessage from dictionary."""
        return cls(
            agent_id=data["agent_id"],
            tick=data["tick"],
            tool=data["tool"],
            params=data.get("params", {}),
            reasoning=data.get("reasoning", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "agent_id": self.agent_id,
            "tick": self.tick,
            "tool": self.tool,
            "params": self.params,
            "reasoning": self.reasoning,
        }


@dataclass
class TickRequest:
    """
    Request sent from Godot to Python containing all agent perceptions for a tick.
    """

    tick: int
    perceptions: list[PerceptionMessage]
    simulation_state: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TickRequest":
        """Create TickRequest from dictionary."""
        perceptions = [PerceptionMessage.from_dict(p) for p in data.get("perceptions", [])]
        return cls(
            tick=data["tick"],
            perceptions=perceptions,
            simulation_state=data.get("simulation_state", {}),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "tick": self.tick,
            "perceptions": [p.to_dict() for p in self.perceptions],
            "simulation_state": self.simulation_state,
        }


@dataclass
class TickResponse:
    """
    Response sent from Python to Godot containing all agent actions for a tick.
    """

    tick: int
    actions: list[ActionMessage]
    metrics: dict[str, Any] = field(default_factory=dict)  # Performance metrics

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TickResponse":
        """Create TickResponse from dictionary."""
        actions = [ActionMessage.from_dict(a) for a in data.get("actions", [])]
        return cls(
            tick=data["tick"],
            actions=actions,
            metrics=data.get("metrics", {}),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "tick": self.tick,
            "actions": [a.to_dict() for a in self.actions],
            "metrics": self.metrics,
        }
