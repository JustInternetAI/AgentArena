"""
Sliding Window Memory - Remember Recent Observations

This memory system keeps the N most recent observations in a sliding window.
When full, the oldest observation is removed to make room for new ones.

On top of the raw FIFO buffer, it tracks:
- Which resources have been collected (so you don't walk back to empty spots)
- Where resources tend to cluster ("productive areas")
- Hazard zones to avoid

This is YOUR code - you can see exactly how it works and modify it!
"""

import math
from agent_arena_sdk import Observation


class SlidingWindowMemory:
    """
    FIFO memory with spatial tracking and pattern detection.

    Perfect for:
    - Remembering what you saw recently
    - Tracking patterns over time (resource clusters, hazard zones)
    - Planning based on recent history
    - Avoiding areas you've already cleared

    Example:
        memory = SlidingWindowMemory(capacity=50)

        # Store each observation
        memory.store(obs)

        # Find things you've seen (filtered by recency and collection status)
        uncollected = memory.find_uncollected_resources(current_tick=10)
        hazard_zones = memory.find_hazard_zones(current_tick=10)

        # Pattern detection: where do resources tend to appear?
        productive = memory.find_productive_areas()
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
        self._collected: set[str] = set()  # Names of resources we picked up

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

    def mark_collected(self, resource_name: str) -> None:
        """
        Mark a resource as collected so we don't path back to it.

        Args:
            resource_name: Name of the collected resource
        """
        self._collected.add(resource_name)

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

    def find_uncollected_resources(
        self, current_tick: int, recency: int = 40
    ) -> list[tuple[str, tuple[float, float, float], int]]:
        """
        Find resources seen recently that we haven't collected yet.

        Args:
            current_tick: The current simulation tick
            recency: Only include resources seen within this many ticks

        Returns:
            List of (resource_name, position, tick_last_seen), nearest-tick first
        """
        all_resources = self.find_resources_seen()
        result = [
            (name, pos, tick)
            for name, pos, tick in all_resources
            if name not in self._collected and current_tick - tick < recency
        ]
        # Sort by most recently seen (most likely still there)
        result.sort(key=lambda r: r[2], reverse=True)
        return result

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

    def find_hazard_zones(
        self, current_tick: int, recency: int = 30
    ) -> list[tuple[str, tuple[float, float, float]]]:
        """
        Find hazard positions that were seen recently (likely still active).

        Args:
            current_tick: The current simulation tick
            recency: Only include hazards seen within this many ticks

        Returns:
            List of (hazard_name, position)
        """
        return [
            (name, pos)
            for name, pos, tick in self.find_hazards_seen()
            if current_tick - tick < recency
        ]

    def find_productive_areas(self) -> list[tuple[float, float, float]]:
        """
        Detect where resources tend to cluster. Returns centroid positions
        of areas where multiple resources were observed.

        This is a simple pattern detection example: "resources appear near
        this area, so explore there when nothing is visible."

        Returns:
            List of (x, y, z) centroids, best area first
        """
        # Collect all resource positions ever seen
        resource_positions: list[tuple[float, float, float]] = []
        for obs in self._observations:
            for resource in obs.nearby_resources:
                resource_positions.append(resource.position)

        if len(resource_positions) < 2:
            return []

        # Simple clustering: group positions within 8 units of each other
        clusters: list[list[tuple[float, float, float]]] = []
        assigned = [False] * len(resource_positions)

        for i, pos in enumerate(resource_positions):
            if assigned[i]:
                continue
            cluster = [pos]
            assigned[i] = True
            for j in range(i + 1, len(resource_positions)):
                if assigned[j]:
                    continue
                if _distance(pos, resource_positions[j]) < 8.0:
                    cluster.append(resource_positions[j])
                    assigned[j] = True
            if len(cluster) >= 2:
                clusters.append(cluster)

        # Return centroids, largest cluster first
        clusters.sort(key=len, reverse=True)
        return [_centroid(c) for c in clusters]

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
        Clear all stored observations and collection tracking.

        Useful when starting a new episode.
        """
        self._observations.clear()
        self._collected.clear()

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
            uncollected = [r for r in resources if r[0] not in self._collected]
            lines.append(
                f"\nResources seen: {len(resources)} "
                f"({len(uncollected)} uncollected, {len(self._collected)} collected)"
            )
            for name, pos, tick in resources[:5]:
                status = "collected" if name in self._collected else "available"
                lines.append(f"  - {name} at {pos} (tick {tick}, {status})")

        # Summarize hazards seen
        hazards = self.find_hazards_seen()
        if hazards:
            lines.append(f"\nHazards seen: {len(hazards)}")
            for name, pos, tick in hazards[:5]:
                lines.append(f"  - {name} at {pos} (tick {tick})")

        # Summarize productive areas
        areas = self.find_productive_areas()
        if areas:
            lines.append(f"\nProductive areas: {len(areas)}")
            for pos in areas[:3]:
                lines.append(f"  - near ({pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f})")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------


def _distance(
    pos1: tuple[float, float, float], pos2: tuple[float, float, float]
) -> float:
    return math.sqrt(
        (pos1[0] - pos2[0]) ** 2
        + (pos1[1] - pos2[1]) ** 2
        + (pos1[2] - pos2[2]) ** 2
    )


def _centroid(
    positions: list[tuple[float, float, float]],
) -> tuple[float, float, float]:
    n = len(positions)
    return (
        sum(p[0] for p in positions) / n,
        sum(p[1] for p in positions) / n,
        sum(p[2] for p in positions) / n,
    )
