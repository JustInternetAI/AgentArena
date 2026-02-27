"""Tests for the reasoning trace system."""

import json
import tempfile
from pathlib import Path

import pytest

from agent_runtime.reasoning_trace import (
    ReasoningTrace,
    TraceStep,
    TraceStepName,
    TraceStore,
    get_global_trace_store,
    set_global_trace_store,
)


class TestTraceStepName:
    """Tests for TraceStepName enum."""

    def test_standard_step_names(self):
        """Test that standard step names exist."""
        assert TraceStepName.OBSERVATION == "observation"
        assert TraceStepName.DECISION == "decision"
        assert TraceStepName.PROMPT_BUILDING == "prompt"
        assert TraceStepName.LLM_REQUEST == "llm_request"
        assert TraceStepName.LLM_RESPONSE == "response"
        assert TraceStepName.RETRIEVED == "retrieved"


class TestTraceStep:
    """Tests for TraceStep dataclass."""

    def test_create_trace_step(self):
        """Test creating a trace step with all required fields."""
        step = TraceStep(
            timestamp="2026-01-01T00:00:00Z",
            agent_id="agent1",
            tick=42,
            name="observation",
            data={"position": [1, 2, 3]},
        )
        assert step.name == "observation"
        assert step.agent_id == "agent1"
        assert step.tick == 42
        assert step.data == {"position": [1, 2, 3]}
        assert step.duration_ms is None

    def test_create_with_duration(self):
        """Test creating a trace step with duration."""
        step = TraceStep(
            timestamp="2026-01-01T00:00:00Z",
            agent_id="agent1",
            tick=42,
            name="llm_request",
            data={"prompt": "test"},
            duration_ms=150.5,
        )
        assert step.duration_ms == 150.5

    def test_to_dict(self):
        """Test converting trace step to dict."""
        step = TraceStep(
            timestamp="2026-01-01T00:00:00Z",
            agent_id="agent1",
            tick=42,
            name="test",
            data={"key": "value"},
        )
        result = step.to_dict()
        assert result["name"] == "test"
        assert result["data"] == {"key": "value"}
        assert result["timestamp"] == "2026-01-01T00:00:00Z"
        assert result["agent_id"] == "agent1"
        assert result["tick"] == 42
        assert "duration_ms" not in result  # None values omitted

    def test_to_dict_with_duration(self):
        """Test to_dict includes duration_ms when set."""
        step = TraceStep(
            timestamp="2026-01-01T00:00:00Z",
            agent_id="agent1",
            tick=42,
            name="test",
            data={},
            duration_ms=5.0,
        )
        result = step.to_dict()
        assert result["duration_ms"] == 5.0


class TestReasoningTrace:
    """Tests for ReasoningTrace dataclass."""

    def test_create_trace(self):
        """Test creating a reasoning trace."""
        trace = ReasoningTrace(
            agent_id="agent1",
            tick=42,
            episode_id="ep1",
            start_time="2026-01-01T00:00:00Z",
        )
        assert trace.agent_id == "agent1"
        assert trace.tick == 42
        assert trace.episode_id == "ep1"
        assert trace.start_time == "2026-01-01T00:00:00Z"
        assert trace.steps == []

    def test_add_step(self):
        """Test adding steps to a trace."""
        trace = ReasoningTrace(
            agent_id="agent1",
            tick=42,
            episode_id="ep1",
            start_time="2026-01-01T00:00:00Z",
        )
        trace.add_step("observation", {"position": [1, 2, 3]})

        assert len(trace.steps) == 1
        assert trace.steps[0].name == "observation"
        assert trace.steps[0].data == {"position": [1, 2, 3]}
        assert trace.steps[0].agent_id == "agent1"
        assert trace.steps[0].tick == 42

    def test_add_step_with_duration(self):
        """Test adding step with explicit duration."""
        trace = ReasoningTrace(
            agent_id="agent1",
            tick=42,
            episode_id="ep1",
            start_time="2026-01-01T00:00:00Z",
        )
        trace.add_step("llm_request", {"prompt": "test"}, duration_ms=200.0)

        assert trace.steps[0].duration_ms == 200.0

    def test_add_multiple_steps(self):
        """Test adding multiple steps."""
        trace = ReasoningTrace(
            agent_id="agent1",
            tick=42,
            episode_id="ep1",
            start_time="2026-01-01T00:00:00Z",
        )
        trace.add_step("observation", {"pos": [0, 0, 0]})
        trace.add_step("decision", {"tool": "move_to"})

        assert len(trace.steps) == 2
        assert trace.steps[0].name == "observation"
        assert trace.steps[1].name == "decision"

    def test_to_dict(self):
        """Test converting trace to dict."""
        trace = ReasoningTrace(
            agent_id="agent1",
            tick=42,
            episode_id="ep1",
            start_time="2026-01-01T00:00:00Z",
        )
        trace.add_step("test", {"key": "value"})

        result = trace.to_dict()
        assert result["agent_id"] == "agent1"
        assert result["tick"] == 42
        assert result["episode_id"] == "ep1"
        assert result["start_time"] == "2026-01-01T00:00:00Z"
        assert len(result["steps"]) == 1

    def test_to_jsonl(self):
        """Test JSONL serialization."""
        trace = ReasoningTrace(
            agent_id="agent1",
            tick=42,
            episode_id="ep1",
            start_time="2026-01-01T00:00:00Z",
        )
        trace.add_step("observation", {"position": [1, 2, 3]})

        jsonl = trace.to_jsonl()
        data = json.loads(jsonl)
        assert data["agent_id"] == "agent1"
        assert data["tick"] == 42
        assert len(data["steps"]) == 1


