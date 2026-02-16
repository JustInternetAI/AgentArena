"""Prompt Inspector - Captures and stores LLM request/response data for debugging.

This module provides tools to inspect what prompts are sent to LLMs and what
responses are received, enabling developers to debug agent decision-making.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class InspectorStage(str, Enum):
    """Stages in the LLM decision pipeline."""

    OBSERVATION = "observation"
    PROMPT_BUILDING = "prompt_building"
    LLM_REQUEST = "llm_request"
    LLM_RESPONSE = "llm_response"
    DECISION = "decision"


@dataclass
class InspectorEntry:
    """A single captured entry in the decision pipeline."""

    timestamp: str
    agent_id: str
    tick: int
    stage: InspectorStage
    data: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp,
            "agent_id": self.agent_id,
            "tick": self.tick,
            "stage": self.stage,
            "data": self.data,
        }


@dataclass
class DecisionCapture:
    """Complete capture of a single agent decision cycle."""

    agent_id: str
    tick: int
    start_time: str
    entries: list[InspectorEntry] = field(default_factory=list)

    def add_entry(self, stage: InspectorStage, data: dict[str, Any]) -> None:
        """Add an entry to this decision capture."""
        entry = InspectorEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            agent_id=self.agent_id,
            tick=self.tick,
            stage=stage,
            data=data,
        )
        self.entries.append(entry)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "agent_id": self.agent_id,
            "tick": self.tick,
            "start_time": self.start_time,
            "entries": [entry.to_dict() for entry in self.entries],
        }


class PromptInspector:
    """Captures and stores LLM request/response data for debugging."""

    def __init__(
        self,
        enabled: bool = True,
        max_entries: int = 1000,
        log_to_file: bool = False,
        log_dir: Path | None = None,
    ):
        """Initialize the Prompt Inspector.

        Args:
            enabled: Whether to capture data (can be toggled for performance)
            max_entries: Maximum number of decision captures to keep in memory
            log_to_file: Whether to write captures to disk
            log_dir: Directory for log files (default: ./logs/inspector)
        """
        self.enabled = enabled
        self.max_entries = max_entries
        self.log_to_file = log_to_file
        self.log_dir = log_dir or Path("logs/inspector")

        # In-memory storage: key is (agent_id, tick)
        self.captures: dict[tuple[str, int], DecisionCapture] = {}

        if self.log_to_file:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Prompt Inspector logging to {self.log_dir}")

    def start_capture(self, agent_id: str, tick: int) -> DecisionCapture | None:
        """Start capturing a new decision cycle.

        Args:
            agent_id: ID of the agent making the decision
            tick: Current simulation tick

        Returns:
            DecisionCapture object to add entries to, or None if disabled
        """
        if not self.enabled:
            return None

        capture = DecisionCapture(
            agent_id=agent_id, tick=tick, start_time=datetime.utcnow().isoformat() + "Z"
        )

        key = (agent_id, tick)
        self.captures[key] = capture

        # Enforce max entries limit (FIFO)
        if len(self.captures) > self.max_entries:
            # Remove oldest entry
            oldest_key = min(self.captures.keys(), key=lambda k: k[1])
            del self.captures[oldest_key]

        return capture

    def finish_capture(self, agent_id: str, tick: int) -> None:
        """Finish capturing a decision cycle and optionally write to file.

        Args:
            agent_id: ID of the agent
            tick: Current simulation tick
        """
        if not self.enabled:
            return

        key = (agent_id, tick)
        capture = self.captures.get(key)

        if not capture:
            logger.warning(f"No capture found for agent {agent_id} tick {tick}")
            return

        if self.log_to_file:
            self._write_to_file(capture)

    def _write_to_file(self, capture: DecisionCapture) -> None:
        """Write a capture to a JSON file.

        Args:
            capture: The decision capture to write
        """
        try:
            filename = f"{capture.agent_id}_tick_{capture.tick:06d}.json"
            filepath = self.log_dir / filename

            with open(filepath, "w") as f:
                json.dump(capture.to_dict(), f, indent=2)

            logger.debug(f"Wrote capture to {filepath}")
        except Exception as e:
            logger.error(f"Failed to write capture to file: {e}")

    def get_capture(self, agent_id: str, tick: int) -> DecisionCapture | None:
        """Retrieve a specific decision capture.

        Args:
            agent_id: ID of the agent
            tick: Simulation tick

        Returns:
            DecisionCapture if found, None otherwise
        """
        return self.captures.get((agent_id, tick))

    def get_captures_for_agent(
        self, agent_id: str, tick_start: int | None = None, tick_end: int | None = None
    ) -> list[DecisionCapture]:
        """Get all captures for a specific agent, optionally filtered by tick range.

        Args:
            agent_id: ID of the agent
            tick_start: Optional minimum tick (inclusive)
            tick_end: Optional maximum tick (inclusive)

        Returns:
            List of DecisionCapture objects, sorted by tick
        """
        captures = [
            capture
            for (aid, tick), capture in self.captures.items()
            if aid == agent_id
            and (tick_start is None or tick >= tick_start)
            and (tick_end is None or tick <= tick_end)
        ]
        return sorted(captures, key=lambda c: c.tick)

    def get_all_captures(
        self, tick_start: int | None = None, tick_end: int | None = None
    ) -> list[DecisionCapture]:
        """Get all captures, optionally filtered by tick range.

        Args:
            tick_start: Optional minimum tick (inclusive)
            tick_end: Optional maximum tick (inclusive)

        Returns:
            List of DecisionCapture objects, sorted by (tick, agent_id)
        """
        captures = [
            capture
            for (aid, tick), capture in self.captures.items()
            if (tick_start is None or tick >= tick_start) and (tick_end is None or tick <= tick_end)
        ]
        return sorted(captures, key=lambda c: (c.tick, c.agent_id))

    def clear(self) -> None:
        """Clear all in-memory captures."""
        self.captures.clear()
        logger.info("Cleared all prompt inspector captures")

    def to_json(self, agent_id: str | None = None, tick: int | None = None) -> str:
        """Export captures as JSON string.

        Args:
            agent_id: Optional filter by agent ID
            tick: Optional filter by specific tick

        Returns:
            JSON string of captures
        """
        if agent_id and tick is not None:
            capture = self.get_capture(agent_id, tick)
            data = [capture.to_dict()] if capture else []
        elif agent_id:
            captures = self.get_captures_for_agent(agent_id)
            data = [c.to_dict() for c in captures]
        else:
            captures = self.get_all_captures()
            data = [c.to_dict() for c in captures]

        return json.dumps(data, indent=2)


# Global singleton instance
_global_inspector: PromptInspector | None = None


def get_global_inspector() -> PromptInspector:
    """Get or create the global PromptInspector instance.

    Returns:
        The global PromptInspector instance
    """
    global _global_inspector
    if _global_inspector is None:
        _global_inspector = PromptInspector()
    return _global_inspector


def set_global_inspector(inspector: PromptInspector) -> None:
    """Set the global PromptInspector instance.

    Args:
        inspector: The inspector instance to use globally
    """
    global _global_inspector
    _global_inspector = inspector
