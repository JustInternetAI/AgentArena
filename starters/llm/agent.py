"""
LLM-Powered Agent - Using Local Language Models

This agent uses a local LLM for decision making, giving it:
- Natural language reasoning
- Complex situation understanding
- Adaptive behavior
- Explanation of decisions

This is YOUR code - you can modify prompts, memory, and reasoning!
"""

from agent_arena_sdk import Observation, Decision, ToolSchema
from memory import SlidingWindowMemory
from llm_client import LLMClient
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


class Agent:
    """
    LLM-powered agent with memory and reasoning.

    Features:
    - Uses local LLM for decisions
    - Remembers past observations
    - Reads and adapts to objectives
    - Provides natural language reasoning
    """

    def __init__(self, model_path: str = "models/llama-2-7b/gguf/q4/model.gguf"):
        """
        Initialize LLM agent.

        Args:
            model_path: Path to GGUF model file
        """
        # Initialize memory
        self.memory = SlidingWindowMemory(capacity=20)

        # Initialize LLM client
        logger.info("Initializing LLM client...")
        self.llm = LLMClient(
            model_path=model_path, temperature=0.3, max_tokens=256, n_gpu_layers=-1  # Use GPU
        )

        # Load prompts
        prompts_dir = Path(__file__).parent / "prompts"
        with open(prompts_dir / "system.txt") as f:
            self.system_prompt = f.read()
        with open(prompts_dir / "decision.txt") as f:
            self.decision_template = f.read()

        # Chain-of-thought trace for debug viewer
        self.last_trace = None

        logger.info("LLM agent initialized")

    def decide(self, obs: Observation) -> Decision:
        """
        Make a decision using the LLM.

        Args:
            obs: Current observation

        Returns:
            Decision from LLM
        """
        # Store observation in memory
        self.memory.store(obs)

        # Build user prompt from observation
        prompt = self._build_prompt(obs)

        # Initialize trace
        trace = {
            "system_prompt": self.system_prompt,
            "user_prompt": prompt,
            "llm_raw_output": None,
            "tokens_used": 0,
            "finish_reason": None,
            "parse_method": None,  # "json", "fallback", "error"
            "decision": None,
        }

        # Generate LLM response (pass system prompt separately for chat formatting)
        try:
            response = self.llm.generate(prompt=prompt, system_prompt=self.system_prompt)

            trace["llm_raw_output"] = response.get("text", "")
            trace["tokens_used"] = response.get("tokens_used", 0)
            trace["finish_reason"] = response.get("finish_reason")

            # Parse response into Decision
            decision = self._parse_response(response, obs, trace)

            trace["decision"] = {
                "tool": decision.tool,
                "params": decision.params,
                "reasoning": decision.reasoning,
            }
            self.last_trace = trace
            return decision

        except Exception as e:
            logger.error(f"Error getting LLM decision: {e}")
            trace["parse_method"] = "error"
            trace["decision"] = {"tool": "idle", "params": {}, "reasoning": f"LLM error: {str(e)}"}
            self.last_trace = trace
            return Decision.idle(f"LLM error: {str(e)}")

    def _build_prompt(self, obs: Observation) -> str:
        """
        Build a prompt from the observation.

        Args:
            obs: Current observation

        Returns:
            Formatted prompt string
        """
        # Format resources
        if obs.nearby_resources:
            resources_lines = [
                f"{r.name} ({r.type}) dist={r.distance:.1f} pos={list(r.position)}" for r in obs.nearby_resources[:5]
            ]
            resources_summary = "; ".join(resources_lines)
        else:
            resources_summary = "None"

        # Format hazards
        if obs.nearby_hazards:
            hazards_lines = [
                f"{h.name} ({h.type}) dist={h.distance:.1f} pos={list(h.position)}" for h in obs.nearby_hazards[:5]
            ]
            hazards_summary = "; ".join(hazards_lines)
        else:
            hazards_summary = "None"

        # Format inventory (check custom dict for simple inventory from crafting system)
        raw_inventory = obs.custom.get("inventory", {}) if obs.custom else {}
        if raw_inventory:
            inventory_summary = ", ".join(f"{k}: {v}" for k, v in raw_inventory.items())
        elif obs.inventory:
            inventory_summary = ", ".join(f"{item.name} x{item.quantity}" for item in obs.inventory)
        else:
            inventory_summary = "Empty"

        # Format stations
        if obs.nearby_stations:
            stations_lines = [
                f"{s.name} ({s.type}) dist={s.distance:.1f} pos={list(s.position)}"
                for s in obs.nearby_stations[:5]
            ]
            stations_summary = "; ".join(stations_lines)
        else:
            stations_summary = "None"

        # Format exploration data with concrete positions
        exploration_pct = 0.0
        explore_targets_summary = "None"
        if obs.exploration:
            exploration_pct = obs.exploration.exploration_percentage
            if obs.exploration.explore_targets:
                target_lines = [
                    f"{t.direction} pos={list(t.position)} ({t.distance:.1f}u away)"
                    for t in obs.exploration.explore_targets[:4]
                ]
                explore_targets_summary = "; ".join(target_lines)

        # Hint when nothing is visible — point to a concrete position
        exploration_hint = ""
        if not obs.nearby_resources:
            if obs.exploration and obs.exploration.explore_targets:
                best = obs.exploration.explore_targets[0]
                pos = list(best.position)
                exploration_hint = (
                    f"No resources visible! move_to an exploration target to find them. "
                    f"Nearest: {pos}"
                )
            else:
                exploration_hint = "No resources visible! move_to an unexplored area to find them."

        # Fill template
        prompt = self.decision_template.format(
            tick=obs.tick,
            position=obs.position,
            health=obs.health,
            energy=obs.energy,
            perception_radius=getattr(obs, "perception_radius", 10.0),
            resources_summary=resources_summary,
            hazards_summary=hazards_summary,
            inventory_summary=inventory_summary,
            stations_summary=stations_summary,
            exploration_percentage=f"{exploration_pct:.1f}",
            explore_targets=explore_targets_summary,
            exploration_hint=exploration_hint,
        )

        return prompt

    def _get_tool_schemas(self) -> list[ToolSchema]:
        """
        Get available tool schemas.

        Returns:
            List of tool schemas
        """
        return [
            ToolSchema(
                name="move_to",
                description="Navigate to a target position",
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
                description="Collect a nearby resource",
                parameters={
                    "type": "object",
                    "properties": {
                        "target_name": {"type": "string", "description": "Name of resource to collect"}
                    },
                    "required": ["target_name"],
                },
            ),
            ToolSchema(
                name="idle", description="Do nothing this tick", parameters={"type": "object", "properties": {}}
            ),
            ToolSchema(
                name="craft_item",
                description="Craft an item at a nearby crafting station. Must be within range of the correct station type.",
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
        ]

    # Valid tool names the agent can use
    VALID_TOOLS = {"move_to", "collect", "idle", "craft_item"}

    # Minimum safe distance from hazards
    HAZARD_SAFE_DISTANCE = 3.0

    def _is_near_hazard(self, target: list, obs: Observation) -> bool:
        """Check if a target position is too close to any known hazard."""
        if not obs.nearby_hazards:
            return False
        tx, tz = target[0], target[2] if len(target) > 2 else 0
        for h in obs.nearby_hazards:
            hx, hz = h.position[0], h.position[2]
            dist = ((tx - hx) ** 2 + (tz - hz) ** 2) ** 0.5
            if dist < self.HAZARD_SAFE_DISTANCE:
                return True
        return False

    def _extract_first_json_object(self, text: str) -> dict | None:
        """Extract the first complete JSON object from text using brace matching."""
        start = text.find("{")
        if start == -1:
            return None

        depth = 0
        in_string = False
        escape_next = False

        for i in range(start, len(text)):
            c = text[i]
            if escape_next:
                escape_next = False
                continue
            if c == "\\":
                escape_next = True
                continue
            if c == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        return None
        return None

    def _parse_response(self, response: dict, obs: Observation, trace: dict | None = None) -> Decision:
        """
        Parse LLM response into a Decision.

        Handles common LLM failure modes:
        - Multiple JSON objects (takes first)
        - JSON arrays (takes first element)
        - Invalid tool names (falls back to observation-based decision)
        - Truncated JSON (falls back)
        """
        # Check for tool call from backend parser
        if response.get("tool_call"):
            tool_call = response["tool_call"]
            tool = tool_call.get("tool", "idle")
            if tool in self.VALID_TOOLS:
                if trace:
                    trace["parse_method"] = "tool_call"
                return Decision(
                    tool=tool,
                    params=tool_call.get("params", {}),
                    reasoning=response.get("text", "LLM decision"),
                )

        text = response.get("text", "")
        if text:
            # Extract first complete JSON object (handles multiple objects, truncation)
            data = self._extract_first_json_object(text)

            if data and isinstance(data, dict):
                tool = data.get("tool", "")
                reasoning = data.get("reasoning", "LLM decision")

                # Validate tool name — LLM often outputs placeholder like "tool_name"
                if tool in self.VALID_TOOLS:
                    params = data.get("params", {})

                    # Validate move_to has proper target_position and isn't toward a hazard
                    if tool == "move_to":
                        target = params.get("target_position")
                        if isinstance(target, list) and len(target) >= 2:
                            # Safety: reject if target is near a known hazard
                            if self._is_near_hazard(target, obs):
                                logger.debug("LLM move_to target is near a hazard, using fallback")
                                if trace:
                                    trace["parse_method"] = "json_rejected_hazard"
                                    trace["parsed_json"] = data
                                # Fall through to fallback
                            else:
                                if trace:
                                    trace["parse_method"] = "json"
                                    trace["parsed_json"] = data
                                return Decision(tool="move_to", params=params, reasoning=reasoning)

                    elif tool == "collect":
                        target_name = params.get("target_name")
                        if isinstance(target_name, str) and target_name:
                            if trace:
                                trace["parse_method"] = "json"
                                trace["parsed_json"] = data
                            return Decision(tool="collect", params=params, reasoning=reasoning)

                    elif tool == "craft_item":
                        recipe = params.get("recipe")
                        if isinstance(recipe, str) and recipe:
                            if trace:
                                trace["parse_method"] = "json"
                                trace["parsed_json"] = data
                            return Decision(tool="craft_item", params=params, reasoning=reasoning)

                    elif tool == "idle":
                        if trace:
                            trace["parse_method"] = "json"
                            trace["parsed_json"] = data
                        return Decision(tool="idle", params={}, reasoning=reasoning)

                logger.debug(f"LLM returned invalid tool '{tool}', using observation fallback")

        # Observation-based fallback: always make a useful decision from the data
        if trace:
            trace["parse_method"] = "fallback"
        return self._fallback_decision(obs)

    def _fallback_decision(self, obs: Observation) -> Decision:
        """Make a sensible decision based on observation data when LLM output is unusable."""
        # Priority 1: Flee from nearby hazards
        if obs.nearby_hazards:
            closest_hazard = min(obs.nearby_hazards, key=lambda h: h.distance)
            if closest_hazard.distance < 3.0:
                # Move away from hazard
                hx, hy, hz = closest_hazard.position
                px, py, pz = obs.position
                dx, dz = px - hx, pz - hz
                dist = max((dx**2 + dz**2) ** 0.5, 0.1)
                flee_x = px + (dx / dist) * 5.0
                flee_z = pz + (dz / dist) * 5.0
                return Decision(
                    tool="move_to",
                    params={"target_position": [flee_x, py, flee_z]},
                    reasoning=f"Fleeing hazard {closest_hazard.name} at dist {closest_hazard.distance:.1f}",
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
                reasoning=f"No resources visible, exploring {best.direction}",
            )

        # Priority 4: Move to a default position when no exploration data
        px, py, pz = obs.position
        return Decision(
            tool="move_to",
            params={"target_position": [px + 10.0, py, pz]},
            reasoning="No resources or exploration data, moving to explore",
        )
