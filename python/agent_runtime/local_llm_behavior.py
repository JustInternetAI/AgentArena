"""
LocalLLMBehavior - Bridges local LLM backends to AgentBehavior API.

This module provides a behavior class that wraps local LLM backends
(LlamaCppBackend, VLLMBackend) and implements the AgentBehavior interface,
allowing local LLMs to power agents via the IPC server.
"""

import json
import logging
from typing import TYPE_CHECKING

from backends.base import BaseBackend, GenerationResult

from .behavior import AgentBehavior
from .memory import SlidingWindowMemory
from .schemas import AgentDecision, Observation, ToolSchema

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class LocalLLMBehavior(AgentBehavior):
    """
    Agent behavior powered by local LLM backends.

    This class wraps local backends (LlamaCppBackend, VLLMBackend) and implements
    the AgentBehavior interface. It handles:
    - Prompt construction with system prompts and observations
    - Memory management with sliding window
    - Tool calling via the backend's generate_with_tools() method
    - Parsing LLM responses into AgentDecision objects
    - Graceful error handling (returns idle on failures)

    Example:
        from backends.llama_cpp_backend import LlamaCppBackend
        from backends.base import BackendConfig

        config = BackendConfig(model_path="path/to/model.gguf", n_gpu_layers=-1)
        backend = LlamaCppBackend(config)

        behavior = LocalLLMBehavior(
            backend=backend,
            system_prompt="You are a foraging agent. Collect resources and avoid hazards.",
            memory_capacity=10
        )

        # Use with IPC server
        server = create_server(behaviors={"forager_001": behavior})
    """

    def __init__(
        self,
        backend: BaseBackend,
        system_prompt: str = "You are an autonomous agent in a simulation environment.",
        memory_capacity: int = 10,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ):
        """
        Initialize the local LLM behavior.

        Args:
            backend: Local LLM backend (LlamaCppBackend or VLLMBackend)
            system_prompt: System prompt describing the agent's role and task
            memory_capacity: Number of recent observations to keep in memory
            temperature: Optional temperature override for generation
            max_tokens: Optional max tokens override for generation
        """
        self.backend = backend
        self.system_prompt = system_prompt
        self.memory = SlidingWindowMemory(capacity=memory_capacity)
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Validate backend is available
        if not self.backend.is_available():
            raise RuntimeError(f"Backend {self.backend.__class__.__name__} is not available")

        logger.info(
            f"Initialized LocalLLMBehavior with {self.backend.__class__.__name__} "
            f"(memory_capacity={memory_capacity})"
        )

    def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
        """
        Decide what action to take given the current observation.

        Constructs a prompt from the system prompt, memory, and current observation,
        then calls the backend's generate_with_tools() method to get a decision.

        Args:
            observation: Current tick's observation from Godot
            tools: List of available tools with their schemas

        Returns:
            AgentDecision specifying which tool to call and with what parameters
        """
        try:
            # Store observation in memory
            self.memory.store(observation)

            # Build prompt from system prompt, memory, and observation
            prompt = self._build_prompt(observation, tools)

            # Convert tools to dict format for backend
            tool_dicts = [self._tool_schema_to_dict(tool) for tool in tools]

            # Generate response using backend
            import time
            start_time = time.time()
            logger.debug(f"Generating decision for agent {observation.agent_id}")
            result = self.backend.generate_with_tools(
                prompt=prompt, tools=tool_dicts, temperature=self.temperature
            )
            elapsed_ms = (time.time() - start_time) * 1000

            # Parse response into AgentDecision
            decision = self._parse_decision(result, observation)

            logger.info(
                f"Agent {observation.agent_id} decided: {decision.tool} - {decision.reasoning} "
                f"(LLM took {elapsed_ms:.0f}ms, {result.tokens_used} tokens)"
            )

            return decision

        except Exception as e:
            logger.error(f"Error in LocalLLMBehavior.decide(): {e}", exc_info=True)
            return AgentDecision.idle(reasoning=f"Error: {str(e)}")

    def _build_prompt(self, observation: Observation, tools: list[ToolSchema]) -> str:
        """
        Build the prompt for LLM generation.

        Includes system prompt, memory context, current observation, and available tools.

        Args:
            observation: Current observation
            tools: Available tools

        Returns:
            Formatted prompt string
        """
        # Start with system prompt
        parts = [self.system_prompt, ""]

        # Add memory context if available
        memory_items = self.memory.retrieve(limit=5)
        if memory_items and len(memory_items) > 1:  # Don't include if only current observation
            parts.append("Recent observations:")
            # Memory items are returned most recent first, so reverse and skip last (current)
            for i, obs in enumerate(reversed(memory_items[1:]), 1):
                parts.append(f"  {i}. Tick {obs.tick}: Position {obs.position}")
                if obs.nearby_resources:
                    parts.append(f"     Resources nearby: {len(obs.nearby_resources)}")
                if obs.nearby_hazards:
                    parts.append(f"     Hazards nearby: {len(obs.nearby_hazards)}")
            parts.append("")

        # Add current observation
        parts.append("Current observation:")
        parts.append(f"  Tick: {observation.tick}")
        parts.append(f"  Position: {observation.position}")
        parts.append(f"  Health: {observation.health}")
        parts.append(f"  Energy: {observation.energy}")

        if observation.nearby_resources:
            parts.append(f"  Nearby resources ({len(observation.nearby_resources)}):")
            for r in observation.nearby_resources[:5]:  # Limit to 5 for brevity
                parts.append(
                    f"    - {r.name} ({r.type}) at distance {r.distance:.1f}, position {r.position}"
                )

        if observation.nearby_hazards:
            parts.append(f"  Nearby hazards ({len(observation.nearby_hazards)}):")
            for h in observation.nearby_hazards[:5]:  # Limit to 5 for brevity
                parts.append(
                    f"    - {h.name} ({h.type}) at distance {h.distance:.1f}, "
                    f"damage {h.damage}, position {h.position}"
                )

        if observation.inventory:
            parts.append(f"  Inventory ({len(observation.inventory)} items):")
            for item in observation.inventory:
                parts.append(f"    - {item.name} (x{item.quantity})")
        else:
            parts.append("  Inventory: empty")

        parts.append("")
        parts.append("Choose an action based on the observation above.")

        return "\n".join(parts)

    def _tool_schema_to_dict(self, tool: ToolSchema) -> dict:
        """
        Convert ToolSchema to dict format for backend.

        Args:
            tool: ToolSchema instance

        Returns:
            Dictionary with name, description, and parameters
        """
        return {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
        }

    def _parse_decision(self, result: GenerationResult, observation: Observation) -> AgentDecision:
        """
        Parse backend generation result into AgentDecision.

        Handles various response formats:
        - Native tool calls from VLLMBackend (in metadata)
        - JSON tool calls from LlamaCppBackend (in text)
        - Fallback to idle if parsing fails

        Args:
            result: Generation result from backend
            observation: Current observation (for context)

        Returns:
            AgentDecision instance
        """
        # Check if backend returned a native tool call (e.g., vLLM)
        if "tool_call" in result.metadata:
            tool_call = result.metadata["tool_call"]
            return AgentDecision(
                tool=tool_call["name"],
                params=tool_call["arguments"],
                reasoning=result.text or "LLM tool call",
            )

        # Check if backend parsed a tool call from text (e.g., llama.cpp)
        if "parsed_tool_call" in result.metadata:
            parsed = result.metadata["parsed_tool_call"]
            return AgentDecision(
                tool=parsed.get("tool", "idle"),
                params=parsed.get("params", {}),
                reasoning=parsed.get("reasoning", "LLM decision"),
            )

        # Try to parse JSON from result text
        try:
            text = result.text.strip()

            # Remove markdown code blocks if present
            if text.startswith("```json"):
                text = text[7:]
            elif text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]

            parsed = json.loads(text.strip())

            # Extract fields
            tool = parsed.get("tool") or parsed.get("action") or "idle"
            params = parsed.get("params") or parsed.get("parameters") or {}
            reasoning = parsed.get("reasoning") or parsed.get("thought") or "LLM decision"

            return AgentDecision(tool=tool, params=params, reasoning=reasoning)

        except (json.JSONDecodeError, AttributeError) as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Response text: {result.text}")

            # Fallback: return idle
            return AgentDecision.idle(reasoning="Failed to parse LLM response")

    def on_tool_result(self, tool: str, result: dict) -> None:
        """
        Called after a tool execution completes.

        Can be overridden to update memory or adjust strategy based on tool results.

        Args:
            tool: Name of the tool that was executed
            result: Result dictionary from the tool
        """
        logger.debug(f"Tool '{tool}' executed with result: {result}")

    def on_episode_start(self) -> None:
        """
        Called when a new episode begins.

        Clears memory to start fresh.
        """
        logger.info("Episode started, clearing memory")
        self.memory.clear()

    def on_episode_end(self, success: bool, metrics: dict | None = None) -> None:
        """
        Called when an episode ends.

        Args:
            success: Whether the episode goal was achieved
            metrics: Optional metrics from the scenario
        """
        logger.info(
            f"Episode ended: success={success}, "
            f"observations_stored={len(self.memory)}"
        )
        if metrics:
            logger.info(f"Episode metrics: {metrics}")


