"""Reasoning trace system for debugging agent decisions.

This module provides tools for logging, storing, and inspecting the step-by-step
reasoning process of agents. Each decision can be traced through multiple steps
(observation, memory retrieval, prompt building, LLM response, parsing, etc.).

Example usage:
    class MyAgent(LLMAgentBehavior):
        def decide(self, observation, tools):
            relevant = self.memory.query(observation, k=5)
            self.log_step("retrieved", relevant)

            prompt = self.build_prompt(observation, tools, relevant)
            self.log_step("prompt", prompt)

            response = self.complete(prompt)
            self.log_step("response", response)

            decision = self.parse_response(response, tools)
            self.log_step("decision", decision)

            return decision
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _get_default_traces_dir() -> Path:
    """Get the default traces directory."""
    # Use AGENT_ARENA_TRACES_DIR env var if set, otherwise ~/.agent_arena/traces
    env_dir = os.environ.get("AGENT_ARENA_TRACES_DIR")
    if env_dir:
        return Path(env_dir)
    return Path.home() / ".agent_arena" / "traces"


@dataclass
class TraceStep:
    """A single step in a reasoning trace.

    Attributes:
        name: The name of the step (e.g., "observation", "prompt", "response", "decision")
        data: The data associated with this step (any JSON-serializable value)
        timestamp: Unix timestamp when this step was logged
        elapsed_ms: Milliseconds since the trace started (for timing analysis)
    """

    name: str
    data: Any
    timestamp: float = field(default_factory=time.time)
    elapsed_ms: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "data": self._serialize_data(self.data),
            "timestamp": self.timestamp,
            "elapsed_ms": self.elapsed_ms,
        }

    @classmethod
    def from_dict(cls, data: dict) -> TraceStep:
        """Create from dictionary."""
        return cls(
            name=data["name"],
            data=data["data"],
            timestamp=data.get("timestamp", time.time()),
            elapsed_ms=data.get("elapsed_ms", 0.0),
        )

    def _serialize_data(self, data: Any) -> Any:
        """Serialize data to JSON-compatible format."""
        if data is None:
            return None
        if isinstance(data, str | int | float | bool):
            return data
        if isinstance(data, list | tuple):
            return [self._serialize_data(item) for item in data]
        if isinstance(data, dict):
            return {str(k): self._serialize_data(v) for k, v in data.items()}
        if hasattr(data, "to_dict"):
            return data.to_dict()
        if hasattr(data, "__dict__"):
            return {
                k: self._serialize_data(v)
                for k, v in data.__dict__.items()
                if not k.startswith("_")
            }
        # Fallback to string representation
        return str(data)


@dataclass
class ReasoningTrace:
    """A complete reasoning trace for one agent decision.

    Attributes:
        agent_id: The ID of the agent that made this decision
        tick: The simulation tick when this decision was made
        episode_id: The ID of the current episode
        steps: List of trace steps in order
        trace_id: Unique identifier for this trace
        start_time: Unix timestamp when the trace started
    """

    agent_id: str
    tick: int
    episode_id: str
    steps: list[TraceStep] = field(default_factory=list)
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    start_time: float = field(default_factory=time.time)

    def add_step(self, name: str, data: Any) -> TraceStep:
        """Add a step to this trace.

        Args:
            name: The name of the step
            data: The data to log

        Returns:
            The created TraceStep
        """
        now = time.time()
        elapsed_ms = (now - self.start_time) * 1000
        step = TraceStep(name=name, data=data, timestamp=now, elapsed_ms=elapsed_ms)
        self.steps.append(step)
        return step

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "agent_id": self.agent_id,
            "tick": self.tick,
            "episode_id": self.episode_id,
            "trace_id": self.trace_id,
            "start_time": self.start_time,
            "steps": [step.to_dict() for step in self.steps],
        }

    @classmethod
    def from_dict(cls, data: dict) -> ReasoningTrace:
        """Create from dictionary."""
        trace = cls(
            agent_id=data["agent_id"],
            tick=data["tick"],
            episode_id=data["episode_id"],
            trace_id=data.get("trace_id", str(uuid.uuid4())[:8]),
            start_time=data.get("start_time", time.time()),
        )
        trace.steps = [TraceStep.from_dict(s) for s in data.get("steps", [])]
        return trace

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> ReasoningTrace:
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def format_tree(self, max_data_length: int = 100, use_ascii: bool = True) -> str:
        """Format this trace as a tree view for display.

        Args:
            max_data_length: Maximum length for data preview
            use_ascii: Use ASCII characters for tree (default True for Windows compatibility)

        Returns:
            Formatted string with tree structure
        """
        # Use ASCII or Unicode box-drawing characters
        if use_ascii:
            branch = "+--"
            last_branch = "+--"
            pipe = "|   "
            space = "    "
            child_branch = "+--"
        else:
            branch = "\u251c\u2500\u2500"  # ├──
            last_branch = "\u2514\u2500\u2500"  # └──
            pipe = "\u2502   "  # │
            space = "    "
            child_branch = "\u2514\u2500\u2500"  # └──

        lines = [f"Decision Trace - Agent: {self.agent_id}, Tick: {self.tick}"]

        for i, step in enumerate(self.steps):
            is_last = i == len(self.steps) - 1
            prefix = last_branch if is_last else branch
            child_prefix = space if is_last else pipe

            # Format the step header with timing
            lines.append(f"{prefix} {step.name} ({step.elapsed_ms:.2f}ms)")

            # Format the data preview
            data_str = self._format_data_preview(step.data, max_data_length)
            for data_line in data_str.split("\n"):
                lines.append(f"{child_prefix}{child_branch} {data_line}")

        return "\n".join(lines)

    def _format_data_preview(self, data: Any, max_length: int) -> str:
        """Format data for preview in tree view."""
        if data is None:
            return "(none)"

        if isinstance(data, str):
            if len(data) > max_length:
                return f'[{len(data)} chars] "{data[:max_length]}..."'
            return f'"{data}"'

        if isinstance(data, dict):
            # Show key highlights for common patterns
            previews = []
            if "position" in data:
                previews.append(f"position: {data['position']}")
            if "tool" in data:
                previews.append(f"tool: {data['tool']}")
            if "params" in data:
                previews.append(f"params: {data['params']}")
            if "text" in data:
                text = data["text"]
                if len(text) > 50:
                    previews.append(f'text: "{text[:50]}..."')
                else:
                    previews.append(f'text: "{text}"')
            if "tokens" in data or "tokens_used" in data:
                tokens = data.get("tokens") or data.get("tokens_used")
                previews.append(f"tokens: {tokens}")
            if "reasoning" in data:
                reasoning = data["reasoning"]
                if reasoning and len(reasoning) > 50:
                    previews.append(f'reasoning: "{reasoning[:50]}..."')
                elif reasoning:
                    previews.append(f'reasoning: "{reasoning}"')

            if previews:
                return ", ".join(previews)

            # Fallback: show truncated JSON
            json_str = json.dumps(data)
            if len(json_str) > max_length:
                return f"[{len(json_str)} chars] {json_str[:max_length]}..."
            return json_str

        if isinstance(data, list):
            return f"[{len(data)} items]"

        return str(data)[:max_length]


class TraceStore:
    """Stores and retrieves reasoning traces.

    Traces are stored as JSONL files (one JSON object per line) for efficient
    append operations and easy tailing for watch mode.

    Storage structure:
        {traces_dir}/{agent_id}/{episode_id}.jsonl

    Attributes:
        traces_dir: Directory where traces are stored
    """

    _instance: TraceStore | None = None
    _lock = threading.Lock()

    def __init__(self, traces_dir: Path | str | None = None):
        """Initialize the trace store.

        Args:
            traces_dir: Directory to store traces. Defaults to ~/.agent_arena/traces
        """
        if traces_dir is None:
            self.traces_dir = _get_default_traces_dir()
        else:
            self.traces_dir = Path(traces_dir)

        # Create traces directory if it doesn't exist
        self.traces_dir.mkdir(parents=True, exist_ok=True)

        # Current traces being built (agent_id -> ReasoningTrace)
        self._current_traces: dict[str, ReasoningTrace] = {}

        # Episode IDs per agent
        self._episode_ids: dict[str, str] = {}

        # Lock for thread safety
        self._write_lock = threading.Lock()

        logger.info(f"TraceStore initialized at {self.traces_dir}")

    @classmethod
    def get_instance(cls, traces_dir: Path | str | None = None) -> TraceStore:
        """Get or create the singleton instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(traces_dir)
            return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (for testing)."""
        with cls._lock:
            cls._instance = None

    def set_episode(self, agent_id: str, episode_id: str | None = None) -> str:
        """Set the current episode for an agent.

        Args:
            agent_id: The agent ID
            episode_id: The episode ID (auto-generated if None)

        Returns:
            The episode ID
        """
        if episode_id is None:
            episode_id = f"ep_{int(time.time())}_{uuid.uuid4().hex[:6]}"

        self._episode_ids[agent_id] = episode_id

        # Ensure agent directory exists
        agent_dir = self.traces_dir / agent_id
        agent_dir.mkdir(parents=True, exist_ok=True)

        logger.debug(f"Episode set for {agent_id}: {episode_id}")
        return episode_id

    def get_episode(self, agent_id: str) -> str:
        """Get the current episode ID for an agent, creating one if needed."""
        if agent_id not in self._episode_ids:
            return self.set_episode(agent_id)
        return self._episode_ids[agent_id]

    def start_trace(self, agent_id: str, tick: int) -> ReasoningTrace:
        """Start a new trace for a decision.

        Args:
            agent_id: The agent ID
            tick: The current simulation tick

        Returns:
            The new ReasoningTrace
        """
        episode_id = self.get_episode(agent_id)
        trace = ReasoningTrace(agent_id=agent_id, tick=tick, episode_id=episode_id)
        self._current_traces[agent_id] = trace
        logger.debug(f"Started trace {trace.trace_id} for {agent_id} at tick {tick}")
        return trace

    def add_step(self, agent_id: str, tick: int, name: str, data: Any) -> TraceStep | None:
        """Add a step to the current trace.

        If no trace exists for this agent/tick, one is created automatically.

        Args:
            agent_id: The agent ID
            tick: The current simulation tick
            name: The step name
            data: The step data

        Returns:
            The created TraceStep, or None if tracing is disabled
        """
        # Get or create trace
        trace = self._current_traces.get(agent_id)
        if trace is None or trace.tick != tick:
            trace = self.start_trace(agent_id, tick)

        step = trace.add_step(name, data)
        logger.debug(f"Added step '{name}' to trace {trace.trace_id}")
        return step

    def end_trace(self, agent_id: str) -> ReasoningTrace | None:
        """End and persist the current trace.

        Args:
            agent_id: The agent ID

        Returns:
            The completed trace, or None if no trace was active
        """
        trace = self._current_traces.pop(agent_id, None)
        if trace is None:
            return None

        # Write to file
        self._write_trace(trace)
        logger.debug(f"Ended trace {trace.trace_id} with {len(trace.steps)} steps")
        return trace

    def _write_trace(self, trace: ReasoningTrace) -> None:
        """Write a trace to its JSONL file."""
        agent_dir = self.traces_dir / trace.agent_id
        agent_dir.mkdir(parents=True, exist_ok=True)

        trace_file = agent_dir / f"{trace.episode_id}.jsonl"

        with self._write_lock:
            with open(trace_file, "a", encoding="utf-8") as f:
                f.write(trace.to_json() + "\n")

    def get_last_decision(self, agent_id: str) -> ReasoningTrace | None:
        """Get the most recent trace for an agent.

        Args:
            agent_id: The agent ID

        Returns:
            The most recent trace, or None if no traces exist
        """
        agent_dir = self.traces_dir / agent_id
        if not agent_dir.exists():
            return None

        # Find the most recent trace file
        trace_files = sorted(
            agent_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True
        )
        if not trace_files:
            return None

        # Read the last line of the most recent file
        with open(trace_files[0], encoding="utf-8") as f:
            lines = f.readlines()
            if not lines:
                return None
            return ReasoningTrace.from_json(lines[-1])

    def get_episode_traces(self, agent_id: str, episode_id: str) -> list[ReasoningTrace]:
        """Get all traces for an episode.

        Args:
            agent_id: The agent ID
            episode_id: The episode ID

        Returns:
            List of traces in chronological order
        """
        trace_file = self.traces_dir / agent_id / f"{episode_id}.jsonl"
        if not trace_file.exists():
            return []

        traces = []
        with open(trace_file, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    traces.append(ReasoningTrace.from_json(line))

        return traces

    def list_agents(self) -> list[str]:
        """List all agents that have traces."""
        if not self.traces_dir.exists():
            return []
        return [d.name for d in self.traces_dir.iterdir() if d.is_dir()]

    def list_episodes(self, agent_id: str) -> list[str]:
        """List all episodes for an agent."""
        agent_dir = self.traces_dir / agent_id
        if not agent_dir.exists():
            return []
        return [
            f.stem
            for f in sorted(
                agent_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True
            )
        ]

    def get_trace_file(self, agent_id: str, episode_id: str | None = None) -> Path | None:
        """Get the path to a trace file.

        Args:
            agent_id: The agent ID
            episode_id: The episode ID (uses current if None)

        Returns:
            Path to the trace file, or None if it doesn't exist
        """
        if episode_id is None:
            episode_id = self._episode_ids.get(agent_id)
            if episode_id is None:
                # Try to find most recent
                episodes = self.list_episodes(agent_id)
                if not episodes:
                    return None
                episode_id = episodes[0]

        trace_file = self.traces_dir / agent_id / f"{episode_id}.jsonl"
        return trace_file if trace_file.exists() else None

    def watch(
        self,
        agent_id: str,
        callback: Callable[[ReasoningTrace], None],
        poll_interval: float = 0.5,
    ) -> Callable[[], None]:
        """Watch for new traces and call callback when they arrive.

        Args:
            agent_id: The agent ID to watch
            callback: Function to call with each new trace
            poll_interval: How often to poll for changes (seconds)

        Returns:
            A stop function to call when done watching
        """
        stop_flag = threading.Event()

        def _watch_thread():
            last_position = 0
            current_file: Path | None = None

            while not stop_flag.is_set():
                # Find the current trace file
                trace_file = self.get_trace_file(agent_id)
                if trace_file is None:
                    stop_flag.wait(poll_interval)
                    continue

                # If file changed, reset position
                if trace_file != current_file:
                    current_file = trace_file
                    last_position = 0

                try:
                    with open(trace_file, encoding="utf-8") as f:
                        f.seek(last_position)
                        new_lines = f.readlines()
                        last_position = f.tell()

                    for line in new_lines:
                        if line.strip():
                            trace = ReasoningTrace.from_json(line)
                            callback(trace)

                except Exception as e:
                    logger.error(f"Error watching traces: {e}")

                stop_flag.wait(poll_interval)

        thread = threading.Thread(target=_watch_thread, daemon=True)
        thread.start()

        def stop():
            stop_flag.set()
            thread.join(timeout=1.0)

        return stop
