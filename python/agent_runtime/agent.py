"""
Core Agent implementation with perception, reasoning, and action capabilities.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class Observation:
    """Represents an agent's observation of the world."""

    timestamp: datetime
    data: Dict[str, Any]
    source: str = "world"


@dataclass
class Action:
    """Represents an action the agent wants to take."""

    tool_name: str
    parameters: Dict[str, Any]
    reasoning: Optional[str] = None


@dataclass
class AgentState:
    """Internal state of an agent."""

    agent_id: str
    goals: List[str] = field(default_factory=list)
    observations: List[Observation] = field(default_factory=list)
    action_history: List[Action] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class Agent:
    """
    Base Agent class for LLM-driven autonomous agents.

    Agents perceive the world, reason about their goals, and take actions
    using available tools through an LLM backend.
    """

    def __init__(
        self,
        agent_id: str,
        backend: Optional[Any] = None,  # LLM backend instance
        tools: Optional[List[str]] = None,
        goals: Optional[List[str]] = None,
    ):
        """
        Initialize an agent.

        Args:
            agent_id: Unique identifier for this agent
            backend: LLM backend for reasoning (e.g., llama.cpp, vLLM)
            tools: List of available tool names
            goals: Initial goals for the agent
        """
        self.state = AgentState(
            agent_id=agent_id,
            goals=goals or [],
        )
        self.backend = backend
        self.available_tools = tools or []
        self.memory_capacity = 10  # Number of recent observations to keep in context

        logger.info(f"Initialized agent {agent_id} with {len(self.available_tools)} tools")

    def perceive(self, observation: Dict[str, Any], source: str = "world") -> None:
        """
        Process a new observation from the environment.

        Args:
            observation: Raw observation data from the world
            source: Source of the observation (e.g., "vision", "audio")
        """
        obs = Observation(
            timestamp=datetime.now(),
            data=observation,
            source=source,
        )
        self.state.observations.append(obs)

        # Keep only recent observations to manage memory
        if len(self.state.observations) > self.memory_capacity:
            self.state.observations = self.state.observations[-self.memory_capacity :]

        logger.debug(f"Agent {self.state.agent_id} received observation from {source}")

    def decide_action(self) -> Optional[Action]:
        """
        Use the LLM backend to decide the next action based on current state.

        Returns:
            Action to take, or None if no action is needed
        """
        if not self.backend:
            logger.warning(f"Agent {self.state.agent_id} has no backend, cannot decide action")
            return None

        # Prepare context for LLM
        context = self._build_context()

        # Query LLM for next action
        # This is a placeholder - actual implementation depends on backend
        try:
            response = self._query_llm(context)
            action = self._parse_action(response)

            if action:
                self.state.action_history.append(action)
                logger.info(f"Agent {self.state.agent_id} decided action: {action.tool_name}")

            return action

        except Exception as e:
            logger.error(f"Error deciding action for agent {self.state.agent_id}: {e}")
            return None

    def _build_context(self) -> str:
        """Build the context string for LLM prompting."""
        context_parts = []

        # Add agent identity and goals
        context_parts.append(f"You are agent {self.state.agent_id}.")
        if self.state.goals:
            context_parts.append(f"Your goals: {', '.join(self.state.goals)}")

        # Add recent observations
        if self.state.observations:
            context_parts.append("\nRecent observations:")
            for obs in self.state.observations[-5:]:  # Last 5 observations
                context_parts.append(f"- [{obs.source}] {obs.data}")

        # Add available tools
        if self.available_tools:
            context_parts.append(f"\nAvailable tools: {', '.join(self.available_tools)}")

        # Add action history context
        if self.state.action_history:
            context_parts.append("\nRecent actions:")
            for action in self.state.action_history[-3:]:  # Last 3 actions
                context_parts.append(f"- {action.tool_name}: {action.parameters}")

        context_parts.append("\nWhat action should you take next?")

        return "\n".join(context_parts)

    def _query_llm(self, context: str) -> str:
        """
        Query the LLM backend with the given context.

        This is a placeholder that should be implemented based on the specific backend.
        """
        # TODO: Implement actual LLM querying based on backend type
        return '{"tool": "idle", "params": {}}'

    def _parse_action(self, response: str) -> Optional[Action]:
        """
        Parse the LLM response into an Action object.

        Expected format: JSON with "tool" and "params" keys
        """
        import json

        try:
            data = json.loads(response)
            return Action(
                tool_name=data.get("tool", "idle"),
                parameters=data.get("params", {}),
                reasoning=data.get("reasoning"),
            )
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return None

    def add_goal(self, goal: str) -> None:
        """Add a new goal for the agent."""
        self.state.goals.append(goal)
        logger.info(f"Agent {self.state.agent_id} added goal: {goal}")

    def clear_goals(self) -> None:
        """Clear all current goals."""
        self.state.goals.clear()
        logger.info(f"Agent {self.state.agent_id} cleared all goals")

    def get_state(self) -> AgentState:
        """Get the current agent state."""
        return self.state
