"""Reasoning Trace System - Captures agent decision-making steps for debugging.

This module provides the trace infrastructure for understanding how agents make
decisions, from observation through LLM interaction to final action selection.

Aligned with issue #45 (Tier 3 Reasoning Trace System) and supports #31 (Prompt Inspector UI).
"""

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from io import TextIOWrapper
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class TraceStepName(str, Enum):
    """Standard step names in the decision pipeline."""

    OBSERVATION = "observation"
    RETRIEVED = "retrieved"  # Memory retrieval (if using RAG/long-term memory)
    PROMPT_BUILDING = "prompt"
    LLM_REQUEST = "llm_request"
    LLM_RESPONSE = "response"
    DECISION = "decision"


@dataclass
class TraceStep:
    """A single step in the reasoning trace."""

    timestamp: str
    agent_id: str
    tick: int
    name: str  # TraceStepName or custom string
    data: dict[str, Any]
    duration_ms: float | None = None  # Optional: duration of this step

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "timestamp": self.timestamp,
            "agent_id": self.agent_id,
            "tick": self.tick,
            "name": self.name,
            "data": self.data,
        }
        if self.duration_ms is not None:
            result["duration_ms"] = self.duration_ms
        return result


@dataclass
class ReasoningTrace:
    """Complete trace of a single agent decision cycle.

    Replaces the previous DecisionCapture class.
    """

    agent_id: str
    tick: int
    episode_id: str  # NEW: Track which episode this trace belongs to
    start_time: str
    steps: list[TraceStep] = field(default_factory=list)

    def add_step(self, name: str, data: dict[str, Any], duration_ms: float | None = None) -> None:
        """Add a step to this reasoning trace.

        Args:
            name: Step name (use TraceStepName enum or custom string)
            data: Arbitrary data for this step
            duration_ms: Optional duration in milliseconds
        """
        step = TraceStep(
            timestamp=datetime.utcnow().isoformat() + "Z",
            agent_id=self.agent_id,
            tick=self.tick,
            name=name,
            data=data,
            duration_ms=duration_ms,
        )
        self.steps.append(step)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "agent_id": self.agent_id,
            "tick": self.tick,
            "episode_id": self.episode_id,
            "start_time": self.start_time,
            "steps": [step.to_dict() for step in self.steps],
        }

    def to_jsonl(self) -> str:
        """Convert to single-line JSON for JSONL format."""
        return json.dumps(self.to_dict())


