"""
Sliding Window Memory - Remember Recent Observations

This memory system keeps the N most recent observations in a sliding window.
When full, the oldest observation is removed to make room for new ones.

This is YOUR code - you can see exactly how it works and modify it!
"""

from agent_arena_sdk import Observation


class SlidingWindowMemory:
    """
    Simple FIFO memory that keeps N most recent observations.

    Perfect for:
    - Remembering what you saw recently
    - Tracking patterns over time
    - Planning based on recent history

    Example:
        memory = SlidingWindowMemory(capacity=50)

        # Each tick, store the observation
        memory.store(obs)

        # Later, retrieve recent observations
        last_10 = memory.get_recent(10)

        # Search for specific things
        resources_seen = memory.find_resources_seen()
    """

    def __init__(self, capacity: int = 50):
        """
        Initialize memory.

        Args:
            capacity: Maximum number of observations to remember
        """
        if capacity < 1:
            raise ValueError("Capacity must be at least 1")

        self.capacity = capacity
        self._observations: list[Observation] = []

    def store(self, observation: Observation) -> None:
        """
        Store an observation in memory.

        Args:
            observation: The observation to store
        """
        self._observations.append(observation)

        # Remove oldest if we exceed capacity
        if len(self._observations) > self.capacity:
            self._observations.pop(0)

    def get_recent(self, n: int = 10) -> list[Observation]:
        """
        Get the N most recent observations.

        Args:
            n: Number of recent observations to return

        Returns:
            List of observations, most recent first
        """
        return list(reversed(self._observations[-n:]))

    def get_all(self) -> list[Observation]:
        """
        Get all stored observations.

        Returns:
            List of all observations, oldest first
        """
        return self._observations.copy()

    def find_resources_seen(self) -> list[tuple[str, tuple[float, float, float], int]]:
        """
        Find all unique resources seen in memory.

        Returns:
            List of (resource_name, last_position, tick_last_seen)
        """
        resources_map: dict[str, tuple[tuple[float, float, float], int]] = {}

        for obs in self._observations:
            for resource in obs.nearby_resources:
                # Update to most recent position/tick
                resources_map[resource.name] = (resource.position, obs.tick)

        return [(name, pos, tick) for name, (pos, tick) in resources_map.items()]

    def find_hazards_seen(self) -> list[tuple[str, tuple[float, float, float], int]]:
        """
        Find all unique hazards seen in memory.

        Returns:
            List of (hazard_name, last_position, tick_last_seen)
        """
        hazards_map: dict[str, tuple[tuple[float, float, float], int]] = {}

        for obs in self._observations:
            for hazard in obs.nearby_hazards:
                hazards_map[hazard.name] = (hazard.position, obs.tick)

        return [(name, pos, tick) for name, (pos, tick) in hazards_map.items()]

    def count_observations(self) -> int:
        """
        Count how many observations are stored.

        Returns:
            Number of observations in memory
        """
        return len(self._observations)

    def is_full(self) -> bool:
        """
        Check if memory is at capacity.

        Returns:
            True if memory is full
        """
        return len(self._observations) >= self.capacity

    def clear(self) -> None:
        """
        Clear all stored observations.

        Useful when starting a new episode.
        """
        self._observations.clear()

    def summarize(self) -> str:
        """
        Create a text summary of what's in memory.

        Useful for debugging or LLM context.

        Returns:
            Human-readable summary
        """
        if not self._observations:
            return "Memory is empty."

        lines = [f"Memory: {len(self._observations)} observations"]

        # Summarize resources seen
        resources = self.find_resources_seen()
        if resources:
            lines.append(f"\nResources seen: {len(resources)}")
            for name, pos, tick in resources[:5]:
                lines.append(f"  - {name} at {pos} (tick {tick})")

        # Summarize hazards seen
        hazards = self.find_hazards_seen()
        if hazards:
            lines.append(f"\nHazards seen: {len(hazards)}")
            for name, pos, tick in hazards[:5]:
                lines.append(f"  - {name} at {pos} (tick {tick})")

        return "\n".join(lines)