class TestTraceStore:
    """Tests for TraceStore."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for traces."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def store(self):
        """Create a basic in-memory trace store."""
        return TraceStore(enabled=True, log_to_file=False)

    @pytest.fixture
    def file_store(self, temp_dir):
        """Create a trace store with file logging."""
        return TraceStore(enabled=True, log_to_file=True, log_dir=temp_dir)

    def test_create_store_defaults(self):
        """Test creating a trace store with defaults."""
        store = TraceStore()
        assert store.enabled is True
        assert store.max_entries == 1000
        assert store.log_to_file is False

    def test_create_store_disabled(self):
        """Test creating a disabled trace store."""
        store = TraceStore(enabled=False)
        assert store.enabled is False

    def test_start_and_get_capture(self, store):
        """Test starting and retrieving a capture."""
        trace = store.start_capture("agent1", tick=42)

        assert trace is not None
        assert trace.agent_id == "agent1"
        assert trace.tick == 42

        retrieved = store.get_capture("agent1", 42)
        assert retrieved is trace

    def test_start_capture_disabled(self):
        """Test start_capture returns None when disabled."""
        store = TraceStore(enabled=False)
        trace = store.start_capture("agent1", tick=42)
        assert trace is None

    def test_finish_capture(self, store):
        """Test finishing a capture."""
        trace = store.start_capture("agent1", tick=42)
        trace.add_step("observation", {"pos": [0, 0, 0]})
        # Should not raise
        store.finish_capture("agent1", 42)

    def test_finish_capture_with_file(self, file_store, temp_dir):
        """Test finishing a capture writes to JSONL file."""
        trace = file_store.start_capture("agent1", tick=42)
        trace.add_step("test", {"key": "value"})
        file_store.finish_capture("agent1", 42)

        # Check that the episode file was written
        episode_file = temp_dir / f"{file_store.episode_id}.jsonl"
        assert episode_file.exists()

        # Close file handle before reading (Windows file locking)
        file_store.end_episode()

        with open(episode_file) as f:
            lines = f.readlines()
            assert len(lines) == 1
            data = json.loads(lines[0])
            assert data["agent_id"] == "agent1"
            assert data["tick"] == 42

    def test_get_captures_for_agent(self, store):
        """Test getting all captures for an agent."""
        store.start_capture("agent1", tick=1)
        store.start_capture("agent1", tick=2)
        store.start_capture("agent2", tick=1)

        traces = store.get_captures_for_agent("agent1")
        assert len(traces) == 2
        assert traces[0].tick == 1
        assert traces[1].tick == 2

    def test_get_all_captures(self, store):
        """Test getting all captures."""
        store.start_capture("agent1", tick=1)
        store.start_capture("agent2", tick=1)
        store.start_capture("agent1", tick=2)

        traces = store.get_all_captures()
        assert len(traces) == 3

    def test_get_all_captures_with_tick_range(self, store):
        """Test filtering captures by tick range."""
        store.start_capture("agent1", tick=1)
        store.start_capture("agent1", tick=5)
        store.start_capture("agent1", tick=10)

        traces = store.get_all_captures(tick_start=3, tick_end=7)
        assert len(traces) == 1
        assert traces[0].tick == 5

    def test_max_entries_limit(self):
        """Test that max_entries limit is enforced."""
        store = TraceStore(max_entries=3)
        store.start_capture("agent1", tick=1)
        store.start_capture("agent1", tick=2)
        store.start_capture("agent1", tick=3)
        store.start_capture("agent1", tick=4)

        assert len(store.traces) == 3
        # Oldest (tick=1) should have been evicted
        assert store.get_capture("agent1", 1) is None
        assert store.get_capture("agent1", 4) is not None

    def test_start_and_end_episode(self, file_store, temp_dir):
        """Test episode lifecycle."""
        file_store.start_episode("ep_custom")
        assert file_store.episode_id == "ep_custom"

        trace = file_store.start_capture("agent1", tick=1)
        trace.add_step("test", {})
        file_store.finish_capture("agent1", 1)

        file_store.end_episode()

        # Verify file was written
        episode_file = temp_dir / "ep_custom.jsonl"
        assert episode_file.exists()

    def test_get_episode_traces(self, file_store, temp_dir):
        """Test reading traces back from episode file."""
        file_store.start_episode("ep_read_test")

        trace = file_store.start_capture("agent1", tick=1)
        trace.add_step("obs", {"pos": [0, 0, 0]})
        file_store.finish_capture("agent1", 1)

        trace2 = file_store.start_capture("agent1", tick=2)
        trace2.add_step("dec", {"tool": "idle"})
        file_store.finish_capture("agent1", 2)

        file_store.end_episode()

        # Read back from file
        traces = file_store.get_episode_traces("ep_read_test")
        assert len(traces) == 2
        assert traces[0].tick == 1
        assert traces[1].tick == 2

    def test_watch_callback(self, store):
        """Test watcher callbacks on finish_capture."""
        received = []

        def on_trace(trace):
            received.append(trace)

        store.watch("agent1", on_trace)

        trace = store.start_capture("agent1", tick=1)
        trace.add_step("test", {})
        store.finish_capture("agent1", 1)

        assert len(received) == 1
        assert received[0].agent_id == "agent1"

    def test_watch_wildcard(self, store):
        """Test wildcard watcher receives all agents."""
        received = []
        store.watch("*", lambda t: received.append(t))

        store.start_capture("agent1", tick=1)
        store.finish_capture("agent1", 1)

        store.start_capture("agent2", tick=1)
        store.finish_capture("agent2", 1)

        assert len(received) == 2

    def test_unwatch(self, store):
        """Test removing a watcher."""
        received = []

        def callback(trace):
            received.append(trace)

        store.watch("agent1", callback)
        store.unwatch("agent1", callback)

        store.start_capture("agent1", tick=1)
        store.finish_capture("agent1", 1)

        assert len(received) == 0

    def test_clear(self, store):
        """Test clearing all in-memory traces."""
        store.start_capture("agent1", tick=1)
        store.start_capture("agent1", tick=2)
        assert len(store.traces) == 2

        store.clear()
        assert len(store.traces) == 0

    def test_to_json(self, store):
        """Test JSON export."""
        trace = store.start_capture("agent1", tick=1)
        trace.add_step("obs", {"pos": [0, 0, 0]})

        json_str = store.to_json()
        data = json.loads(json_str)
        assert len(data) == 1
        assert data[0]["agent_id"] == "agent1"

    def test_to_json_filter_by_agent(self, store):
        """Test JSON export filtered by agent."""
        store.start_capture("agent1", tick=1)
        store.start_capture("agent2", tick=1)

        json_str = store.to_json(agent_id="agent1")
        data = json.loads(json_str)
        assert len(data) == 1
        assert data[0]["agent_id"] == "agent1"

    def test_get_capture_nonexistent(self, store):
        """Test getting a nonexistent capture returns None."""
        assert store.get_capture("agent1", 999) is None


class TestGlobalTraceStore:
    """Tests for global singleton functions."""

    def test_get_global_creates_default(self):
        """Test get_global_trace_store creates a default store."""
        # Reset global
        set_global_trace_store(None)

        # Import and reset the global
        import agent_runtime.reasoning_trace as rt

        rt._global_trace_store = None

        store = get_global_trace_store()
        assert store is not None
        assert isinstance(store, TraceStore)

    def test_set_and_get_global(self):
        """Test setting and getting a custom global store."""
        custom_store = TraceStore(enabled=False, max_entries=50)
        set_global_trace_store(custom_store)

        retrieved = get_global_trace_store()
        assert retrieved is custom_store
        assert retrieved.enabled is False
        assert retrieved.max_entries == 50


class TestAgentBehaviorTracing:
    """Tests for tracing integration with AgentBehavior."""

    def test_log_step_with_tracing(self):
        """Test log_step adds to current trace when tracing is active."""
        from agent_runtime.behavior import AgentBehavior
        from agent_runtime.schemas import AgentDecision, Observation

        class TestAgent(AgentBehavior):
            def decide(self, observation, tools):
                self.log_step("test_step", {"data": "value"})
                return AgentDecision.idle()

        store = TraceStore(enabled=True, log_to_file=False)
        agent = TestAgent()
        agent._trace_store = store

        # Simulate what IPC server does
        agent._set_trace_context("test_agent", 1)

        obs = Observation(agent_id="test_agent", tick=1, position=(0, 0, 0))
        agent.decide(obs, [])
        agent._end_trace()

        # Verify the trace was captured
        trace = store.get_capture("test_agent", 1)
        assert trace is not None
        assert len(trace.steps) == 1
        assert trace.steps[0].name == "test_step"
        assert trace.steps[0].data == {"data": "value"}

    def test_log_step_without_tracing(self):
        """Test log_step is a no-op when tracing is disabled."""
        from agent_runtime.behavior import AgentBehavior
        from agent_runtime.schemas import AgentDecision, Observation

        class TestAgent(AgentBehavior):
            def decide(self, observation, tools):
                self.log_step("test_step", {"data": "value"})
                return AgentDecision.idle()

        agent = TestAgent()
        # Don't set _trace_store

        obs = Observation(agent_id="test_agent", tick=1, position=(0, 0, 0))
        # Should not raise
        agent.decide(obs, [])
