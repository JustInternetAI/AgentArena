"""
Agent Runtime schemas (DEPRECATED — use agent_arena_sdk for new projects).

Shared types (Observation, EntityInfo, etc.) are re-exported from the SDK,
which is the single source of truth.  V1-only classes that still have
internal consumers are kept here.
"""

import json
import logging
import warnings
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Re-exports from SDK (single source of truth)
# ---------------------------------------------------------------------------
from agent_arena_sdk.schemas import (  # noqa: F401
    EntityInfo,
    ExplorationInfo,
    ExploreTarget,
    HazardInfo,
    ItemInfo,
    MetricDefinition,
    Objective,
    Observation,
    ResourceInfo,
    StationInfo,
    ToolResult,
    ToolSchema,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# V1-only classes (still used by agent_runtime internals)
# ---------------------------------------------------------------------------


@dataclass
class WorldObject:
    """A remembered object in the world map.

    .. deprecated::
        Use ``agent_arena_sdk.schemas.WorldObject`` instead.
        This import path will be removed in v0.2.0.
    """

    name: str
    object_type: str  # "resource", "hazard", "entity"
    subtype: str  # e.g., "berry", "fire", "agent"
    position: tuple[float, float, float]
    last_seen_tick: int
    status: str = "active"  # "active", "collected", "destroyed", "unknown"
    damage: float = 0.0  # For hazards
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        warnings.warn(
            "agent_runtime.schemas.WorldObject is deprecated. "
            "Use 'from agent_arena_sdk.schemas import WorldObject' instead. "
            "This import path will be removed in v0.2.0.",
            DeprecationWarning,
            stacklevel=2,
        )

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

    .. deprecated::
        Use ``agent_arena_sdk.schemas.ExperienceEvent`` instead.
        This import path will be removed in v0.2.0.
    """

    tick: int
    event_type: str  # "collision", "damage", "trapped", "collected"
    description: str
    position: tuple[float, float, float]
    object_name: str | None = None
    damage_taken: float = 0.0
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        warnings.warn(
            "agent_runtime.schemas.ExperienceEvent is deprecated. "
            "Use 'from agent_arena_sdk.schemas import ExperienceEvent' instead. "
            "This import path will be removed in v0.2.0.",
            DeprecationWarning,
            stacklevel=2,
        )

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
