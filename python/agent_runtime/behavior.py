"""
Agent behavior interfaces.

Defines the contracts that user agents must fulfill.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .schemas import AgentDecision, Observation, SimpleContext, ToolSchema


class AgentBehavior(ABC):
    """
    Base class for agent decision-making logic.

    Users implement this to create custom agents. The framework calls
    `decide()` each tick with the current observation and available tools.

    Example:
        class MyAgent(AgentBehavior):
            def __init__(self, backend):
                self.backend = backend
                self.memory = SlidingWindowMemory(capacity=10)

            def decide(self, observation, tools):
                self.memory.store(observation)
                prompt = self._build_prompt(observation)
                response = self.backend.generate(prompt)
                return AgentDecision.from_llm_response(response)
    """

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
        """
        pass

    def on_episode_end(self, success: bool, metrics: dict | None = None) -> None:
        """
        Called when an episode ends.

        Override to perform cleanup, learning, or logging.

        Args:
            success: Whether the episode goal was achieved
            metrics: Optional metrics from the scenario
        """
        pass


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
