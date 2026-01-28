"""
LLM-Powered Foraging Agent - Advanced Example.

This demonstrates the LLMAgentBehavior interface which:
- Integrates with LLM backends (Anthropic, OpenAI, Ollama)
- Uses natural language reasoning for decisions
- Supports custom prompts and response parsing
- Perfect for learning LLM-based agent development

Requirements:
    pip install anthropic  # or openai, or ollama

Environment:
    export ANTHROPIC_API_KEY="your-key"  # or OPENAI_API_KEY
"""

import json
import re

from agent_runtime import AgentDecision, LLMAgentBehavior
from agent_runtime.memory import SlidingWindowMemory


class LLMForager(LLMAgentBehavior):
    """
    LLM-powered foraging agent.

    This agent uses a language model to reason about the environment
    and make decisions. It demonstrates:
    - Building prompts from observation data
    - Parsing structured responses from LLM
    - Memory integration for context
    - Graceful fallback handling

    Usage:
        from user_agents.examples.llm_forager import LLMForager

        agent = LLMForager(backend="anthropic", model="claude-3-haiku-20240307")
        # or
        agent = LLMForager(backend="openai", model="gpt-4o-mini")
        # or
        agent = LLMForager(backend="ollama", model="llama3.2")
    """

    def __init__(
        self,
        backend: str = "anthropic",
        model: str = "claude-3-haiku-20240307",
        memory_capacity: int = 10,
    ):
        """
        Initialize the LLM forager.

        Args:
            backend: LLM provider ("anthropic", "openai", "ollama")
            model: Model identifier for the backend
            memory_capacity: Number of observations to keep in memory
        """
        super().__init__(backend=backend, model=model)
        self.memory = SlidingWindowMemory(capacity=memory_capacity)
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Build the system prompt for the LLM."""
        return """You are an intelligent foraging agent operating in a game environment.

GOAL: Collect all resources while avoiding hazards.

PRIORITIES:
1. SAFETY FIRST - Always avoid hazards (stay at least 3 units away)
2. EFFICIENCY - Collect nearest resources first
3. AWARENESS - Remember where you've been

AVAILABLE TOOLS:
- move_to: Move toward a position. Params: {"target_position": [x, y, z]}
- collect: Collect a nearby resource (must be within 2 units). Params: {"resource_id": "name"}
- idle: Do nothing this tick. Params: {}

RESPONSE FORMAT:
Always respond in exactly this format:
REASONING: [Your analysis in 1-2 sentences]
TOOL: [tool name]
PARAMS: [JSON parameters]

Example:
REASONING: Apple is close at 1.5 units and there are no hazards nearby.
TOOL: collect
PARAMS: {"resource_id": "Apple_001"}"""

    def on_episode_start(self) -> None:
        """Called when a new episode begins - clear memory."""
        self.memory.clear()

    def decide(self, observation, tools) -> AgentDecision:
        """
        Decide what action to take using the LLM.

        Args:
            observation: Current observation from Godot
            tools: List of available tool schemas

        Returns:
            AgentDecision with tool, params, and reasoning
        """
        # Store observation in memory
        self.memory.store(observation)

        # Build context for LLM
        context = self._build_context(observation)

        try:
            # Get LLM response
            response = self.complete(context, temperature=0.3)

            # Parse response into decision
            decision = self._parse_response(response, tools)
            return decision

        except Exception as e:
            # Fallback to safe behavior on error
            print(f"LLM error: {e}, using fallback")
            return self._fallback_decision(observation)

    def _build_context(self, observation) -> str:
        """Build the context prompt from the current observation."""
        # Format resources
        resources = []
        for r in sorted(observation.nearby_resources, key=lambda x: x.distance)[:5]:
            resources.append(f"- {r.name} ({r.type}): {r.distance:.1f} units away")

        # Format hazards
        hazards = []
        for h in sorted(observation.nearby_hazards, key=lambda x: x.distance)[:3]:
            danger = "DANGER!" if h.distance < 3 else "warning"
            hazards.append(f"- [{danger}] {h.name}: {h.distance:.1f} units, {h.damage} damage")

        # Format memory
        recent = self.memory.retrieve()[-3:]
        memory_summary = f"Observations in memory: {len(self.memory.retrieve())}"
        if recent:
            positions = [f"({o.position[0]:.0f}, {o.position[2]:.0f})" for o in recent]
            memory_summary += f"\nRecent positions: {', '.join(positions)}"

        return f"""
