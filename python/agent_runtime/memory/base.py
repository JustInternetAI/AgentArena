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
    for agent decision-making.
    """

    @abstractmethod
    def store(self, observation: "Observation") -> None:
        """Store an observation in memory."""
        pass

    @abstractmethod
    def retrieve(self, query: str | None = None, limit: int | None = None) -> list["Observation"]:
        """Retrieve observations from memory."""
        pass

    @abstractmethod
    def summarize(self) -> str:
        """Create a text summary of memory contents for LLM context."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all stored memories."""
        pass

    @abstractmethod
    def dump(self) -> dict:
        """Dump full memory state for inspection/debugging."""
        pass

    def __len__(self) -> int:
        """Get number of observations in memory."""
        return len(self.retrieve())
