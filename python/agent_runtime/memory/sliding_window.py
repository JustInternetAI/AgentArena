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

    This is the simplest memory implementation, suitable for:
    - Beginners learning agent programming
    - Short episodes where all context fits in memory
    - Scenarios with limited state complexity

    When capacity is reached, oldest observations are discarded.

    Example:
        memory = SlidingWindowMemory(capacity=10)

        # Store observations
        for obs in observations:
            memory.store(obs)

        # Get recent context
        context = memory.summarize()

        # Retrieve specific observations
        recent_5 = memory.retrieve(limit=5)
    """

    def __init__(self, capacity: int = 10):
        """
        Initialize sliding window memory.

        Args:
            capacity: Maximum number of observations to keep
        """
        if capacity < 1:
            raise ValueError("Capacity must be at least 1")

        self.capacity = capacity
        self._observations: list[Observation] = []

    def store(self, observation: "Observation") -> None:
        """
        Store an observation in memory.

        Args:
            observation: The observation to store
        """
        self._observations.append(observation)

        # Enforce capacity limit
        if len(self._observations) > self.capacity:
            self._observations = self._observations[-self.capacity :]

    def retrieve(self, query: str | None = None, limit: int | None = None) -> list["Observation"]:
        """
        Retrieve observations from memory.

        Note: query parameter is ignored in SlidingWindowMemory (returns most recent).

        Args:
            query: Ignored (kept for interface compatibility)
            limit: Maximum number of observations to return (most recent)

        Returns:
            List of observations, most recent first
        """
        if limit is None:
            return list(reversed(self._observations))
        else:
            return list(reversed(self._observations[-limit:]))

    def summarize(self) -> str:
        """
        Create a text summary of memory contents for LLM context.

        Returns:
            String with recent observations formatted for LLM
        """
        if not self._observations:
            return "No observations in memory."

        lines = [f"Memory (last {len(self._observations)} observations):"]

        for i, obs in enumerate(reversed(self._observations), 1):
            lines.append(f"\n[Tick {obs.tick}]")
            lines.append(f"  Position: {obs.position}")

            if obs.visible_entities:
                lines.append(f"  Visible entities: {len(obs.visible_entities)}")
                for entity in obs.visible_entities[:3]:  # Show first 3
                    lines.append(
                        f"    - {entity.type} '{entity.id}' at distance {entity.distance:.1f}"
                    )
                if len(obs.visible_entities) > 3:
                    lines.append(f"    ... and {len(obs.visible_entities) - 3} more")

            if obs.nearby_resources:
                lines.append(f"  Nearby resources: {len(obs.nearby_resources)}")
                for resource in obs.nearby_resources[:3]:
                    lines.append(
                        f"    - {resource.name} ({resource.type}) at distance {resource.distance:.1f}"
                    )
                if len(obs.nearby_resources) > 3:
                    lines.append(f"    ... and {len(obs.nearby_resources) - 3} more")

            if obs.nearby_hazards:
                lines.append(f"  Nearby hazards: {len(obs.nearby_hazards)}")
                for hazard in obs.nearby_hazards[:3]:
                    lines.append(
                        f"    - {hazard.name} ({hazard.type}) at distance {hazard.distance:.1f}, damage: {hazard.damage}"
                    )

            if obs.inventory:
                items_str = ", ".join(f"{item.name}x{item.quantity}" for item in obs.inventory)
                lines.append(f"  Inventory: {items_str}")

            lines.append(f"  Health: {obs.health:.0f}, Energy: {obs.energy:.0f}")

        return "\n".join(lines)

    def clear(self) -> None:
        """
        Clear all stored memories.
        """
        self._observations.clear()

    def __len__(self) -> int:
        """
        Get number of observations in memory.

        Returns:
            Count of stored observations
        """
        return len(self._observations)