def create_local_llm_behavior(
    backend: BaseBackend,
    system_prompt: str | None = None,
    memory_capacity: int = 10,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> LocalLLMBehavior:
    """
    Factory function to create a LocalLLMBehavior instance.

    Args:
        backend: Local LLM backend (LlamaCppBackend or VLLMBackend)
        system_prompt: System prompt describing the agent's role and task.
                      If None, uses a default foraging prompt.
        memory_capacity: Number of recent observations to keep in memory
        temperature: Optional temperature override for generation
        max_tokens: Optional max tokens override for generation

    Returns:
        LocalLLMBehavior instance

    Example:
        from backends.llama_cpp_backend import LlamaCppBackend
        from backends.base import BackendConfig

        config = BackendConfig(model_path="path/to/model.gguf", n_gpu_layers=-1)
        backend = LlamaCppBackend(config)

        behavior = create_local_llm_behavior(
            backend=backend,
            system_prompt="You are a foraging agent. Collect apples and avoid fire hazards.",
            memory_capacity=10
        )
    """
    if system_prompt is None:
        # Default foraging prompt
        system_prompt = """You are an autonomous foraging agent in a simulation environment.

Your goal is to:
1. Collect resources (like apples) to increase your score
2. Avoid hazards (like fire) that can damage you
3. Manage your health and energy efficiently

When you receive an observation, analyze the situation and choose the best action.
Prioritize safety (avoid hazards) over collecting resources."""

    return LocalLLMBehavior(
        backend=backend,
        system_prompt=system_prompt,
        memory_capacity=memory_capacity,
        temperature=temperature,
        max_tokens=max_tokens,
    )