## CURRENT STATE
- Position: ({observation.position[0]:.1f}, {observation.position[1]:.1f}, {observation.position[2]:.1f})
- Health: {observation.health}/100
- Inventory: {len(observation.inventory)} items

## NEARBY RESOURCES ({len(observation.nearby_resources)} visible)
{chr(10).join(resources) or "None visible"}

## HAZARDS ({len(observation.nearby_hazards)} detected)
{chr(10).join(hazards) or "None detected"}

## MEMORY
{memory_summary}

What should I do? Respond in the required format."""

    def _parse_response(self, response: str, tools) -> AgentDecision:
        """
        Parse the LLM response into an AgentDecision.

        Args:
            response: Raw text response from LLM
            tools: Available tool schemas for validation

        Returns:
            AgentDecision extracted from the response
        """
        reasoning = ""
        tool_name = "idle"
        params = {}

        # Extract reasoning
        if "REASONING:" in response:
            reasoning_match = re.search(r"REASONING:\s*(.+?)(?=TOOL:|$)", response, re.DOTALL)
            if reasoning_match:
                reasoning = reasoning_match.group(1).strip()[:200]

        # Extract tool name
        tool_match = re.search(r"TOOL:\s*(\w+)", response, re.IGNORECASE)
        if tool_match:
            tool_name = tool_match.group(1).lower()

        # Extract parameters
        params_match = re.search(r"PARAMS:\s*(\{[^}]+\})", response, re.DOTALL)
        if params_match:
            try:
                params = json.loads(params_match.group(1))
            except json.JSONDecodeError:
                pass

        # Validate tool exists
        valid_tools = {t.name.lower() for t in tools}
        if tool_name not in valid_tools:
            print(f"Invalid tool '{tool_name}', defaulting to idle")
            tool_name = "idle"
            params = {}
            reasoning = f"Invalid tool from LLM: {tool_name}"

        return AgentDecision(
            tool=tool_name,
            params=params,
            reasoning=reasoning,
        )

    def _fallback_decision(self, observation) -> AgentDecision:
        """
        Make a safe fallback decision when LLM fails.

        Uses simple rule-based logic as backup.
        """
        # Escape hazards
        for hazard in observation.nearby_hazards:
            if hazard.distance < 3.0:
                escape = self._calculate_escape(observation.position, hazard.position)
                return AgentDecision(
                    tool="move_to",
                    params={"target_position": escape},
                    reasoning="Fallback: escaping hazard",
                )

        # Collect nearby resources
        for resource in observation.nearby_resources:
            if resource.distance < 2.0:
                return AgentDecision(
                    tool="collect",
                    params={"resource_id": resource.name},
                    reasoning="Fallback: collecting nearby resource",
                )

        # Move to nearest resource
        if observation.nearby_resources:
            nearest = min(observation.nearby_resources, key=lambda r: r.distance)
            return AgentDecision(
                tool="move_to",
                params={"target_position": list(nearest.position)},
                reasoning="Fallback: moving to resource",
            )

        return AgentDecision.idle(reasoning="Fallback: no action needed")

    def _calculate_escape(self, agent_pos, hazard_pos):
        """Calculate a safe position away from a hazard."""
        dx = agent_pos[0] - hazard_pos[0]
        dz = agent_pos[2] - hazard_pos[2]
        length = (dx**2 + dz**2) ** 0.5
        if length > 0:
            dx = (dx / length) * 5.0
            dz = (dz / length) * 5.0
        else:
            dx, dz = 5.0, 0.0
        return [agent_pos[0] + dx, agent_pos[1], agent_pos[2] + dz]
