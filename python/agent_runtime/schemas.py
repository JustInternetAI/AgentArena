"""
Core data schemas for Agent Arena.

Defines the contracts between framework components, user code, and Godot.
"""

import json
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


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
        Parse LLM response into decision, supporting chain-of-thought format.

        Handles various LLM response formats:
        - Pure JSON: {"tool": "move_to", ...}
        - Chain-of-thought: THINKING: ... ACTION: {"tool": ...}
        - Markdown code blocks: ```json ... ```
        - JSON embedded in text

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
            reasoning_text = None
        else:
            import re

            data = None
            reasoning_text = None

            # Check for Chain-of-Thought format: THINKING: ... ACTION: ...
            thinking_match = re.search(
                r"THINKING:\s*(.*?)(?=ACTION:|$)", response, re.DOTALL | re.IGNORECASE
            )
            if thinking_match:
                reasoning_text = thinking_match.group(1).strip()

            # Look for ACTION: section first (CoT format)
            action_match = re.search(r"ACTION:\s*(\{.*)", response, re.DOTALL | re.IGNORECASE)
            if action_match:
                action_text = action_match.group(1)
                # Extract JSON from action section
                brace_start = action_text.find("{")
                if brace_start != -1:
                    depth = 0
                    for i, char in enumerate(action_text[brace_start:], brace_start):
                        if char == "{":
                            depth += 1
                        elif char == "}":
                            depth -= 1
                            if depth == 0:
                                json_str = action_text[brace_start : i + 1]
                                try:
                                    data = json.loads(json_str)
                                    break
                                except json.JSONDecodeError:
                                    pass

            # Try to parse JSON directly first
            if data is None:
                try:
                    data = json.loads(response)
                except json.JSONDecodeError:
                    pass

            # Try to extract JSON from markdown code blocks
            if data is None and ("```json" in response or "```" in response):
                json_match = re.search(r"```(?:json)?\s*\n(.*?)\n```", response, re.DOTALL)
                if json_match:
                    try:
                        data = json.loads(json_match.group(1))
                    except json.JSONDecodeError:
                        pass

            # Try to find JSON object embedded in text
            if data is None:
                # Look for {"tool": pattern which is our expected format
                json_match = re.search(r'\{[^{}]*"tool"[^{}]*\}', response)
                if json_match:
                    try:
                        data = json.loads(json_match.group(0))
                    except json.JSONDecodeError:
                        pass

                # Try finding any JSON object with nested braces
                if data is None:
                    # Find JSON objects - match balanced braces
                    brace_start = response.find("{")
                    if brace_start != -1:
                        depth = 0
                        for i, char in enumerate(response[brace_start:], brace_start):
                            if char == "{":
                                depth += 1
                            elif char == "}":
                                depth -= 1
                                if depth == 0:
                                    json_str = response[brace_start : i + 1]
                                    try:
                                        data = json.loads(json_str)
                                        break
                                    except json.JSONDecodeError:
                                        # Try next occurrence
                                        brace_start = response.find("{", i + 1)
                                        if brace_start == -1:
                                            break
                                        depth = 0

            # Last resort: try to recover from truncated JSON
            # This handles cases where finish_reason="length" truncated the output
            if data is None:
                data = cls._recover_truncated_json(response)

            if data is None:
                logger.error("Failed to parse LLM response: No valid JSON found")
                raise ValueError("Invalid JSON in LLM response: No valid JSON found")

        # At this point data is guaranteed to be a dict (mypy needs explicit assertion)
        assert data is not None

        # Extract fields with defaults
        tool = data.get("tool")
        if not tool:
            # Try alternate field names
            tool = data.get("action") or data.get("tool_name") or data.get("name")

        if not tool:
            logger.warning("No tool specified in LLM response, defaulting to 'idle'")
            tool = "idle"

        params = data.get("params") or data.get("parameters") or data.get("arguments") or {}

        # Prefer extracted chain-of-thought reasoning over JSON field
        reasoning = None
        if reasoning_text:
            reasoning = reasoning_text
        else:
            reasoning = data.get("reasoning") or data.get("thought") or data.get("explanation")

        return cls(tool=tool, params=params, reasoning=reasoning)

    @classmethod
    def _recover_truncated_json(cls, response: str) -> dict | None:
        """
        Attempt to recover tool and params from truncated JSON.

        When the LLM hits the token limit (finish_reason="length"), the JSON
        may be cut off mid-way. This method tries to extract the essential
        fields (tool and params) even from incomplete JSON.

        Args:
            response: The truncated LLM response

        Returns:
            Dictionary with tool and params, or None if recovery fails
        """
        import re

        # Look for the ACTION section
        action_match = re.search(r"ACTION:\s*(\{.*)", response, re.DOTALL | re.IGNORECASE)
        if not action_match:
            # Try to find any JSON-like structure
            action_match = re.search(r'(\{"tool".*)', response, re.DOTALL)

        if not action_match:
            return None

        json_fragment = action_match.group(1)

        # Extract tool name
        tool_match = re.search(r'"tool"\s*:\s*"([^"]+)"', json_fragment)
        if not tool_match:
            return None

        tool = tool_match.group(1)
        params = {}

        # Try to extract params - look for complete nested object
        params_match = re.search(r'"params"\s*:\s*(\{[^{}]*\})', json_fragment)
        if params_match:
            try:
                params = json.loads(params_match.group(1))
            except json.JSONDecodeError:
                # Try to extract just target_position array
                pos_match = re.search(r'"target_position"\s*:\s*\[([-\d.,\s]+)\]', json_fragment)
                if pos_match:
                    try:
                        coords = [float(x.strip()) for x in pos_match.group(1).split(",")]
                        params = {"target_position": coords}
                    except ValueError:
                        pass

                # Try to extract target string
                target_match = re.search(r'"target"\s*:\s*"([^"]+)"', json_fragment)
                if target_match:
                    params["target"] = target_match.group(1)

        logger.warning(f"Recovered truncated JSON: tool={tool}, params={params}")

        return {"tool": tool, "params": params}

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


