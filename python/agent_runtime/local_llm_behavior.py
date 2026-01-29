"""
Local LLM agent behavior for GPU-accelerated backends.

This module provides LocalLLMBehavior, a Tier 2 behavior that bridges
local LLM backends (like LlamaCppBackend) to the AgentBehavior interface.

Unlike LLMAgentBehavior which uses external API services, LocalLLMBehavior
uses in-process GPU-accelerated inference via BaseBackend implementations.
"""

import logging
from typing import TYPE_CHECKING

from .behavior import AgentBehavior
from .schemas import AgentDecision, Observation, ToolSchema

if TYPE_CHECKING:
    from backends.base import BaseBackend

logger = logging.getLogger(__name__)


class LocalLLMBehavior(AgentBehavior):
    """
    Agent behavior using local GPU-accelerated LLM backend.

    This is a Tier 2 behavior that provides LLM-based decision making
    using local models (llama.cpp, etc.) rather than external APIs.

    Example:
        from backends import BackendConfig, LlamaCppBackend
        from agent_runtime import LocalLLMBehavior

        # Create backend
        config = BackendConfig(
            model_path="models/llama-2-7b.gguf",
            n_gpu_layers=-1
        )
        backend = LlamaCppBackend(config)

        # Create behavior
        behavior = LocalLLMBehavior(
            backend=backend,
            system_prompt="You are a foraging agent. Collect resources efficiently."
        )

        # Register with arena
        arena.register_behavior("agent_001", behavior)
    """

    def __init__(
        self,
        backend: "BaseBackend",
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 256,
    ):
        """
        Initialize the local LLM behavior.

        Args:
            backend: A BaseBackend implementation (e.g., LlamaCppBackend)
            system_prompt: System prompt providing agent context and goals
            temperature: LLM temperature for response randomness (0-1)
            max_tokens: Maximum tokens to generate per decision
        """
        self.backend = backend
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Validate backend is ready
        if not backend.is_available():
            raise RuntimeError("Backend is not available - model may not be loaded")

        logger.info(f"LocalLLMBehavior initialized with backend: {type(backend).__name__}")

    def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
        """
        Decide what action to take using the local LLM.

        Args:
            observation: Current tick's observation from Godot
            tools: List of available tools with their schemas

        Returns:
            AgentDecision specifying which tool to call and with what parameters
        """
        try:
            # Build the prompt from observation and tools
            prompt = self._build_prompt(observation, tools)
            logger.debug(f"Prompt length: {len(prompt)} chars (~{len(prompt)//4} tokens)")

            # Convert ToolSchema list to dict format for backend
            tool_dicts = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                }
                for tool in tools
            ]

            # Generate response using backend
            result = self.backend.generate_with_tools(
                prompt=prompt,
                tools=tool_dicts,
                temperature=self.temperature,
            )

            # Check for generation errors
            if result.finish_reason == "error":
                error_msg = result.metadata.get("error", "Unknown error")
                logger.error(f"LLM generation error: {error_msg}")
                return AgentDecision.idle(reasoning=f"LLM error: {error_msg}")

            # Debug: log token usage and raw response
            logger.debug(f"Tokens used: {result.tokens_used}")
            logger.debug(f"Raw LLM response: {result.text[:500] if result.text else '(empty)'}")

            # Try to parse from metadata first (pre-parsed by backend)
            if "parsed_tool_call" in result.metadata:
                parsed = result.metadata["parsed_tool_call"]
                return AgentDecision(
                    tool=parsed.get("tool", "idle"),
                    params=parsed.get("params", {}),
                    reasoning=parsed.get("reasoning", ""),
                )

            # Otherwise parse the raw text response
            try:
                return AgentDecision.from_llm_response(result.text)
            except ValueError as e:
                logger.warning(f"Failed to parse LLM response: {e}")
                logger.debug(f"Raw response: {result.text}")
                return AgentDecision.idle(reasoning=f"Parse error: {e}")

        except Exception as e:
            logger.error(f"Error in LocalLLMBehavior.decide(): {e}", exc_info=True)
            return AgentDecision.idle(reasoning=f"Error: {e}")

    def _build_prompt(self, observation: Observation, tools: list[ToolSchema]) -> str:
        """
        Build the LLM prompt from observation and tools.

        Args:
            observation: Current observation from Godot
            tools: Available tool schemas

        Returns:
            Formatted prompt string
        """
        sections = []

        # Add system prompt if provided
        if self.system_prompt:
            sections.append(self.system_prompt)
            sections.append("")

        # Current state
        sections.append("## Current Situation")
        sections.append(f"Position: {observation.position}")
        sections.append(f"Health: {observation.health}")
        sections.append(f"Energy: {observation.energy}")
        sections.append(f"Tick: {observation.tick}")

        # Nearby resources
        if observation.nearby_resources:
            sections.append("\n## Nearby Resources")
            for resource in observation.nearby_resources:
                sections.append(
                    f"- {resource.name} ({resource.type}) at distance {resource.distance:.1f}"
                )
        else:
            sections.append("\n## Nearby Resources\nNone visible")

        # Nearby hazards
        if observation.nearby_hazards:
            sections.append("\n## Nearby Hazards")
            for hazard in observation.nearby_hazards:
                damage_str = f", damage: {hazard.damage}" if hazard.damage > 0 else ""
                sections.append(
                    f"- {hazard.name} ({hazard.type}) at distance {hazard.distance:.1f}{damage_str}"
                )
        else:
            sections.append("\n## Nearby Hazards\nNone visible")

        # Inventory
        if observation.inventory:
            sections.append("\n## Inventory")
            for item in observation.inventory:
                sections.append(f"- {item.name} x{item.quantity}")
        else:
            sections.append("\n## Inventory\nEmpty")

        # Add instruction for response format
        sections.append("\n## Instructions")
        sections.append("Based on the current situation, decide what action to take.")
        sections.append("Consider your goals, nearby resources, and any hazards.")

        return "\n".join(sections)

    def on_episode_start(self) -> None:
        """Called when a new episode begins."""
        logger.debug("LocalLLMBehavior: Episode started")

    def on_episode_end(self, success: bool, metrics: dict | None = None) -> None:
        """Called when an episode ends."""
        logger.debug(f"LocalLLMBehavior: Episode ended, success={success}")

    def on_tool_result(self, tool: str, result: dict) -> None:
        """Called after a tool execution completes."""
        logger.debug(f"LocalLLMBehavior: Tool {tool} returned {result}")


def create_local_llm_behavior(
    model_path: str,
    system_prompt: str = "",
    n_gpu_layers: int = -1,
    temperature: float = 0.7,
    max_tokens: int = 256,
) -> LocalLLMBehavior:
    """
    Factory function to create a LocalLLMBehavior with LlamaCppBackend.

    This is a convenience function that handles backend creation.
    For more control, create the backend manually and pass it to LocalLLMBehavior.

    Args:
        model_path: Path to the GGUF model file
        system_prompt: System prompt for the agent
        n_gpu_layers: GPU layers to offload (-1 = all, 0 = CPU only)
        temperature: LLM temperature (0-1)
        max_tokens: Maximum tokens per response

    Returns:
        Configured LocalLLMBehavior instance

    Example:
        behavior = create_local_llm_behavior(
            model_path="models/llama-2-7b.gguf",
            system_prompt="You are a foraging agent.",
            n_gpu_layers=-1
        )
    """
    from backends import BackendConfig, LlamaCppBackend

    config = BackendConfig(
        model_path=model_path,
        temperature=temperature,
        max_tokens=max_tokens,
        n_gpu_layers=n_gpu_layers,
    )

    backend = LlamaCppBackend(config)

    return LocalLLMBehavior(
        backend=backend,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )
