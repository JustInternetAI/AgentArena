"""
Base adapter for LLM framework integrations.

Provides shared utilities that all framework adapters need:
- Observation formatting (game state -> text for LLM prompts)
- Canonical action tool definitions
- Fallback decision logic when the LLM fails
"""

from abc import ABC, abstractmethod

from ..schemas import Decision, Observation, ToolSchema


class FrameworkAdapter(ABC):
    """
    Base class for framework-specific adapters.

    Subclasses implement ``decide()`` with their framework's LLM client.
    The base class provides shared utilities so each adapter doesn't
    duplicate observation formatting or tool definitions.

    Example::

        class MyAdapter(FrameworkAdapter):
            def decide(self, obs: Observation) -> Decision:
                context = self.format_observation(obs)
                tools = self.get_action_tools()
                # ... call your LLM with context and tools ...
                return Decision(tool="move_to", params={...})

        arena = AgentArena()
        arena.run(MyAdapter())
    """

    @abstractmethod
    def decide(self, obs: Observation) -> Decision:
        """Make a decision given an observation. Subclasses must implement."""
        ...

    def format_observation(self, obs: Observation) -> str:
        """
        Format an observation into human-readable text for an LLM prompt.

        Includes: position, health, energy, nearby resources/hazards/stations,
        inventory, exploration status, objective progress, and last tool result.

        Override to customize how observations are presented to your LLM.
        """
        lines: list[str] = []

        # Header
        lines.append(
            f"Tick: {obs.tick} | Position: ({obs.position[0]:.1f}, "
            f"{obs.position[1]:.1f}, {obs.position[2]:.1f}) | "
            f"Health: {obs.health:.0f} | Energy: {obs.energy:.0f}"
        )

        # Perception
        perception = getattr(obs, "perception_radius", 50.0)
        exploration_pct = 0.0
        if obs.exploration:
            exploration_pct = obs.exploration.exploration_percentage
        lines.append(f"Perception: {perception:.0f} units | Explored: {exploration_pct:.1f}%")
        lines.append("")

        # Resources (top 5)
        if obs.nearby_resources:
            summaries = [
                f"{r.name} ({r.type}) dist={r.distance:.1f} pos={list(r.position)}"
                for r in obs.nearby_resources[:5]
            ]
            lines.append(f"Resources: {'; '.join(summaries)}")
        else:
            lines.append("Resources: None")

        # Hazards (top 5)
        if obs.nearby_hazards:
            summaries = [
                f"{h.name} ({h.type}) dist={h.distance:.1f} pos={list(h.position)}"
                for h in obs.nearby_hazards[:5]
            ]
            lines.append(f"Hazards: {'; '.join(summaries)}")
        else:
            lines.append("Hazards: None")

        # Stations (top 5)
        if obs.nearby_stations:
            summaries = [
                f"{s.name} ({s.type}) dist={s.distance:.1f} pos={list(s.position)}"
                for s in obs.nearby_stations[:5]
            ]
            lines.append(f"Stations: {'; '.join(summaries)}")
        else:
            lines.append("Stations: None")

        # Inventory (handles both dict format from custom and ItemInfo list)
        raw_inventory = obs.custom.get("inventory", {}) if obs.custom else {}
        if raw_inventory:
            inv_str = ", ".join(f"{k}: {v}" for k, v in raw_inventory.items())
            lines.append(f"Inventory: {inv_str}")
        elif obs.inventory:
            inv_str = ", ".join(f"{item.name} x{item.quantity}" for item in obs.inventory)
            lines.append(f"Inventory: {inv_str}")
        else:
            lines.append("Inventory: Empty")

        lines.append("")

        # Exploration targets (top 4)
        if obs.exploration and obs.exploration.explore_targets:
            targets = [
                f"{t.direction} pos={list(t.position)} ({t.distance:.1f}u away)"
                for t in obs.exploration.explore_targets[:4]
            ]
            lines.append(f"Exploration targets: {'; '.join(targets)}")
        else:
            lines.append("Exploration targets: None")

        # Exploration hint when no resources visible
        if not obs.nearby_resources:
            if obs.exploration and obs.exploration.explore_targets:
                best = obs.exploration.explore_targets[0]
                pos = list(best.position)
                lines.append(
                    f"No resources visible! Use explore or move_to an "
                    f"exploration target to find them. Nearest: {pos}"
                )
            else:
                lines.append("No resources visible! Move to an unexplored area to find them.")

        # Objective
        if obs.objective:
            lines.append("")
            lines.append(f"Objective: {obs.objective.description}")
            if obs.current_progress:
                progress_parts = []
                for metric, value in obs.current_progress.items():
                    target = ""
                    if obs.objective.success_metrics and metric in obs.objective.success_metrics:
                        target = f"/{obs.objective.success_metrics[metric].target:.0f}"
                    progress_parts.append(f"{metric}: {value:.0f}{target}")
                lines.append(f"Progress: {', '.join(progress_parts)}")

        # Last tool result
        if obs.last_tool_result:
            tr = obs.last_tool_result
            status = "OK" if tr.success else f"FAILED: {tr.error}"
            lines.append(f"Last action: {tr.tool} -> {status}")

        return "\n".join(lines)

    def get_action_tools(self) -> list[ToolSchema]:
        """
        Return the canonical set of action tools.

        These are terminal tools — calling one ends the agent's turn.
        Descriptions include "This ends your turn." so LLMs can
        distinguish action tools from future query tools.

        Override to add scenario-specific tools or modify descriptions.
        """
        return [
            ToolSchema(
                name="move_to",
                description=(
                    "Navigate to a target position. The game handles "
                    "pathfinding and obstacle avoidance. This ends your turn."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "target_position": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "Target position as [x, y, z]",
                        }
                    },
                    "required": ["target_position"],
                },
            ),
            ToolSchema(
                name="collect",
                description=(
                    "Collect a nearby resource by name. Must be within "
                    "collection range. This ends your turn."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "target_name": {
                            "type": "string",
                            "description": "Name of the resource to collect",
                        }
                    },
                    "required": ["target_name"],
                },
            ),
            ToolSchema(
                name="craft_item",
                description=(
                    "Craft an item at a nearby crafting station. Must be "
                    "within range of the correct station type. Recipes: "
                    "torch (1 wood + 1 stone at workbench), "
                    "meal (2 berry at workbench), "
                    "shelter (3 wood + 2 stone at anvil). "
                    "This ends your turn."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "recipe": {
                            "type": "string",
                            "description": "Recipe name (e.g., 'torch', 'shelter', 'meal')",
                        }
                    },
                    "required": ["recipe"],
                },
            ),
            ToolSchema(
                name="explore",
                description=(
                    "Move toward the nearest unexplored area to discover "
                    "new resources. Use this when no resources are visible. "
                    "This ends your turn."
                ),
                parameters={"type": "object", "properties": {}},
            ),
            ToolSchema(
                name="idle",
                description="Do nothing this tick. This ends your turn.",
                parameters={"type": "object", "properties": {}},
            ),
        ]

    def fallback_decision(self, obs: Observation) -> Decision:
        """
        Make a sensible fallback decision from observation data.

        Used when the LLM fails to produce a valid tool call. Priority:

        1. Flee from nearby hazards (within 3.0 units)
        2. Move toward the closest resource
        3. Move toward the nearest exploration target
        4. Move in +X direction as a last resort

        Override to customize fallback behavior.
        """
        # Priority 1: Flee from nearby hazards
        if obs.nearby_hazards:
            closest = min(obs.nearby_hazards, key=lambda h: h.distance)
            if closest.distance < 3.0:
                hx, hy, hz = closest.position
                px, py, pz = obs.position
                dx, dz = px - hx, pz - hz
                dist = max((dx**2 + dz**2) ** 0.5, 0.1)
                flee_x = px + (dx / dist) * 5.0
                flee_z = pz + (dz / dist) * 5.0
                return Decision(
                    tool="move_to",
                    params={"target_position": [flee_x, py, flee_z]},
                    reasoning=f"Fleeing hazard {closest.name} at dist {closest.distance:.1f}",
                )

        # Priority 2: Move toward closest resource
        if obs.nearby_resources:
            closest = min(obs.nearby_resources, key=lambda r: r.distance)
            return Decision(
                tool="move_to",
                params={"target_position": list(closest.position)},
                reasoning=f"Moving toward {closest.name} at dist {closest.distance:.1f}",
            )

        # Priority 3: Move toward nearest exploration target
        if obs.exploration and obs.exploration.explore_targets:
            best = obs.exploration.explore_targets[0]
            return Decision(
                tool="move_to",
                params={"target_position": list(best.position)},
                reasoning=f"Exploring {best.direction}",
            )

        # Priority 4: Move in +X direction
        px, py, pz = obs.position
        return Decision(
            tool="move_to",
            params={"target_position": [px + 10.0, py, pz]},
            reasoning="No resources or exploration data, moving to explore",
        )