# =============================================================================
# Scenario Definition Schemas
# =============================================================================


@dataclass
class Goal:
    """A scenario goal that the agent should achieve."""

    name: str
    description: str
    success_condition: str  # Human-readable description of success
    priority: int = 1  # Lower = higher priority
    optional: bool = False


@dataclass
class Constraint:
    """A constraint or rule the agent must follow."""

    name: str
    description: str
    penalty: str | None = None  # What happens if violated


@dataclass
class Metric:
    """A metric used to evaluate agent performance."""

    name: str
    description: str
    unit: str | None = None
    optimize: str = "maximize"  # "maximize", "minimize", or "target"
    target_value: float | None = None  # For "target" optimization


@dataclass
class ScenarioDefinition:
    """
    Complete definition of a scenario for both LLM agents and documentation.

    This is the single source of truth for scenario information:
    - LLM agents use it to understand their task
    - Documentation is auto-generated from it
    - Framework validates against it
    """

    # Identity (required fields first - no defaults)
    name: str
    id: str  # Machine-readable identifier (e.g., "foraging")
    tier: int  # Learning tier: 1=beginner, 2=intermediate, 3=advanced
    description: str

    # Optional fields with defaults
    version: str = "1.0.0"
    backstory: str | None = None  # Optional narrative context

    # Goals and constraints
    goals: list[Goal] = field(default_factory=list)
    constraints: list[Constraint] = field(default_factory=list)

    # Available tools (references to tool names, full schemas loaded separately)
    available_tools: list[str] = field(default_factory=list)

    # Success metrics
    metrics: list[Metric] = field(default_factory=list)
    success_threshold: dict = field(default_factory=dict)  # Metric name -> value

    # Perception info
    perception_info: dict = field(default_factory=dict)  # What agent can observe

    # Hints for learners (not sent to LLM by default)
    hints: list[str] = field(default_factory=list)
    learning_objectives: list[str] = field(default_factory=list)

    # Resource types in this scenario
    resource_types: list[dict] = field(default_factory=list)
    hazard_types: list[dict] = field(default_factory=list)

    def to_system_prompt(self, include_hints: bool = False) -> str:
        """
        Generate a system prompt section for LLM agents.

        Args:
            include_hints: Whether to include learner hints

        Returns:
            Formatted string for system prompt
        """
        sections = []

        # Scenario overview
        sections.append(f"# Scenario: {self.name}\n")
        sections.append(self.description)
        if self.backstory:
            sections.append(f"\n{self.backstory}")

        # Goals
        sections.append("\n## Goals")
        for goal in sorted(self.goals, key=lambda g: g.priority):
            optional_tag = " (optional)" if goal.optional else ""
            sections.append(f"- **{goal.name}**{optional_tag}: {goal.description}")
            sections.append(f"  - Success: {goal.success_condition}")

        # Constraints
        if self.constraints:
            sections.append("\n## Constraints")
            for constraint in self.constraints:
                sections.append(f"- **{constraint.name}**: {constraint.description}")
                if constraint.penalty:
                    sections.append(f"  - Penalty: {constraint.penalty}")

        # Available tools
        if self.available_tools:
            sections.append("\n## Available Tools")
            for tool_name in self.available_tools:
                sections.append(f"- `{tool_name}`")

        # Perception info
        if self.perception_info:
            sections.append("\n## Perception")
            for key, value in self.perception_info.items():
                sections.append(f"- **{key}**: {value}")

        # Resource types
        if self.resource_types:
            sections.append("\n## Resource Types")
            for rt in self.resource_types:
                sections.append(f"- **{rt['name']}** ({rt['type']}): {rt.get('description', '')}")

        # Hazard types
        if self.hazard_types:
            sections.append("\n## Hazard Types")
            for ht in self.hazard_types:
                sections.append(
                    f"- **{ht['name']}** ({ht['type']}): {ht.get('description', '')} "
                    f"[Damage: {ht.get('damage', 'unknown')}]"
                )

        # Success metrics
        if self.metrics:
            sections.append("\n## Success Metrics")
            for metric in self.metrics:
                unit_str = f" ({metric.unit})" if metric.unit else ""
                sections.append(f"- **{metric.name}**{unit_str}: {metric.description}")
                if metric.optimize == "target" and metric.target_value is not None:
                    sections.append(f"  - Target: {metric.target_value}")
                else:
                    sections.append(f"  - Goal: {metric.optimize}")

        # Optional hints
        if include_hints and self.hints:
            sections.append("\n## Hints")
            for hint in self.hints:
                sections.append(f"- {hint}")

        return "\n".join(sections)

    def to_markdown(self) -> str:
        """
        Generate full markdown documentation for learners.

        Returns:
            Complete markdown document
        """
        sections = []

        # Header
        sections.append(f"# {self.name}")
        sections.append(
            f"\n**Tier:** {self.tier} | **ID:** `{self.id}` | **Version:** {self.version}\n"
        )

        # Description
        sections.append("## Overview\n")
        sections.append(self.description)
        if self.backstory:
            sections.append(f"\n> {self.backstory}")

        # Learning objectives
        if self.learning_objectives:
            sections.append("\n## Learning Objectives\n")
            sections.append("After completing this scenario, you will understand:\n")
            for obj in self.learning_objectives:
                sections.append(f"- {obj}")

        # Goals
        sections.append("\n## Goals\n")
        for goal in sorted(self.goals, key=lambda g: g.priority):
            priority_badge = f"[Priority {goal.priority}]" if goal.priority > 1 else "[Primary]"
            optional_badge = " *(Optional)*" if goal.optional else ""
            sections.append(f"### {goal.name} {priority_badge}{optional_badge}\n")
            sections.append(goal.description)
            sections.append(f"\n**Success Condition:** {goal.success_condition}\n")

        # Constraints
        if self.constraints:
            sections.append("## Constraints\n")
            sections.append("Your agent must operate within these rules:\n")
            sections.append("| Constraint | Description | Penalty |")
            sections.append("|------------|-------------|---------|")
            for constraint in self.constraints:
                penalty = constraint.penalty or "None"
                sections.append(f"| {constraint.name} | {constraint.description} | {penalty} |")
            sections.append("")

        # Available tools
        if self.available_tools:
            sections.append("## Available Tools\n")
            sections.append("Your agent can use these tools:\n")
            for tool_name in self.available_tools:
                sections.append(f"- `{tool_name}`")
            sections.append("\nSee the [Tool Reference](../api_reference/tools.md) for details.\n")

        # Perception
        if self.perception_info:
            sections.append("## What Your Agent Can See\n")
            for key, value in self.perception_info.items():
                sections.append(f"- **{key}**: {value}")
            sections.append("")

        # Resources and hazards
        if self.resource_types:
            sections.append("## Resources\n")
            sections.append("| Type | Name | Description |")
            sections.append("|------|------|-------------|")
            for rt in self.resource_types:
                sections.append(f"| {rt['type']} | {rt['name']} | {rt.get('description', '')} |")
            sections.append("")

        if self.hazard_types:
            sections.append("## Hazards\n")
            sections.append("| Type | Name | Damage | Description |")
            sections.append("|------|------|--------|-------------|")
            for ht in self.hazard_types:
                sections.append(
                    f"| {ht['type']} | {ht['name']} | {ht.get('damage', '?')} | "
                    f"{ht.get('description', '')} |"
                )
            sections.append("")

        # Metrics
        if self.metrics:
            sections.append("## Success Metrics\n")
            sections.append("Your agent will be evaluated on:\n")
            sections.append("| Metric | Description | Goal |")
            sections.append("|--------|-------------|------|")
            for metric in self.metrics:
                goal_str = metric.optimize
                if metric.optimize == "target" and metric.target_value is not None:
                    goal_str = f"Target: {metric.target_value}"
                unit_str = f" ({metric.unit})" if metric.unit else ""
                sections.append(f"| {metric.name}{unit_str} | {metric.description} | {goal_str} |")
            sections.append("")

        # Hints
        if self.hints:
            sections.append("## Hints\n")
            sections.append(
                "<details>\n<summary>Click to reveal hints (try without them first!)</summary>\n"
            )
            for i, hint in enumerate(self.hints, 1):
                sections.append(f"{i}. {hint}")
            sections.append("\n</details>\n")

        return "\n".join(sections)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "id": self.id,
            "tier": self.tier,
            "version": self.version,
            "description": self.description,
            "backstory": self.backstory,
            "goals": [
                {
                    "name": g.name,
                    "description": g.description,
                    "success_condition": g.success_condition,
                    "priority": g.priority,
                    "optional": g.optional,
                }
                for g in self.goals
            ],
            "constraints": [
                {
                    "name": c.name,
                    "description": c.description,
                    "penalty": c.penalty,
                }
                for c in self.constraints
            ],
            "available_tools": self.available_tools,
            "metrics": [
                {
                    "name": m.name,
                    "description": m.description,
                    "unit": m.unit,
                    "optimize": m.optimize,
                    "target_value": m.target_value,
                }
                for m in self.metrics
            ],
            "success_threshold": self.success_threshold,
            "perception_info": self.perception_info,
            "hints": self.hints,
            "learning_objectives": self.learning_objectives,
            "resource_types": self.resource_types,
            "hazard_types": self.hazard_types,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ScenarioDefinition":
        """Create from dictionary."""
        goals = [
            Goal(
                name=g["name"],
                description=g["description"],
                success_condition=g["success_condition"],
                priority=g.get("priority", 1),
                optional=g.get("optional", False),
            )
            for g in data.get("goals", [])
        ]

        constraints = [
            Constraint(
                name=c["name"],
                description=c["description"],
                penalty=c.get("penalty"),
            )
            for c in data.get("constraints", [])
        ]

        metrics = [
            Metric(
                name=m["name"],
                description=m["description"],
                unit=m.get("unit"),
                optimize=m.get("optimize", "maximize"),
                target_value=m.get("target_value"),
            )
            for m in data.get("metrics", [])
        ]

        return cls(
            name=data["name"],
            id=data["id"],
            tier=data.get("tier", 1),
            version=data.get("version", "1.0.0"),
            description=data["description"],
            backstory=data.get("backstory"),
            goals=goals,
            constraints=constraints,
            available_tools=data.get("available_tools", []),
            metrics=metrics,
            success_threshold=data.get("success_threshold", {}),
            perception_info=data.get("perception_info", {}),
            hints=data.get("hints", []),
            learning_objectives=data.get("learning_objectives", []),
            resource_types=data.get("resource_types", []),
            hazard_types=data.get("hazard_types", []),
        )
