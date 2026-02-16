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
            model_path=model_path, temperature=0.7, max_tokens=512, n_gpu_layers=-1  # Use GPU
        )

        # Load prompts
        prompts_dir = Path(__file__).parent / "prompts"
        with open(prompts_dir / "system.txt") as f:
            self.system_prompt = f.read()
        with open(prompts_dir / "decision.txt") as f:
            self.decision_template = f.read()

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

        # Build prompt from observation
        prompt = self._build_prompt(obs)

        # Get available tools
        tools = self._get_tool_schemas()

        # Generate LLM response
        try:
            response = self.llm.generate(prompt=prompt, tools=tools)

            # Parse response into Decision
            decision = self._parse_response(response)

            return decision

        except Exception as e:
            logger.error(f"Error getting LLM decision: {e}")
            return Decision.idle(f"LLM error: {str(e)}")

    def _build_prompt(self, obs: Observation) -> str:
        """
        Build a prompt from the observation.

        Args:
            obs: Current observation

        Returns:
            Formatted prompt string
        """
        # Format objective
        if obs.objective:
            obj_desc = obs.objective.description
            progress_lines = []
            for metric, definition in obs.objective.success_metrics.items():
                current = obs.current_progress.get(metric, 0)
                target = definition.target
                progress_lines.append(f"- {metric}: {current:.1f}/{target:.1f}")
            progress_summary = "\n".join(progress_lines) if progress_lines else "No metrics"
        else:
            obj_desc = "No objective defined"
            progress_summary = "No progress tracked"

        # Format resources
        if obs.nearby_resources:
            resources_lines = [
                f"- {r.name} ({r.type}) at distance {r.distance:.1f}m" for r in obs.nearby_resources[:5]
            ]
            resources_summary = "\n".join(resources_lines)
        else:
            resources_summary = "No resources visible"

        # Format hazards
        if obs.nearby_hazards:
            hazards_lines = [
                f"- {h.name} ({h.type}) at distance {h.distance:.1f}m, damage: {h.damage}"
                for h in obs.nearby_hazards[:5]
            ]
            hazards_summary = "\n".join(hazards_lines)
        else:
            hazards_summary = "No hazards visible"

        # Format inventory
        if obs.inventory:
            inventory_lines = [f"- {item.name} x{item.quantity}" for item in obs.inventory]
            inventory_summary = "\n".join(inventory_lines)
        else:
            inventory_summary = "Empty"

        # Get memory summary
        memory_summary = self.memory.summarize() if self.memory.count_observations() > 0 else "No memory yet"

        # Fill template
        prompt = self.decision_template.format(
            tick=obs.tick,
            position=obs.position,
            health=obs.health,
            energy=obs.energy,
            scenario_name=obs.scenario_name or "Unknown",
            objective_description=obj_desc,
            progress_summary=progress_summary,
            resources_summary=resources_summary,
            hazards_summary=hazards_summary,
            inventory_summary=inventory_summary,
            memory_summary=memory_summary,
        )

        # Combine system prompt + decision prompt
        full_prompt = f"{self.system_prompt}\n\n{prompt}"

        return full_prompt

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
        ]

    def _parse_response(self, response: dict) -> Decision:
        """
        Parse LLM response into a Decision.

        Args:
            response: Response from LLM client

        Returns:
            Decision object
        """
        # Check for tool call
        if response.get("tool_call"):
            tool_call = response["tool_call"]
            return Decision(
                tool=tool_call["tool"],
                params=tool_call.get("params", {}),
                reasoning=response.get("text", "LLM decision"),
            )

        # Try to parse text as JSON
        text = response.get("text", "")
        if text:
            try:
                # Look for JSON block
                if "```json" in text:
                    start = text.find("```json") + 7
                    end = text.find("```", start)
                    json_str = text[start:end].strip()
                elif "{" in text and "}" in text:
                    start = text.find("{")
                    end = text.rfind("}") + 1
                    json_str = text[start:end]
                else:
                    json_str = text

                data = json.loads(json_str)

                return Decision(
                    tool=data.get("tool", "idle"),
                    params=data.get("params", {}),
                    reasoning=data.get("reasoning", text),
                )

            except Exception as e:
                logger.warning(f"Could not parse LLM response as JSON: {e}")

        # Fallback: idle
        return Decision.idle("Could not parse LLM response")
