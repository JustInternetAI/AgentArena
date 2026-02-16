"""Debug middleware for observation tracking and visibility change detection.

Provides an ObservationTracker that can be plugged into the SDK server to log
observations and detect gained/lost resources and hazards — the same functionality
as the old standalone observe_inspector tool, but running alongside the agent.
"""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ObservationEntry:
    """A single tracked observation with visibility change analysis."""

    tick: int
    agent_id: str
    timestamp: str
    position: list[float]
    visible_resources: list[str]
    visible_hazards: list[str]
    gained_resources: list[str]
    lost_resources: list[str]
    gained_hazards: list[str]
    lost_hazards: list[str]
    raw_observation: dict[str, Any] = field(repr=False)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            "tick": self.tick,
            "agent_id": self.agent_id,
            "timestamp": self.timestamp,
            "position": self.position,
            "visible_resources": self.visible_resources,
            "visible_hazards": self.visible_hazards,
            "gained_resources": self.gained_resources,
            "lost_resources": self.lost_resources,
            "gained_hazards": self.gained_hazards,
            "lost_hazards": self.lost_hazards,
            "raw_observation": self.raw_observation,
        }

    @property
    def has_changes(self) -> bool:
        """Whether this observation had any visibility changes."""
        return bool(
            self.gained_resources or self.lost_resources or self.gained_hazards or self.lost_hazards
        )


class ObservationTracker:
    """Tracks observations and detects visibility changes per agent.

    Uses a fixed-size ring buffer (deque) for in-memory storage so it
    never grows unbounded.  Thread-safe for concurrent access.
    """

    def __init__(self, max_entries: int = 1000) -> None:
        self._observations: deque[ObservationEntry] = deque(maxlen=max_entries)
        # Per-agent last-seen sets: agent_id -> (resources, hazards)
        self._last_visible: dict[str, tuple[set[str], set[str]]] = {}
        self._lock = threading.Lock()

    def track_observation(self, observation: dict[str, Any]) -> ObservationEntry:
        """Record an observation and compute visibility changes.

        Args:
            observation: Raw observation dict from Godot.

        Returns:
            The created ObservationEntry with change analysis.
        """
        agent_id = observation.get("agent_id", "unknown")
        tick = observation.get("tick", 0)
        position = observation.get("position", [0, 0, 0])

        nearby_resources = observation.get("nearby_resources", [])
        nearby_hazards = observation.get("nearby_hazards", [])

        current_resources = {r.get("name", str(r)) for r in nearby_resources}
        current_hazards = {h.get("name", str(h)) for h in nearby_hazards}

        with self._lock:
            last_resources, last_hazards = self._last_visible.get(agent_id, (set(), set()))

            gained_resources = current_resources - last_resources
            lost_resources = last_resources - current_resources
            gained_hazards = current_hazards - last_hazards
            lost_hazards = last_hazards - current_hazards

            self._last_visible[agent_id] = (current_resources, current_hazards)

            entry = ObservationEntry(
                tick=tick,
                agent_id=agent_id,
                timestamp=datetime.now(tz=timezone.utc).isoformat(),
                position=position,
                visible_resources=sorted(current_resources),
                visible_hazards=sorted(current_hazards),
                gained_resources=sorted(gained_resources),
                lost_resources=sorted(lost_resources),
                gained_hazards=sorted(gained_hazards),
                lost_hazards=sorted(lost_hazards),
                raw_observation=observation,
            )
            self._observations.append(entry)

        return entry

    def get_recent(
        self,
        limit: int = 50,
        agent_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return the most recent observations."""
        with self._lock:
            items = list(self._observations)

        if agent_id:
            items = [o for o in items if o.agent_id == agent_id]

        return [o.to_dict() for o in items[-limit:]]

    def get_changes(
        self,
        limit: int = 50,
        agent_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return only observations where visibility changed."""
        with self._lock:
            items = list(self._observations)

        if agent_id:
            items = [o for o in items if o.agent_id == agent_id]

        changed = [o for o in items if o.has_changes]
        return [o.to_dict() for o in changed[-limit:]]

    def clear(self) -> None:
        """Clear all tracked observations."""
        with self._lock:
            self._observations.clear()
            self._last_visible.clear()
