"""
Sliding window memory implementation.
"""

from typing import TYPE_CHECKING

from .base import AgentMemory

if TYPE_CHECKING:
    from ..schemas import Observation


class SlidingWindowMemory(AgentMemory):
    """
    Simple FIFO memory keeping N most recent observations.

    When capacity is reached, oldest observations are discarded.
    """

    def __init__(self, capacity: int = 10):
        if capacity < 1:
            raise ValueError("Capacity must be at least 1")

        self.capacity = capacity
        self._observations: list[Observation] = []

    def store(self, observation: "Observation") -> None:
        """Store an observation in memory."""
        self._observations.append(observation)
        if len(self._observations) > self.capacity:
            self._observations = self._observations[-self.capacity :]

    def retrieve(self, query: str | None = None, limit: int | None = None) -> list["Observation"]:
        """Retrieve observations (most recent first)."""
        if limit is None:
            return list(reversed(self._observations))
        else:
            return list(reversed(self._observations[-limit:]))

    def summarize(self) -> str:
        """Create a text summary of memory contents."""
        if not self._observations:
            return "No observations in memory."

        lines = [f"Memory (last {len(self._observations)} observations):"]
        for obs in reversed(self._observations):
            lines.append(f"\n[Tick {obs.tick}]")
            lines.append(f"  Position: {obs.position}")
            if obs.nearby_resources:
                lines.append(f"  Nearby resources: {len(obs.nearby_resources)}")
            if obs.nearby_hazards:
                lines.append(f"  Nearby hazards: {len(obs.nearby_hazards)}")
            lines.append(f"  Health: {obs.health:.0f}, Energy: {obs.energy:.0f}")
        return "\n".join(lines)

    def clear(self) -> None:
        """Clear all stored memories."""
        self._observations.clear()

    def dump(self) -> dict:
        """Dump full memory state for inspection/debugging."""
        return {
            "type": "SlidingWindowMemory",
            "stats": {
                "observation_count": len(self._observations),
                "capacity": self.capacity,
            },
            "observations": [obs.to_dict() for obs in self._observations],
        }

    def __len__(self) -> int:
        return len(self._observations)
