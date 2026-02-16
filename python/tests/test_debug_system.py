"""Tests for the unified debug system (Issue #62).

Tests ObservationTracker (debug_middleware) and DebugStore (debug_store)
independently of the FastAPI server.
"""

from __future__ import annotations

from agent_arena_sdk.server.debug_middleware import ObservationTracker
from agent_arena_sdk.server.debug_store import DebugStore, DebugTrace

# ── Helpers ───────────────────────────────────────────────────


def _make_observation(
    agent_id: str = "agent_1",
    tick: int = 1,
    resources: list[str] | None = None,
    hazards: list[str] | None = None,
) -> dict:
    """Build a minimal observation dict for testing."""
    return {
        "agent_id": agent_id,
        "tick": tick,
        "position": [1.0, 0.0, 2.0],
        "nearby_resources": [{"name": r} for r in (resources or [])],
        "nearby_hazards": [{"name": h} for h in (hazards or [])],
    }


# ── ObservationTracker ────────────────────────────────────────


class TestObservationTracker:
    def test_basic_tracking(self) -> None:
        tracker = ObservationTracker(max_entries=10)
        entry = tracker.track_observation(_make_observation(resources=["berry_1"]))
        assert entry.agent_id == "agent_1"
        assert entry.tick == 1
        assert "berry_1" in entry.visible_resources

    def test_gained_resources_on_first_observation(self) -> None:
        tracker = ObservationTracker()
        entry = tracker.track_observation(_make_observation(resources=["berry_1", "berry_2"]))
        assert set(entry.gained_resources) == {"berry_1", "berry_2"}
        assert entry.lost_resources == []

    def test_visibility_changes(self) -> None:
        tracker = ObservationTracker()

        # Tick 1: see berry_1
        tracker.track_observation(_make_observation(tick=1, resources=["berry_1"]))

        # Tick 2: see berry_1 + berry_2 (gained berry_2)
        entry2 = tracker.track_observation(
            _make_observation(tick=2, resources=["berry_1", "berry_2"])
        )
        assert "berry_2" in entry2.gained_resources
        assert entry2.lost_resources == []

        # Tick 3: only berry_2 (lost berry_1)
        entry3 = tracker.track_observation(_make_observation(tick=3, resources=["berry_2"]))
        assert "berry_1" in entry3.lost_resources
        assert entry3.gained_resources == []

    def test_per_agent_tracking(self) -> None:
        tracker = ObservationTracker()

        tracker.track_observation(_make_observation(agent_id="a", tick=1, resources=["r1"]))
        entry_b = tracker.track_observation(
            _make_observation(agent_id="b", tick=1, resources=["r2"])
        )
        # Agent b should see r2 as gained (independent from agent a)
        assert "r2" in entry_b.gained_resources

    def test_get_recent(self) -> None:
        tracker = ObservationTracker()
        for i in range(5):
            tracker.track_observation(_make_observation(tick=i))

        recent = tracker.get_recent(limit=3)
        assert len(recent) == 3
        assert recent[-1]["tick"] == 4  # most recent

    def test_get_recent_filtered_by_agent(self) -> None:
        tracker = ObservationTracker()
        tracker.track_observation(_make_observation(agent_id="a", tick=1))
        tracker.track_observation(_make_observation(agent_id="b", tick=2))
        tracker.track_observation(_make_observation(agent_id="a", tick=3))

        recent = tracker.get_recent(agent_id="a")
        assert len(recent) == 2
        assert all(o["agent_id"] == "a" for o in recent)

    def test_get_changes(self) -> None:
        tracker = ObservationTracker()

        # Tick 1: nothing visible (first obs, empty resources = no change)
        tracker.track_observation(_make_observation(tick=1, resources=[]))

        # Tick 2: gained berry_1
        tracker.track_observation(_make_observation(tick=2, resources=["berry_1"]))

        # Tick 3: no change (still berry_1)
        tracker.track_observation(_make_observation(tick=3, resources=["berry_1"]))

        changes = tracker.get_changes()
        assert len(changes) == 1
        assert changes[0]["tick"] == 2

    def test_ring_buffer_limit(self) -> None:
        tracker = ObservationTracker(max_entries=3)
        for i in range(10):
            tracker.track_observation(_make_observation(tick=i))

        recent = tracker.get_recent(limit=100)
        assert len(recent) == 3
        assert recent[0]["tick"] == 7  # oldest kept

    def test_clear(self) -> None:
        tracker = ObservationTracker()
        tracker.track_observation(_make_observation())
        tracker.clear()
        assert tracker.get_recent() == []

    def test_has_changes_property(self) -> None:
        tracker = ObservationTracker()
        entry = tracker.track_observation(_make_observation(resources=["berry_1"]))
        assert entry.has_changes  # first observation gains everything

    def test_hazard_changes(self) -> None:
        tracker = ObservationTracker()
        tracker.track_observation(_make_observation(tick=1, hazards=[]))
        entry2 = tracker.track_observation(_make_observation(tick=2, hazards=["lava_1"]))
        assert "lava_1" in entry2.gained_hazards


