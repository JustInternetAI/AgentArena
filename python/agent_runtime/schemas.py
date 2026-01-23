"""
Core data schemas for Agent Arena.

Defines the contracts between framework components, user code, and Godot.
"""

import json
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


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
class ToolSchema:
    """Schema for an available tool."""

    name: str
    description: str
    parameters: dict  # JSON Schema format

    def to_openai_format(self) -> dict:
        """
        Convert to OpenAI function calling format.

        Returns:
            Dictionary in OpenAI function calling format
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def to_anthropic_format(self) -> dict:
        """
        Convert to Anthropic tool calling format.

        Returns:
            Dictionary in Anthropic tool calling format
        """
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ToolSchema":
        """
        Create ToolSchema from dictionary.

        Args:
            data: Dictionary with 'name', 'description', and 'parameters'

        Returns:
            ToolSchema instance
        """
        return cls(
            name=data["name"],
            description=data["description"],
            parameters=data["parameters"],
        )


@dataclass
class Observation:
    """What the agent receives from Godot each tick."""

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
        # Parse position (required)
        position = (
            tuple(data["position"]) if isinstance(data["position"], list) else data["position"]
        )

        # Parse optional rotation
        rotation = None
        if "rotation" in data and data["rotation"] is not None:
            rotation = (
                tuple(data["rotation"]) if isinstance(data["rotation"], list) else data["rotation"]
            )

        # Parse optional velocity
        velocity = None
        if "velocity" in data and data["velocity"] is not None:
            velocity = (
                tuple(data["velocity"]) if isinstance(data["velocity"], list) else data["velocity"]
            )

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
            custom=data.get("custom", {}),
        )

    def to_dict(self) -> dict:
        """
        Convert to dictionary for serialization.

        Returns:
            Dictionary representation
        """
        return {
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
            "custom": self.custom,
        }


@dataclass
class AgentDecision:
    """What the agent returns to the framework."""

    tool: str
    params: dict = field(default_factory=dict)
    reasoning: str | None = None

    @classmethod
    def from_llm_response(cls, response: str | dict) -> "AgentDecision":
        """
        Parse LLM JSON response into decision.

        Handles various LLM response formats and malformed JSON gracefully.

        Args:
            response: LLM response (JSON string or dict)

        Returns:
            AgentDecision instance

        Raises:
            ValueError: If response cannot be parsed
        """
        # If already a dict, use it directly
        if isinstance(response, dict):
            data = response
        else:
            # Try to parse JSON
            try:
                data = json.loads(response)
            except json.JSONDecodeError as e:
                # Try to extract JSON from markdown code blocks
                if "```json" in response or "```" in response:
                    # Extract content between ```json and ``` or ``` and ```
                    import re

                    json_match = re.search(r"```(?:json)?\s*\n(.*?)\n```", response, re.DOTALL)
                    if json_match:
                        try:
                            data = json.loads(json_match.group(1))
                        except json.JSONDecodeError:
                            logger.error(f"Failed to parse JSON from code block: {e}")
                            raise ValueError(f"Invalid JSON in LLM response: {e}")
                    else:
                        logger.error(f"Failed to parse LLM response: {e}")
                        raise ValueError(f"Invalid JSON in LLM response: {e}")
                else:
                    logger.error(f"Failed to parse LLM response: {e}")
                    raise ValueError(f"Invalid JSON in LLM response: {e}")

        # Extract fields with defaults
        tool = data.get("tool")
        if not tool:
            # Try alternate field names
            tool = data.get("action") or data.get("tool_name") or data.get("name")

        if not tool:
            logger.warning("No tool specified in LLM response, defaulting to 'idle'")
            tool = "idle"

        params = data.get("params") or data.get("parameters") or data.get("arguments") or {}
        reasoning = data.get("reasoning") or data.get("thought") or data.get("explanation")

        return cls(tool=tool, params=params, reasoning=reasoning)

    @classmethod
    def idle(cls, reasoning: str | None = None) -> "AgentDecision":
        """
        Create an idle decision.

        Args:
            reasoning: Optional explanation for idling

        Returns:
            AgentDecision for idle action
        """
        return cls(tool="idle", params={}, reasoning=reasoning)

    def to_dict(self) -> dict:
        """
        Convert to dictionary for IPC.

        Returns:
            Dictionary representation
        """
        result = {
            "tool": self.tool,
            "params": self.params,
        }
        if self.reasoning is not None:
            result["reasoning"] = self.reasoning
        return result


@dataclass
class SimpleContext:
    """Simplified context for beginners (Layer 1)."""

    position: tuple[float, float, float]
    nearby_resources: list[dict]
    nearby_hazards: list[dict]
    inventory: list[str]
    goal: str | None = None
    tick: int = 0

    @classmethod
    def from_observation(cls, obs: Observation, goal: str | None = None) -> "SimpleContext":
        """
        Create simplified context from full observation.

        Args:
            obs: Full observation from Godot
            goal: Optional goal description

        Returns:
            SimpleContext instance
        """
        # Simplify resources to basic dicts
        nearby_resources = [
            {
                "name": r.name,
                "type": r.type,
                "position": r.position,
                "distance": r.distance,
            }
            for r in obs.nearby_resources
        ]

        # Simplify hazards to basic dicts
        nearby_hazards = [
            {
                "name": h.name,
                "type": h.type,
                "position": h.position,
                "distance": h.distance,
                "damage": h.damage,
            }
            for h in obs.nearby_hazards
        ]

        # Simplify inventory to just item names
        inventory = [item.name for item in obs.inventory]

        return cls(
            position=obs.position,
            nearby_resources=nearby_resources,
            nearby_hazards=nearby_hazards,
            inventory=inventory,
            goal=goal,
            tick=obs.tick,
        )