class TraceStore:
    """Stores and manages reasoning traces with episode-based JSONL persistence.

    Replaces the previous PromptInspector class.
    Implements the TraceStore from issue #45.
    """

    def __init__(
        self,
        enabled: bool = True,
        max_entries: int = 1000,
        log_to_file: bool = False,
        log_dir: Path | None = None,
        episode_id: str | None = None,
    ):
        """Initialize the Trace Store.

        Args:
            enabled: Whether to capture traces (can be toggled for performance)
            max_entries: Maximum number of traces to keep in memory
            log_to_file: Whether to write traces to disk (JSONL format)
            log_dir: Directory for trace files (default: ./logs/traces)
            episode_id: Current episode ID (auto-generated if not provided)
        """
        self.enabled = enabled
        self.max_entries = max_entries
        self.log_to_file = log_to_file
        self.log_dir = log_dir or Path("logs/traces")

        # In-memory storage: key is (agent_id, tick)
        self.traces: dict[tuple[str, int], ReasoningTrace] = {}

        # Episode management
        self.episode_id = episode_id or self._generate_episode_id()
        self.episode_file: Path | None = None
        self.episode_file_handle: TextIOWrapper | None = None

        # Watch callbacks for real-time streaming
        self._watchers: dict[str, list[Callable[[ReasoningTrace], None]]] = {}

        if self.log_to_file:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            self._open_episode_file()
            logger.info(f"TraceStore logging to {self.log_dir} (episode: {self.episode_id})")

    def _generate_episode_id(self) -> str:
        """Generate a unique episode ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return f"ep_{timestamp}"

    def _open_episode_file(self) -> None:
        """Open JSONL file for the current episode (append mode)."""
        if not self.log_to_file:
            return

        self.episode_file = self.log_dir / f"{self.episode_id}.jsonl"
        try:
            # Open in append mode for incremental writes
            self.episode_file_handle = open(self.episode_file, "a", encoding="utf-8")
            logger.debug(f"Opened episode file: {self.episode_file}")
        except Exception as e:
            logger.error(f"Failed to open episode file: {e}")
            self.episode_file_handle = None

    def start_episode(self, episode_id: str) -> None:
        """Start a new episode.

        Args:
            episode_id: Unique identifier for this episode
        """
        # Close current episode file if open
        if self.episode_file_handle:
            self.episode_file_handle.close()
            self.episode_file_handle = None

        self.episode_id = episode_id

        if self.log_to_file:
            self._open_episode_file()

        logger.info(f"Started new episode: {episode_id}")

    def end_episode(self) -> None:
        """End the current episode and close the file."""
        if self.episode_file_handle:
            self.episode_file_handle.close()
            self.episode_file_handle = None
            logger.info(f"Ended episode: {self.episode_id}")

    def start_capture(self, agent_id: str, tick: int) -> ReasoningTrace | None:
        """Start capturing a new reasoning trace.

        Args:
            agent_id: ID of the agent making the decision
            tick: Current simulation tick

        Returns:
            ReasoningTrace object to add steps to, or None if disabled
        """
        if not self.enabled:
            return None

        trace = ReasoningTrace(
            agent_id=agent_id,
            tick=tick,
            episode_id=self.episode_id,
            start_time=datetime.utcnow().isoformat() + "Z",
        )

        key = (agent_id, tick)
        self.traces[key] = trace

        # Enforce max entries limit (FIFO)
        if len(self.traces) > self.max_entries:
            # Remove oldest entry
            oldest_key = min(self.traces.keys(), key=lambda k: k[1])
            del self.traces[oldest_key]

        return trace

    def finish_capture(self, agent_id: str, tick: int) -> None:
        """Finish capturing a reasoning trace and trigger file write + watchers.

        Args:
            agent_id: ID of the agent
            tick: Current simulation tick
        """
        if not self.enabled:
            return

        key = (agent_id, tick)
        trace = self.traces.get(key)

        if not trace:
            logger.warning(f"No trace found for agent {agent_id} tick {tick}")
            return

        # Write to JSONL file
        if self.log_to_file:
            self._write_to_jsonl(trace)

        # Notify watchers
        self._notify_watchers(agent_id, trace)

    def _write_to_jsonl(self, trace: ReasoningTrace) -> None:
        """Append trace to episode JSONL file.

        Args:
            trace: The reasoning trace to write
        """
        if not self.episode_file_handle:
            logger.warning("Episode file not open, skipping write")
            return

        try:
            # Write as single-line JSON
            self.episode_file_handle.write(trace.to_jsonl() + "\n")
            self.episode_file_handle.flush()  # Ensure it's written immediately
            logger.debug(f"Wrote trace to {self.episode_file}")
        except Exception as e:
            logger.error(f"Failed to write trace to JSONL: {e}")

    def watch(self, agent_id: str, callback: Callable[[ReasoningTrace], None]) -> None:
        """Subscribe to real-time trace updates for an agent.

        Args:
            agent_id: Agent ID to watch, or "*" for all agents
            callback: Function called when a trace is completed
        """
        if agent_id not in self._watchers:
            self._watchers[agent_id] = []
        self._watchers[agent_id].append(callback)
        logger.info(f"Added watcher for agent: {agent_id}")

    def unwatch(self, agent_id: str, callback: Callable[[ReasoningTrace], None]) -> None:
        """Unsubscribe from trace updates.

        Args:
            agent_id: Agent ID that was being watched
            callback: The callback function to remove
        """
        if agent_id in self._watchers:
            self._watchers[agent_id].remove(callback)
            if not self._watchers[agent_id]:
                del self._watchers[agent_id]

    def _notify_watchers(self, agent_id: str, trace: ReasoningTrace) -> None:
        """Notify all watchers that a trace is complete.

        Args:
            agent_id: Agent ID that completed the trace
            trace: The completed trace
        """
        # Notify agent-specific watchers
        for callback in self._watchers.get(agent_id, []):
            try:
                callback(trace)
            except Exception as e:
                logger.error(f"Error in trace watcher callback: {e}")

        # Notify wildcard watchers
        for callback in self._watchers.get("*", []):
            try:
                callback(trace)
            except Exception as e:
                logger.error(f"Error in wildcard trace watcher callback: {e}")

    def get_capture(self, agent_id: str, tick: int) -> ReasoningTrace | None:
        """Retrieve a specific reasoning trace.

        Args:
            agent_id: ID of the agent
            tick: Simulation tick

        Returns:
            ReasoningTrace if found, None otherwise
        """
        return self.traces.get((agent_id, tick))

    def get_captures_for_agent(
        self, agent_id: str, tick_start: int | None = None, tick_end: int | None = None
    ) -> list[ReasoningTrace]:
        """Get all traces for a specific agent, optionally filtered by tick range.

        Args:
            agent_id: ID of the agent
            tick_start: Optional minimum tick (inclusive)
            tick_end: Optional maximum tick (inclusive)

        Returns:
            List of ReasoningTrace objects, sorted by tick
        """
        traces = [
            trace
            for (aid, tick), trace in self.traces.items()
            if aid == agent_id
            and (tick_start is None or tick >= tick_start)
            and (tick_end is None or tick <= tick_end)
        ]
        return sorted(traces, key=lambda t: t.tick)

    def get_all_captures(
        self, tick_start: int | None = None, tick_end: int | None = None
    ) -> list[ReasoningTrace]:
        """Get all traces, optionally filtered by tick range.

        Args:
            tick_start: Optional minimum tick (inclusive)
            tick_end: Optional maximum tick (inclusive)

        Returns:
            List of ReasoningTrace objects, sorted by (tick, agent_id)
        """
        traces = [
            trace
            for (aid, tick), trace in self.traces.items()
            if (tick_start is None or tick >= tick_start) and (tick_end is None or tick <= tick_end)
        ]
        return sorted(traces, key=lambda t: (t.tick, t.agent_id))

    def get_episode_traces(self, episode_id: str) -> list[ReasoningTrace]:
        """Get all traces for a specific episode.

        This reads from the JSONL file on disk.

        Args:
            episode_id: Episode ID to retrieve

        Returns:
            List of ReasoningTrace objects from that episode
        """
        episode_file = self.log_dir / f"{episode_id}.jsonl"

        if not episode_file.exists():
            logger.warning(f"Episode file not found: {episode_file}")
            return []

        traces = []
        try:
            with open(episode_file, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        # Reconstruct ReasoningTrace from dict
                        trace = ReasoningTrace(
                            agent_id=data["agent_id"],
                            tick=data["tick"],
                            episode_id=data["episode_id"],
                            start_time=data["start_time"],
                            steps=[],
                        )
                        # Reconstruct steps
                        for step_data in data.get("steps", []):
                            step = TraceStep(
                                timestamp=step_data["timestamp"],
                                agent_id=step_data["agent_id"],
                                tick=step_data["tick"],
                                name=step_data["name"],
                                data=step_data["data"],
                                duration_ms=step_data.get("duration_ms"),
                            )
                            trace.steps.append(step)
                        traces.append(trace)
        except Exception as e:
            logger.error(f"Failed to read episode traces: {e}")

        return sorted(traces, key=lambda t: (t.tick, t.agent_id))

    def clear(self) -> None:
        """Clear all in-memory traces."""
        self.traces.clear()
        logger.info("Cleared all reasoning traces from memory")

    def to_json(self, agent_id: str | None = None, tick: int | None = None) -> str:
        """Export traces as JSON string.

        Args:
            agent_id: Optional filter by agent ID
            tick: Optional filter by specific tick

        Returns:
            JSON string of traces
        """
        if agent_id and tick is not None:
            trace = self.get_capture(agent_id, tick)
            data = [trace.to_dict()] if trace else []
        elif agent_id:
            traces = self.get_captures_for_agent(agent_id)
            data = [t.to_dict() for t in traces]
        else:
            traces = self.get_all_captures()
            data = [t.to_dict() for t in traces]

        return json.dumps(data, indent=2)

    def __del__(self):
        """Cleanup: close episode file on destruction."""
        if self.episode_file_handle:
            self.episode_file_handle.close()


# Global singleton instance
_global_trace_store: TraceStore | None = None


def get_global_trace_store() -> TraceStore:
    """Get or create the global TraceStore instance.

    Returns:
        The global TraceStore instance
    """
    global _global_trace_store
    if _global_trace_store is None:
        _global_trace_store = TraceStore()
    return _global_trace_store


def set_global_trace_store(store: TraceStore) -> None:
    """Set the global TraceStore instance.

    Args:
        store: The trace store instance to use globally
    """
    global _global_trace_store
    _global_trace_store = store


# Backwards compatibility aliases
PromptInspector = TraceStore
DecisionCapture = ReasoningTrace
InspectorEntry = TraceStep
InspectorStage = TraceStepName
get_global_inspector = get_global_trace_store
set_global_inspector = set_global_trace_store
