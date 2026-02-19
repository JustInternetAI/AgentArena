"""
LocalLLMBehavior - Bridges local LLM backends to AgentBehavior API.

This module provides LocalLLMBehavior, a behavior class that wraps local LLM backends
(LlamaCppBackend, VLLMBackend) and implements the AgentBehavior interface,
allowing local GPU-accelerated LLMs to power agents via the IPC server.

Unlike LLMAgentBehavior which uses external API services, LocalLLMBehavior
uses in-process GPU-accelerated inference via BaseBackend implementations.
"""

import logging
from typing import TYPE_CHECKING

from .behavior import AgentBehavior
from .memory import SlidingWindowMemory

# Backwards compatibility
from .reasoning_trace import (
    PromptInspector,
    TraceStepName,
    get_global_inspector,
)
from .schemas import AgentDecision, Observation, ToolSchema

if TYPE_CHECKING:
    from backends.base import BaseBackend

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

        # Register with arena
        arena.register("agent_001", behavior)
    """

    def __init__(
        self,
        backend: "BaseBackend",
        system_prompt: str = "You are an autonomous agent in a simulation environment.",
        memory_capacity: int = 10,
        temperature: float = 0.7,
        max_tokens: int = 256,
        inspector: PromptInspector | None = None,
    ):
        """
        Initialize the local LLM behavior.

        Args:
            backend: Local LLM backend (LlamaCppBackend or VLLMBackend)
            system_prompt: System prompt describing the agent's role and task
            memory_capacity: Number of recent observations to keep in memory
            temperature: Temperature for generation (0-1)
            max_tokens: Maximum tokens to generate per decision
            inspector: Optional PromptInspector for debugging (uses global if None)
        """
        self.backend = backend
        self.system_prompt = system_prompt
        self.memory = SlidingWindowMemory(capacity=memory_capacity)
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.inspector = inspector or get_global_inspector()

        # Validate backend is available
        if not self.backend.is_available():
            raise RuntimeError("Backend is not available - model may not be loaded")

        logger.info(
            f"Initialized LocalLLMBehavior with {type(backend).__name__} "
            f"(memory_capacity={memory_capacity})"
        )

    def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
        """
        Decide what action to take given the current observation.

        Constructs a prompt from the system prompt, memory, and current observation,
        then calls the backend's generate_with_tools() method to get a decision.

        If tracing is enabled (via enable_tracing()), each step is automatically logged:
        - observation: The input observation
        - prompt: The constructed prompt
        - llm_response: The raw LLM response
        - decision: The parsed decision

        Args:
            observation: Current tick's observation from Godot
            tools: List of available tools with their schemas

        Returns:
            AgentDecision specifying which tool to call and with what parameters
        """
        # Start trace capture
        capture = self.inspector.start_capture(observation.agent_id, observation.tick)
        self._current_trace = capture  # Enable log_step() calls

        try:
            # Store observation in memory
            self.memory.store(observation)

            # Capture observation stage
            if capture:
                capture.add_step(
                    TraceStepName.OBSERVATION,
                    {
                        "agent_id": observation.agent_id,
                        "tick": observation.tick,
                        "position": observation.position,
                        "health": observation.health,
                        "energy": observation.energy,
                        "nearby_resources": [
                            {
                                "name": r.name,
                                "type": r.type,
                                "distance": r.distance,
                                "position": r.position,
                            }
                            for r in observation.nearby_resources
                        ],
                        "nearby_hazards": [
                            {
                                "name": h.name,
                                "type": h.type,
                                "distance": h.distance,
                                "damage": h.damage,
                            }
                            for h in observation.nearby_hazards
                        ],
                        "inventory": [
                            {"name": item.name, "quantity": item.quantity}
                            for item in observation.inventory
                        ],
                    },
                )

            # Build prompt from system prompt, memory, and observation
            prompt = self._build_prompt(observation, tools)
            logger.debug(f"Prompt length: {len(prompt)} chars (~{len(prompt) // 4} tokens)")

            # Log prompt (if tracing enabled)
            self.log_step("prompt", {"text": prompt})

            # Capture prompt building stage
            if capture:
                memory_items = self.memory.retrieve(limit=5)
                capture.add_step(
                    TraceStepName.PROMPT_BUILDING,
                    {
                        "system_prompt": self.system_prompt,
                        "memory_context": {
                            "count": len(memory_items),
                            "items": [
                                {"tick": obs.tick, "position": obs.position} for obs in memory_items
                            ],
                        },
                        "final_prompt": prompt,
                        "prompt_length": len(prompt),
                        "estimated_tokens": len(prompt) // 4,
                    },
                )

            # Convert tools to dict format for backend
            tool_dicts = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                }
                for tool in tools
            ]

            # Capture LLM request stage
            if capture:
                capture.add_step(
                    TraceStepName.LLM_REQUEST,
                    {
                        "model": getattr(self.backend, "model_name", "unknown"),
                        "prompt": prompt,
                        "tools": tool_dicts,
                        "temperature": self.temperature,
                        "max_tokens": self.max_tokens,
                    },
                )

            # Generate response using backend
            import time

            start_time = time.time()
            logger.debug(f"Generating decision for agent {observation.agent_id}")
            result = self.backend.generate_with_tools(
                prompt=prompt, tools=tool_dicts, temperature=self.temperature
            )
            elapsed_ms = (time.time() - start_time) * 1000

            # Capture LLM response stage
            if capture:
                capture.add_step(
                    TraceStepName.LLM_RESPONSE,
                    {
                        "raw_text": result.text,
                        "tokens_used": result.tokens_used,
                        "finish_reason": result.finish_reason,
                        "metadata": result.metadata,
                        "latency_ms": elapsed_ms,
                    },
                )

            # Check for generation errors
            if result.finish_reason == "error":
                error_msg = result.metadata.get("error", "Unknown error")
                logger.error(f"LLM generation error: {error_msg}")
                decision = AgentDecision.idle(reasoning=f"LLM error: {error_msg}")

                # Capture error decision
                if capture:
                    capture.add_step(
                        TraceStepName.DECISION,
                        {
                            "tool": decision.tool,
                            "params": decision.params,
                            "reasoning": decision.reasoning,
                            "total_latency_ms": elapsed_ms,
                            "error": error_msg,
                        },
                    )

                self.inspector.finish_capture(observation.agent_id, observation.tick)
                self._current_trace = None  # Clear for next decision
                return decision

            # Debug: log token usage and raw response
            logger.debug(f"Tokens used: {result.tokens_used}")
            logger.debug(f"Raw LLM response: {result.text[:500] if result.text else '(empty)'}")

            # Log LLM response (if tracing enabled)
            self.log_step(
                "llm_response",
                {
                    "text": result.text,
                    "tokens_used": result.tokens_used,
                    "finish_reason": result.finish_reason,
                    "elapsed_ms": elapsed_ms,
                },
            )

            # Try to parse from metadata first (pre-parsed by backend)
            if "parsed_tool_call" in result.metadata:
                parsed = result.metadata["parsed_tool_call"]
                decision = AgentDecision(
                    tool=parsed.get("tool", "idle"),
                    params=parsed.get("params", {}),
                    reasoning=parsed.get("reasoning", ""),
                )
            elif "tool_call" in result.metadata:
                # Native tool call from vLLM
                tool_call = result.metadata["tool_call"]
                decision = AgentDecision(
                    tool=tool_call["name"],
                    params=tool_call["arguments"],
                    reasoning=result.text or "LLM tool call",
                )
            else:
                # Parse the raw text response using robust JSON extraction
                try:
                    decision = AgentDecision.from_llm_response(result.text)
                except ValueError as e:
                    logger.warning(f"Failed to parse LLM response: {e}")
                    logger.debug(f"Raw response: {result.text}")
                    decision = AgentDecision.idle(reasoning=f"Parse error: {e}")

            # Capture final decision stage
            if capture:
                capture.add_step(
                    TraceStepName.DECISION,
                    {
                        "tool": decision.tool,
                        "params": decision.params,
                        "reasoning": decision.reasoning,
                        "total_latency_ms": elapsed_ms,
                    },
                )

            logger.info(
                f"Agent {observation.agent_id} decided: {decision.tool} - {decision.reasoning} "
                f"(LLM took {elapsed_ms:.0f}ms, {result.tokens_used} tokens)"
            )

            # Finish capture and optionally write to file
            self.inspector.finish_capture(observation.agent_id, observation.tick)
            self._current_trace = None  # Clear for next decision

            return decision

        except Exception as e:
            logger.error(f"Error in LocalLLMBehavior.decide(): {e}", exc_info=True)

            # Capture error in inspector
            if capture:
                capture.add_step(
                    TraceStepName.DECISION,
                    {"tool": "idle", "params": {}, "reasoning": f"Error: {e}", "error": str(e)},
                )
                self.inspector.finish_capture(observation.agent_id, observation.tick)
                self._current_trace = None  # Clear for next decision

            return AgentDecision.idle(reasoning=f"Error: {e}")

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
        sections = []

        # Add system prompt
        if self.system_prompt:
            sections.append(self.system_prompt)
            sections.append("")

        # Add memory context if available
        memory_items = self.memory.retrieve(limit=5)
        if memory_items and len(memory_items) > 1:  # Don't include if only current observation
            sections.append("## Recent History")
            # Memory items are returned most recent first, so reverse and skip last (current)
            for i, obs in enumerate(reversed(memory_items[1:]), 1):
                sections.append(f"  {i}. Tick {obs.tick}: Position {obs.position}")
                if obs.nearby_resources:
                    sections.append(f"     Resources nearby: {len(obs.nearby_resources)}")
                if obs.nearby_hazards:
                    sections.append(f"     Hazards nearby: {len(obs.nearby_hazards)}")
            sections.append("")

        # Current state
        sections.append("## Current Situation")
        sections.append(f"Position: {observation.position}")
        sections.append(f"Health: {observation.health}")
        sections.append(f"Energy: {observation.energy}")
        sections.append(f"Tick: {observation.tick}")

        # Add analysis hints (but let LLM reason)
        danger_hazards = [h for h in observation.nearby_hazards if h.distance < 2.0]
        collect_resources = [r for r in observation.nearby_resources if r.distance < 1.0]

        sections.append("\n## Quick Analysis")
        sections.append(f"Hazards in danger zone (< 2.0): {len(danger_hazards)}")
        sections.append(f"Resources in collection range (< 1.0): {len(collect_resources)}")

        # Nearby resources
        if observation.nearby_resources:
            sections.append("\n## Nearby Resources")
            for resource in observation.nearby_resources[:5]:  # Limit to 5 for brevity
                sections.append(
                    f"- {resource.name} ({resource.type}) at distance {resource.distance:.1f}, "
                    f"position {resource.position}"
                )
        else:
            sections.append("\n## Nearby Resources\nNone visible")

        # Nearby hazards
        if observation.nearby_hazards:
            sections.append("\n## Nearby Hazards")
            for hazard in observation.nearby_hazards[:5]:  # Limit to 5 for brevity
                damage_str = f", damage: {hazard.damage}" if hazard.damage > 0 else ""
                sections.append(
                    f"- {hazard.name} ({hazard.type}) at distance {hazard.distance:.1f}{damage_str}, "
                    f"position {hazard.position}"
                )
        else:
            sections.append("\n## Nearby Hazards\nNone visible")

        # Remembered objects from world_map (out of sight but known)
        visible_names = {r.name for r in observation.nearby_resources}
        visible_names.update(h.name for h in observation.nearby_hazards)

        remembered_resources = [
            obj for obj in self.world_map.get_resources() if obj.name not in visible_names
        ]
        remembered_hazards = [
            obj for obj in self.world_map.get_hazards() if obj.name not in visible_names
        ]

        if remembered_resources or remembered_hazards:
            sections.append("\n## Remembered Objects (out of sight)")
            if remembered_resources:
                # Sort by distance from current position
                remembered_resources.sort(key=lambda obj: obj.distance_to(observation.position))
                sections.append("Resources:")
                for obj in remembered_resources[:5]:
                    dist = obj.distance_to(observation.position)
                    stale = observation.tick - obj.last_seen_tick
                    sections.append(
                        f"- {obj.name} ({obj.subtype}) at position {obj.position}, "
                        f"~{dist:.1f} units away (last seen {stale} ticks ago)"
                    )
            if remembered_hazards:
                remembered_hazards.sort(key=lambda obj: obj.distance_to(observation.position))
                sections.append("Hazards:")
                for obj in remembered_hazards[:3]:
                    dist = obj.distance_to(observation.position)
                    sections.append(
                        f"- {obj.name} ({obj.subtype}) at position {obj.position}, "
                        f"~{dist:.1f} units away, damage: {obj.damage}"
                    )

        # Recent Experiences (collisions, damage, traps)
        # Note: Always access world_map - it's lazy-loaded and always returns a valid instance.
        # Don't use truthiness check as SpatialMemory.__len__ returns object count which may be 0.
        experiences = self.world_map.get_recent_experiences(limit=5)
        if experiences:
            sections.append("\n## Recent Experiences")
            for exp in experiences:
                if exp.event_type == "collision":
                    sections.append(
                        f"- Tick {exp.tick}: Movement BLOCKED by {exp.object_name} "
                        f"at position {exp.position}"
                    )
                elif exp.event_type == "damage":
                    sections.append(
                        f"- Tick {exp.tick}: Took {exp.damage_taken:.1f} damage from "
                        f"{exp.object_name} at {exp.position}"
                    )
                elif exp.event_type == "trapped":
                    ticks_trapped = exp.metadata.get("trap_duration", "?")
                    sections.append(
                        f"- Tick {exp.tick}: TRAPPED by {exp.object_name}! "
                        f"Lost {ticks_trapped} ticks"
                    )

        # Known Obstacles from collisions
        obstacles = self.world_map.query_by_type("obstacle")
        if obstacles:
            sections.append("\n## Known Obstacles (from collisions)")
            for obstacle in obstacles[:5]:
                sections.append(f"- {obstacle.name} at {obstacle.position}")

        # Exploration Status
        if observation.exploration:
            exploration = observation.exploration
            sections.append("\n## Exploration Status")
            sections.append(f"Area explored: {exploration.exploration_percentage:.1f}%")

            if exploration.frontiers_by_direction:
                sections.append("Unexplored frontiers:")
                # Sort by distance (nearest first)
                sorted_frontiers = sorted(
                    exploration.frontiers_by_direction.items(), key=lambda x: x[1]
                )
                for direction, distance in sorted_frontiers[:5]:
                    sections.append(f"- {direction.upper()}: {distance:.1f} units away")

            if exploration.explore_targets:
                sections.append("\nSuggested exploration targets:")
                for target in exploration.explore_targets[:3]:
                    sections.append(
                        f"- {target.direction.upper()}: position {target.position}, "
                        f"{target.distance:.1f} units away"
                    )

        # Inventory
        if observation.inventory:
            sections.append("\n## Inventory")
            for item in observation.inventory:
                sections.append(f"- {item.name} x{item.quantity}")
        else:
            sections.append("\n## Inventory\nEmpty")

        # Add instruction for response format (CoT)
        sections.append("\n## Your Task")
        sections.append(
            "Follow the RESPONSE FORMAT from your instructions. "
            "Show your THINKING step by step, then output your ACTION as JSON."
        )

        return "\n".join(sections)

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

        Clears memory to start fresh. If tracing is enabled, starts a new trace episode.
        """
        super().on_episode_start()  # Handle trace episode start and world_map clearing
        logger.info("Episode started, clearing memory")
        self.memory.clear()
        # Note: world_map clearing is handled by super().on_episode_start()
        # which checks _world_map is not None (avoiding SpatialMemory truthiness issue)

    def on_episode_end(self, success: bool, metrics: dict | None = None) -> None:
        """
        Called when an episode ends.

        Args:
            success: Whether the episode goal was achieved
            metrics: Optional metrics from the scenario
        """
        logger.info(f"Episode ended: success={success}, observations_stored={len(self.memory)}")
        if metrics:
            logger.info(f"Episode metrics: {metrics}")
        super().on_episode_end(success, metrics)  # Handle trace episode end


def create_local_llm_behavior(
    model_path: str,
    system_prompt: str = "",
    n_gpu_layers: int = -1,
    temperature: float = 0.7,
    max_tokens: int = 256,
    memory_capacity: int = 10,
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
        memory_capacity: Number of recent observations to keep in memory

    Returns:
        Configured LocalLLMBehavior instance

    Example:
        behavior = create_local_llm_behavior(
            model_path="models/mistral-7b.gguf",
            system_prompt="You are a foraging agent.",
            n_gpu_layers=-1
        )
    """
    from backends import BackendConfig, LlamaCppBackend

    # Use default foraging prompt if none provided
    if not system_prompt:
        system_prompt = """You are an autonomous foraging agent in a simulation environment.

Your goal is to:
1. Collect resources (like apples) to increase your score
2. Avoid hazards (like fire) that can damage you
3. Manage your health and energy efficiently

When you receive an observation, analyze the situation and choose the best action.
Prioritize safety (avoid hazards) over collecting resources."""

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
        memory_capacity=memory_capacity,
        temperature=temperature,
        max_tokens=max_tokens,
    )
