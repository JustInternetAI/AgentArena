"""
Base memory interface for agents.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..schemas import Observation


class AgentMemory(ABC):
    """
    Abstract base class for agent memory systems.

    Memory systems store and retrieve observations to provide context
    for agent decision-making. Different implementations offer different
    trade-offs between memory capacity, retrieval speed, and semantic understanding.

    Example:
        class MyAgent(AgentBehavior):
            def __init__(self, backend):
                self.backend = backend
                self.memory = SlidingWindowMemory(capacity=10)

            def decide(self, observation, tools):
                # Store observation
                self.memory.store(observation)

                # Get context for LLM
                context = self.memory.summarize()

                # Make decision using context
                response = self.backend.generate(context)
                return AgentDecision.from_llm_response(response)
    """

    @abstractmethod
    def store(self, observation: "Observation") -> None:
        """
        Store an observation in memory.

        Args:
            observation: The observation to store
        """
        pass

    @abstractmethod
    def retrieve(self, query: str | None = None, limit: int | None = None) -> list["Observation"]:
        """
        Retrieve observations from memory.

        Args:
            query: Optional query string for semantic retrieval (implementation-dependent)
            limit: Optional maximum number of observations to return

        Returns:
            List of observations (most recent or most relevant)
        """
        pass

    @abstractmethod
    def summarize(self) -> str:
        """
        Create a text summary of memory contents for LLM context.

        Returns:
            String representation suitable for including in LLM prompts
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """
        Clear all stored memories.

        Used to reset state between episodes.
        """
        pass

    @abstractmethod
    def dump(self) -> dict:
        """
        Dump full memory state for inspection/debugging.

        Returns a dictionary containing the complete memory state that can be
        serialized to JSON for analysis. This is useful for debugging agent
        behavior and understanding what the agent "remembers".

        Returns:
            Dictionary containing complete memory state
        """
        pass

    def __len__(self) -> int:
        """
        Get number of observations in memory.

        Returns:
            Count of stored observations
        """
        return len(self.retrieve())
