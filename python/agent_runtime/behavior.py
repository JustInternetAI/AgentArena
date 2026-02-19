"""
Agent behavior interfaces.

This module defines the base classes for agent decision-making logic,
organized into a three-tier learning progression:

BEGINNER TIER: SimpleAgentBehavior
    - User returns a tool name (string)
    - Framework handles parameters, memory, and context
    - Focus: Understanding the perception → decision → action loop

INTERMEDIATE TIER: AgentBehavior
    - User returns AgentDecision with tool, params, and reasoning
    - Built-in world_map (SpatialMemory) for tracking object positions
    - User implements lifecycle hooks (on_episode_start, on_tool_result)
    - Focus: State tracking, explicit parameters, memory patterns

ADVANCED TIER: LLMAgentBehavior
    - User integrates LLM backends (Anthropic, OpenAI, Ollama)
    - User implements custom memory systems and planning
    - User controls prompt engineering and response parsing
    - Focus: LLM reasoning, planning, multi-agent coordination

See docs/learners/ for tutorials at each tier.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from .memory.spatial import SpatialMemory
    from .reasoning_trace import ReasoningTrace, TraceStore
    from .schemas import AgentDecision, Observation, SimpleContext, ToolSchema


class AgentBehavior(ABC):
    """
    Base class for agent decision-making logic (Intermediate Tier).

    Users implement this to create agents with full control over decisions.
    The framework calls `decide()` each tick with the current observation
    and available tools.

    This is the intermediate tier interface. For beginners, see
    SimpleAgentBehavior. For advanced LLM integration, see LLMAgentBehavior.

    Built-in Features:
        - world_map: SpatialMemory that automatically tracks all resources,
          hazards, and entities the agent has seen. Updated each tick.
        - Tracing support for debugging decision logic.

    Example:
        from agent_runtime import AgentBehavior, Observation, AgentDecision, ToolSchema

        class MyAgent(AgentBehavior):
            def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
                # world_map is automatically updated each tick
                # Query remembered objects (even those out of sight)
                remembered = self.world_map.query_near_position(
                    observation.position, radius=50, object_type="resource"
                )

                # Prefer visible resources, fall back to remembered ones
                if observation.nearby_resources:
                    target = observation.nearby_resources[0]
                    return AgentDecision(
                        tool="move_to",
                        params={"target_position": list(target.position)},
                        reasoning=f"Moving to visible {target.name}"
                    )
                elif remembered:
                    target = remembered[0].obj
                    return AgentDecision(
                        tool="move_to",
                        params={"target_position": list(target.position)},
                        reasoning=f"Moving to remembered {target.name}"
                    )

                return AgentDecision.idle(reasoning="No resources known")
    """

    # Framework-managed attributes (set by IPC server before decide())
    _world_map: Optional["SpatialMemory"] = None
    _trace_store: Optional["TraceStore"] = None
    _agent_id: str | None = None
    _current_trace: Optional["ReasoningTrace"] = None

    @property
    def world_map(self) -> "SpatialMemory":
        """Public accessor for spatial memory. Lazily creates if needed."""
        if self._world_map is None:
            from .memory.spatial import SpatialMemory

            self._world_map = SpatialMemory()
        return self._world_map

    def _set_trace_context(self, agent_id: str, tick: int) -> None:
        """Set trace context before decide(). Called by the IPC server."""
        self._agent_id = agent_id
        if self._trace_store is not None:
            self._current_trace = self._trace_store.start_capture(agent_id, tick)

    def _update_world_map(self, observation: "Observation") -> None:
        """Update spatial memory with current observation. Called by the IPC server."""
        if self._world_map is not None:
            self._world_map.update_from_observation(observation)

    def _end_trace(self) -> None:
        """End and persist the current trace. Called by the IPC server."""
        if self._current_trace is not None and self._trace_store is not None:
            self._trace_store.finish_capture(self._current_trace.agent_id, self._current_trace.tick)
        self._current_trace = None

    @abstractmethod
    def decide(self, observation: "Observation", tools: list["ToolSchema"]) -> "AgentDecision":
        """
        Decide what action to take given the current observation.

        Args:
            observation: Current tick's observation from Godot
            tools: List of available tools with their schemas

        Returns:
            AgentDecision specifying which tool to call and with what parameters
        """
        pass

    def log_step(self, name: str, data: dict[str, Any], duration_ms: float | None = None) -> None:
        """
        Log a reasoning step for debugging and analysis.

        This method integrates with the TraceStore system from issue #45.
        Call this during decide() to record intermediate reasoning steps.

        Args:
            name: Step name (e.g., "retrieved", "prompt", "response")
            data: Arbitrary data for this step (will be JSON-serialized)
            duration_ms: Optional duration of this step in milliseconds

        Example:
            def decide(self, observation, tools):
                # Log memory retrieval
                relevant = self.memory.query(observation, k=5)
                self.log_step("retrieved", {"count": len(relevant), "items": relevant})

                # Log prompt
                prompt = self.build_prompt(observation, relevant)
                self.log_step("prompt", {"text": prompt, "length": len(prompt)})

                # ... rest of decision logic
        """
        if self._current_trace:
            self._current_trace.add_step(name, data, duration_ms)

    def on_tool_result(self, tool: str, result: dict) -> None:
        """
        Called after a tool execution completes.

        Override to react to tool results (e.g., update memory, adjust strategy).

        Args:
            tool: Name of the tool that was executed
            result: Result dictionary from the tool
        """
        pass

    def on_episode_start(self) -> None:
        """
        Called when a new episode begins.

        Override to reset state, clear memory, etc.
        The world_map is automatically cleared. If tracing is enabled,
        a new episode is started in the trace store.

        If you override this method, call super().on_episode_start() to
        ensure the world map is cleared.
        """
        # Clear world map for new episode
        if self._world_map is not None:
            self._world_map.clear()

        # Start a new trace episode if tracing is enabled
        if self._trace_store is not None and self._agent_id is not None:
            self._trace_store.start_episode(self._agent_id)

    def on_episode_end(self, success: bool, metrics: dict | None = None) -> None:
        """
        Called when an episode ends.

        Override to perform cleanup, learning, or logging.
        If tracing is enabled, the final trace is ended.

        Args:
            success: Whether the episode goal was achieved
            metrics: Optional metrics from the scenario
        """
        # End any pending trace
        self._end_trace()


class SimpleAgentBehavior(AgentBehavior):
    """
    Simplified interface for beginners.

    Users only need to implement `decide()` returning a tool name.
    The framework handles memory, prompts, and parameter inference.

    Example:
        class MyFirstAgent(SimpleAgentBehavior):
            system_prompt = "You are a foraging agent. Collect apples."

            def decide(self, context):
                if context.nearby_resources:
                    return "move_to"  # Framework infers target
                return "idle"
    """

    # User can override these class attributes
    system_prompt: str = "You are an autonomous agent."
    memory_capacity: int = 10

    def __init__(self):
        """Initialize the simple agent behavior."""
        self._observations: list = []
        self._goal: str | None = None

    @abstractmethod
    def decide(self, context: "SimpleContext") -> str:  # type: ignore[override]
        """
        Decide which tool to use.

        Args:
            context: Simplified context with key information

        Returns:
            Name of the tool to execute (e.g., "move_to", "pickup", "idle")
        """
        pass

    def set_goal(self, goal: str) -> None:
        """
        Set the current goal for the agent.

        Args:
            goal: Goal description
        """
        self._goal = goal

    # Internal method - framework uses this
    def _internal_decide(
        self, observation: "Observation", tools: list["ToolSchema"]
    ) -> "AgentDecision":
        """
        Framework calls this; converts to SimpleContext and calls user's decide().

        This is an internal method used by the framework to bridge the full
        AgentBehavior interface to the simplified interface.

        Args:
            observation: Full observation from Godot
            tools: List of available tools

        Returns:
            AgentDecision with inferred parameters
        """
        from .schemas import AgentDecision, SimpleContext

        # Store observation for memory
        self._observations.append(observation)
        if len(self._observations) > self.memory_capacity:
            self._observations = self._observations[-self.memory_capacity :]

        # Build simple context
        context = SimpleContext.from_observation(observation, self._goal)

        # Get tool name from user
        tool_name = self.decide(context)

        # Infer parameters based on context
        params = self._infer_parameters(tool_name, context, tools)

        return AgentDecision(tool=tool_name, params=params)

    def _infer_parameters(
        self, tool_name: str, context: "SimpleContext", tools: list["ToolSchema"]
    ) -> dict:
        """
        Infer tool parameters from context.

        Uses heuristics to fill in parameters for common tools based on
        the current context.

        Args:
            tool_name: Name of the tool to execute
            context: Simplified context
            tools: Available tool schemas

        Returns:
            Dictionary of inferred parameters
        """
        # move_to: target nearest resource or hazard to avoid
        if tool_name == "move_to":
            if context.nearby_resources:
                # Move to nearest resource
                nearest = min(
                    context.nearby_resources, key=lambda r: r.get("distance", float("inf"))
                )
                # Get position from the resource dict
                if "position" in nearest:
                    return {"target_position": nearest["position"]}
                # Fallback: use distance to calculate approximate position
                return {"target_position": context.position}
            elif context.nearby_hazards:
                # Move away from nearest hazard
                hazard = min(context.nearby_hazards, key=lambda h: h.get("distance", float("inf")))
                # Calculate escape position away from hazard
                if "position" in hazard:
                    hx, hy, hz = hazard["position"]
                    px, py, pz = context.position
                    dx, dy, dz = px - hx, py - hy, pz - hz
                    dist = (dx**2 + dy**2 + dz**2) ** 0.5
                    if dist > 0:
                        # Move 5 units away from hazard
                        escape_x = px + (dx / dist) * 5.0
                        escape_y = py + (dy / dist) * 5.0
                        escape_z = pz + (dz / dist) * 5.0
                        return {"target_position": (escape_x, escape_y, escape_z)}
                return {"target_position": context.position}
            else:
                # No target, stay in place
                return {"target_position": context.position}

        # pickup: pick up nearest resource
        elif tool_name == "pickup":
            if context.nearby_resources:
                nearest = min(
                    context.nearby_resources, key=lambda r: r.get("distance", float("inf"))
                )
                return {"item_id": nearest.get("name", "")}
            return {}

        # drop: drop first item in inventory
        elif tool_name == "drop":
            if context.inventory:
                return {"item_name": context.inventory[0]}
            return {}

        # use: use first item in inventory
        elif tool_name == "use":
            if context.inventory:
                return {"item_name": context.inventory[0]}
            return {}

        # Default: no parameters
        return {}


class LLMAgentBehavior(AgentBehavior):
    """
    LLM-powered agent behavior (Advanced Tier).

    Extends AgentBehavior with LLM integration capabilities. Users specify
    the LLM backend and model, then use the `complete()` method to get
    LLM responses for decision-making.

    Example:
        from agent_runtime import LLMAgentBehavior, Observation, AgentDecision, ToolSchema

        class MyLLMAgent(LLMAgentBehavior):
            def __init__(self):
                super().__init__(backend="anthropic", model="claude-3-haiku-20240307")
                self.system_prompt = "You are an intelligent foraging agent."

            def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
                context = self._format_observation(observation)
                response = self.complete(context)
                return self._parse_response(response, tools)

    Supported backends:
        - "anthropic": Claude models (requires ANTHROPIC_API_KEY)
        - "openai": GPT models (requires OPENAI_API_KEY)
        - "ollama": Local models (requires ollama serve running)
    """

    def __init__(self, backend: str = "anthropic", model: str = "claude-3-haiku-20240307"):
        """
        Initialize the LLM agent behavior.

        Args:
            backend: LLM provider ("anthropic", "openai", "ollama")
            model: Model identifier for the chosen backend
        """
        self.backend = backend
        self.model = model
        self.system_prompt: str = "You are an autonomous agent."
        self._client = None

    def complete(self, prompt: str, system: str | None = None, temperature: float = 0.7) -> str:
        """
        Send a prompt to the LLM and get a response.

        Args:
            prompt: The prompt to send to the LLM
            system: Optional system prompt override (uses self.system_prompt if None)
            temperature: Randomness of response (0 = deterministic, 1 = creative)

        Returns:
            The LLM's response as a string
        """
        # Lazy initialization of client
        if self._client is None:
            self._client = self._create_client()

        sys_prompt = system if system is not None else self.system_prompt
        return self._call_llm(prompt, sys_prompt, temperature)

    def _create_client(self):
        """Create the LLM client based on backend."""
        if self.backend == "anthropic":
            try:
                import anthropic

                return anthropic.Anthropic()
            except ImportError:
                raise ImportError("Install anthropic: pip install anthropic")
        elif self.backend == "openai":
            try:
                import openai

                return openai.OpenAI()
            except ImportError:
                raise ImportError("Install openai: pip install openai")
        elif self.backend == "ollama":
            try:
                import ollama

                return ollama
            except ImportError:
                raise ImportError("Install ollama: pip install ollama")
        else:
            raise ValueError(f"Unknown backend: {self.backend}")

    def _call_llm(self, prompt: str, system: str, temperature: float) -> str:
        """Make the actual LLM API call."""
        # Client is guaranteed to be initialized by complete() before this is called
        assert self._client is not None, "LLM client not initialized"

        if self.backend == "anthropic":
            response = self._client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=system,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
            )
            return str(response.content[0].text)
        elif self.backend == "openai":
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
            )
            content = response.choices[0].message.content
            return str(content) if content else ""
        elif self.backend == "ollama":
            response = self._client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                options={"temperature": temperature},
            )
            return str(response["message"]["content"])
        else:
            raise ValueError(f"Unknown backend: {self.backend}")

    def decide(self, observation: "Observation", tools: list["ToolSchema"]) -> "AgentDecision":
        """
        Decide what action to take using the LLM.

        Override this method to implement your agent's decision logic.
        Use self.complete() to get LLM responses.

        Args:
            observation: Current tick's observation from Godot
            tools: List of available tools with their schemas

        Returns:
            AgentDecision specifying which tool to call and with what parameters
        """
        # Default implementation - override in subclass
        from .schemas import AgentDecision

        return AgentDecision.idle(reasoning="LLMAgentBehavior.decide() not implemented")
