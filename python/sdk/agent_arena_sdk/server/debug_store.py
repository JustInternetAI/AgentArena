"""Hybrid debug storage: in-memory ring buffer + optional persistent TraceStore.

The DebugStore provides fast in-memory access to recent traces via a ring buffer,
and optionally bridges to the agent_runtime's TraceStore for disk persistence and
PromptInspector for LLM prompt/response capture data.

When agent_runtime is not on the Python path (e.g. when the SDK is installed
standalone), the store operates in memory-only mode.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lightweight trace dataclasses (SDK-local, no agent_runtime dependency)
# ---------------------------------------------------------------------------


@dataclass
class DebugTraceStep:
    """A single step inside a reasoning trace."""

    name: str
    data: Any
    timestamp: float = field(default_factory=time.time)
    elapsed_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "data": self._serialize(self.data),
            "timestamp": self.timestamp,
            "elapsed_ms": self.elapsed_ms,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DebugTraceStep:
        return cls(
            name=d["name"],
            data=d["data"],
            timestamp=d.get("timestamp", time.time()),
            elapsed_ms=d.get("elapsed_ms", 0.0),
        )

    @staticmethod
    def _serialize(data: Any) -> Any:
        if data is None or isinstance(data, (str, int, float, bool)):
            return data
        if isinstance(data, (list, tuple)):
            return [DebugTraceStep._serialize(i) for i in data]
        if isinstance(data, dict):
            return {str(k): DebugTraceStep._serialize(v) for k, v in data.items()}
        if hasattr(data, "to_dict"):
            return data.to_dict()
        return str(data)


@dataclass
class DebugTrace:
    """A complete reasoning trace for one agent decision tick."""

    agent_id: str
    tick: int
    episode_id: str = ""
    steps: list[DebugTraceStep] = field(default_factory=list)
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    start_time: float = field(default_factory=time.time)

    def add_step(self, name: str, data: Any) -> DebugTraceStep:
        now = time.time()
        step = DebugTraceStep(
            name=name,
            data=data,
            timestamp=now,
            elapsed_ms=(now - self.start_time) * 1000,
        )
        self.steps.append(step)
        return step

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "tick": self.tick,
            "episode_id": self.episode_id,
            "trace_id": self.trace_id,
            "start_time": self.start_time,
            "steps": [s.to_dict() for s in self.steps],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DebugTrace:
        trace = cls(
            agent_id=d["agent_id"],
            tick=d["tick"],
            episode_id=d.get("episode_id", ""),
            trace_id=d.get("trace_id", uuid.uuid4().hex[:8]),
            start_time=d.get("start_time", time.time()),
        )
        trace.steps = [DebugTraceStep.from_dict(s) for s in d.get("steps", [])]
        return trace


# ---------------------------------------------------------------------------
# Optional bridges to agent_runtime modules
# ---------------------------------------------------------------------------

_TraceStore: type | None = None
_ReasoningTrace: type | None = None
_PromptInspector: type | None = None

try:
    from agent_runtime.reasoning_trace import ReasoningTrace as _ReasoningTraceCls
    from agent_runtime.reasoning_trace import TraceStore as _TraceStoreCls

    _TraceStore = _TraceStoreCls
    _ReasoningTrace = _ReasoningTraceCls
except ImportError:
    pass

try:
    from agent_runtime.prompt_inspector import PromptInspector as _PromptInspectorCls

    _PromptInspector = _PromptInspectorCls
except ImportError:
    pass


def _runtime_trace_to_debug(rt: Any) -> DebugTrace:
    """Convert an agent_runtime ReasoningTrace to a DebugTrace."""
    return DebugTrace(
        agent_id=rt.agent_id,
        tick=rt.tick,
        episode_id=getattr(rt, "episode_id", ""),
        trace_id=getattr(rt, "trace_id", uuid.uuid4().hex[:8]),
        start_time=getattr(rt, "start_time", time.time()),
        steps=[
            DebugTraceStep(
                name=s.name,
                data=s.data,
                timestamp=s.timestamp,
                elapsed_ms=s.elapsed_ms,
            )
            for s in rt.steps
        ],
    )


# ---------------------------------------------------------------------------
# DebugStore
# ---------------------------------------------------------------------------


class DebugStore:
    """Hybrid trace storage: in-memory ring buffer + optional disk persistence.

    The ring buffer always works.  If ``agent_runtime`` is importable the store
    also delegates to ``TraceStore`` for JSONL persistence and can bridge
    ``PromptInspector`` captures into the unified API.
    """

    def __init__(self, max_memory_traces: int = 1000) -> None:
        self._buffer: deque[DebugTrace] = deque(maxlen=max_memory_traces)
        self._lock = threading.Lock()

        # Optional persistent store
        self._trace_store: Any | None = None
        if _TraceStore is not None:
            try:
                self._trace_store = _TraceStore.get_instance()  # type: ignore[attr-defined]
                logger.info("DebugStore: connected to persistent TraceStore")
            except Exception:
                logger.debug("DebugStore: TraceStore not available, memory-only mode")

        # Optional prompt inspector bridge
        self._prompt_inspector: Any | None = None
        if _PromptInspector is not None:
            try:
                from agent_runtime.prompt_inspector import get_global_inspector

                self._prompt_inspector = get_global_inspector()
                logger.info("DebugStore: connected to PromptInspector")
            except Exception:
                logger.debug("DebugStore: PromptInspector not available")

    # -- recording ----------------------------------------------------------

    def record_trace(self, trace: DebugTrace) -> None:
        """Add a trace to the in-memory buffer and persist if available."""
        with self._lock:
            self._buffer.append(trace)

        if self._trace_store is not None and _ReasoningTrace is not None:
            try:
                rt = _ReasoningTrace(
                    agent_id=trace.agent_id,
                    tick=trace.tick,
                    episode_id=trace.episode_id,
                    trace_id=trace.trace_id,
                    start_time=trace.start_time,
                )
                for step in trace.steps:
                    rt_step = rt.add_step(step.name, step.data)
                    rt_step.timestamp = step.timestamp
                    rt_step.elapsed_ms = step.elapsed_ms
                self._trace_store._write_trace(rt)
            except Exception as exc:
                logger.warning("DebugStore: failed to persist trace: %s", exc)

    def record_runtime_trace(self, rt: Any) -> None:
        """Record an agent_runtime ReasoningTrace (from existing instrumentation)."""
        debug_trace = _runtime_trace_to_debug(rt)
        with self._lock:
            self._buffer.append(debug_trace)
        # The runtime's own TraceStore already persists it, so skip double-write.

    # -- querying -----------------------------------------------------------

    def get_recent_traces(
        self,
        limit: int = 50,
        agent_id: str | None = None,
        tick_start: int | None = None,
        tick_end: int | None = None,
    ) -> list[dict[str, Any]]:
        """Return recent traces from the in-memory buffer."""
        with self._lock:
            items = list(self._buffer)

        if agent_id:
            items = [t for t in items if t.agent_id == agent_id]
        if tick_start is not None:
            items = [t for t in items if t.tick >= tick_start]
        if tick_end is not None:
            items = [t for t in items if t.tick <= tick_end]

        items.sort(key=lambda t: t.tick)
        return [t.to_dict() for t in items[-limit:]]

    def get_episode_traces(self, agent_id: str, episode_id: str) -> list[dict[str, Any]]:
        """Read all traces for an episode from persistent storage."""
        if self._trace_store is None:
            return []
        try:
            traces = self._trace_store.get_episode_traces(agent_id, episode_id)
            return [_runtime_trace_to_debug(t).to_dict() for t in traces]
        except Exception as exc:
            logger.warning("DebugStore: failed to read episode traces: %s", exc)
            return []

    def list_agents(self) -> list[str]:
        """List agents that have traces (persistent or in-memory)."""
        agents: set[str] = set()

        with self._lock:
            agents.update(t.agent_id for t in self._buffer)

        if self._trace_store is not None:
            try:
                agents.update(self._trace_store.list_agents())
            except Exception:
                pass

        return sorted(agents)

    def list_episodes(self, agent_id: str) -> list[str]:
        """List episodes for an agent from persistent storage."""
        if self._trace_store is None:
            return []
        try:
            return self._trace_store.list_episodes(agent_id)  # type: ignore[no-any-return]
        except Exception:
            return []

    # -- prompt inspector bridge --------------------------------------------

    def get_captures(
        self,
        agent_id: str | None = None,
        tick: int | None = None,
        tick_start: int | None = None,
        tick_end: int | None = None,
    ) -> list[dict[str, Any]]:
        """Get LLM prompt/response captures from the PromptInspector bridge."""
        if self._prompt_inspector is None:
            return []

        try:
            if agent_id and tick is not None:
                cap = self._prompt_inspector.get_capture(agent_id, tick)
                return [cap.to_dict()] if cap else []
            elif agent_id:
                caps = self._prompt_inspector.get_captures_for_agent(agent_id, tick_start, tick_end)
                return [c.to_dict() for c in caps]
            else:
                caps = self._prompt_inspector.get_all_captures(tick_start, tick_end)
                return [c.to_dict() for c in caps]
        except Exception as exc:
            logger.warning("DebugStore: failed to read captures: %s", exc)
            return []

    def clear(self) -> None:
        """Clear in-memory buffer."""
        with self._lock:
            self._buffer.clear()