# ── DebugStore ────────────────────────────────────────────────


class TestDebugStore:
    def test_record_and_retrieve(self) -> None:
        store = DebugStore(max_memory_traces=100)
        trace = DebugTrace(agent_id="agent_1", tick=5, episode_id="ep1")
        trace.add_step("observation", {"position": [1, 0, 0]})
        trace.add_step("decision", {"tool": "idle"})

        store.record_trace(trace)

        recent = store.get_recent_traces()
        assert len(recent) == 1
        assert recent[0]["agent_id"] == "agent_1"
        assert recent[0]["tick"] == 5
        assert len(recent[0]["steps"]) == 2

    def test_ring_buffer_limit(self) -> None:
        store = DebugStore(max_memory_traces=5)

        for i in range(10):
            trace = DebugTrace(agent_id="agent_1", tick=i, episode_id="ep1")
            store.record_trace(trace)

        recent = store.get_recent_traces(limit=100)
        assert len(recent) == 5
        assert recent[0]["tick"] == 5  # oldest kept

    def test_filter_by_agent(self) -> None:
        store = DebugStore()

        for agent in ["a", "b"]:
            for tick in range(3):
                store.record_trace(DebugTrace(agent_id=agent, tick=tick, episode_id="ep1"))

        result = store.get_recent_traces(agent_id="a")
        assert len(result) == 3
        assert all(t["agent_id"] == "a" for t in result)

    def test_filter_by_tick_range(self) -> None:
        store = DebugStore()

        for tick in range(10):
            store.record_trace(DebugTrace(agent_id="agent_1", tick=tick, episode_id="ep1"))

        result = store.get_recent_traces(tick_start=3, tick_end=6)
        assert len(result) == 4  # ticks 3, 4, 5, 6
        ticks = [t["tick"] for t in result]
        assert ticks == [3, 4, 5, 6]

    def test_list_agents_from_buffer(self) -> None:
        store = DebugStore()
        # Disconnect from persistent store so we only test in-memory
        store._trace_store = None
        store.record_trace(DebugTrace(agent_id="bob", tick=1, episode_id="ep1"))
        store.record_trace(DebugTrace(agent_id="alice", tick=2, episode_id="ep1"))
        store.record_trace(DebugTrace(agent_id="bob", tick=3, episode_id="ep1"))

        agents = store.list_agents()
        assert agents == ["alice", "bob"]  # sorted

    def test_clear(self) -> None:
        store = DebugStore()
        store.record_trace(DebugTrace(agent_id="a", tick=1, episode_id="ep1"))
        store.clear()
        assert store.get_recent_traces() == []

    def test_debug_trace_step_elapsed(self) -> None:
        trace = DebugTrace(agent_id="a", tick=1)
        step1 = trace.add_step("observation", {"data": 1})
        assert step1.elapsed_ms >= 0

    def test_debug_trace_to_dict_roundtrip(self) -> None:
        trace = DebugTrace(agent_id="a", tick=42, episode_id="ep1")
        trace.add_step("observation", {"pos": [1, 2, 3]})
        trace.add_step("decision", {"tool": "move_to"})

        d = trace.to_dict()
        trace2 = DebugTrace.from_dict(d)

        assert trace2.agent_id == "a"
        assert trace2.tick == 42
        assert len(trace2.steps) == 2
        assert trace2.steps[0].name == "observation"
        assert trace2.steps[1].data == {"tool": "move_to"}

    def test_captures_empty_without_runtime(self) -> None:
        """get_captures should return [] when agent_runtime is not available."""
        store = DebugStore()
        # If PromptInspector isn't available, should gracefully return empty
        captures = store.get_captures(agent_id="anything")
        assert isinstance(captures, list)
