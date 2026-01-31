"""Tests for the reasoning trace system."""

import importlib.util
import json
import sys
import tempfile
import time
from pathlib import Path

import pytest

# Add python directory to path for imports
python_dir = Path(__file__).parent.parent / "python"
sys.path.insert(0, str(python_dir))


def load_module_directly(name: str, file_path: Path):
    """Load a module directly from file, adding it to sys.modules."""
    spec = importlib.util.spec_from_file_location(name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# Import the reasoning_trace module directly to avoid heavy dependencies in __init__.py
reasoning_trace_module = load_module_directly(
    "agent_runtime.reasoning_trace", python_dir / "agent_runtime" / "reasoning_trace.py"
)

ReasoningTrace = reasoning_trace_module.ReasoningTrace
TraceStep = reasoning_trace_module.TraceStep
TraceStore = reasoning_trace_module.TraceStore


class TestTraceStep:
    """Tests for TraceStep dataclass."""

    def test_create_trace_step(self):
        """Test creating a trace step."""
        step = TraceStep(name="test", data={"key": "value"})
        assert step.name == "test"
        assert step.data == {"key": "value"}
        assert step.timestamp > 0
        assert step.elapsed_ms == 0.0

    def test_trace_step_to_dict(self):
        """Test converting trace step to dict."""
        step = TraceStep(name="test", data={"key": "value"}, timestamp=1000.0, elapsed_ms=5.0)
        result = step.to_dict()
        assert result["name"] == "test"
        assert result["data"] == {"key": "value"}
        assert result["timestamp"] == 1000.0
        assert result["elapsed_ms"] == 5.0

    def test_trace_step_from_dict(self):
        """Test creating trace step from dict."""
        data = {"name": "test", "data": {"key": "value"}, "timestamp": 1000.0, "elapsed_ms": 5.0}
        step = TraceStep.from_dict(data)
        assert step.name == "test"
        assert step.data == {"key": "value"}
        assert step.timestamp == 1000.0
        assert step.elapsed_ms == 5.0

    def test_trace_step_serialize_complex_data(self):
        """Test serializing complex data types."""

        class MockObject:
            def __init__(self):
                self.field = "value"

        step = TraceStep(name="test", data=MockObject())
        result = step.to_dict()
        assert result["data"] == {"field": "value"}

    def test_trace_step_serialize_to_dict_method(self):
        """Test serializing objects with to_dict method."""

        class MockDataClass:
            def to_dict(self):
                return {"custom": "data"}

        step = TraceStep(name="test", data=MockDataClass())
        result = step.to_dict()
        assert result["data"] == {"custom": "data"}


class TestReasoningTrace:
    """Tests for ReasoningTrace dataclass."""

    def test_create_trace(self):
        """Test creating a reasoning trace."""
        trace = ReasoningTrace(agent_id="agent1", tick=42, episode_id="ep1")
        assert trace.agent_id == "agent1"
        assert trace.tick == 42
        assert trace.episode_id == "ep1"
        assert trace.steps == []
        assert trace.trace_id is not None
        assert trace.start_time > 0

    def test_add_step(self):
        """Test adding steps to a trace."""
        trace = ReasoningTrace(agent_id="agent1", tick=42, episode_id="ep1")
        step = trace.add_step("observation", {"position": [1, 2, 3]})

        assert len(trace.steps) == 1
        assert trace.steps[0].name == "observation"
        assert trace.steps[0].data == {"position": [1, 2, 3]}
        assert step.elapsed_ms >= 0

    def test_add_multiple_steps(self):
        """Test adding multiple steps tracks elapsed time."""
        trace = ReasoningTrace(agent_id="agent1", tick=42, episode_id="ep1")

        trace.add_step("step1", "data1")
        time.sleep(0.01)  # Small delay
        trace.add_step("step2", "data2")

        assert len(trace.steps) == 2
        assert trace.steps[1].elapsed_ms > trace.steps[0].elapsed_ms

    def test_to_dict(self):
        """Test converting trace to dict."""
        trace = ReasoningTrace(agent_id="agent1", tick=42, episode_id="ep1")
        trace.add_step("test", {"key": "value"})

        result = trace.to_dict()
        assert result["agent_id"] == "agent1"
        assert result["tick"] == 42
        assert result["episode_id"] == "ep1"
        assert len(result["steps"]) == 1

    def test_to_json_and_from_json(self):
        """Test JSON serialization round-trip."""
        trace = ReasoningTrace(agent_id="agent1", tick=42, episode_id="ep1")
        trace.add_step("observation", {"position": [1, 2, 3]})
        trace.add_step("decision", {"tool": "move_to"})

        json_str = trace.to_json()
        restored = ReasoningTrace.from_json(json_str)

        assert restored.agent_id == trace.agent_id
        assert restored.tick == trace.tick
        assert restored.episode_id == trace.episode_id
        assert len(restored.steps) == 2
        assert restored.steps[0].name == "observation"
        assert restored.steps[1].name == "decision"

    def test_format_tree(self):
        """Test tree formatting."""
        trace = ReasoningTrace(agent_id="agent1", tick=42, episode_id="ep1")
        trace.add_step("observation", {"position": [1, 2, 3]})
        trace.add_step("decision", {"tool": "move_to", "params": {"target": [4, 5, 6]}})

        tree = trace.format_tree()
        assert "Decision Trace - Agent: agent1, Tick: 42" in tree
        assert "observation" in tree
        assert "decision" in tree
        assert "move_to" in tree


class TestTraceStore:
    """Tests for TraceStore."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for traces."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def store(self, temp_dir):
        """Create a trace store in temp directory."""
        # Reset singleton
        TraceStore.reset_instance()
        return TraceStore(temp_dir)

    def test_create_store(self, temp_dir):
        """Test creating a trace store."""
        store = TraceStore(temp_dir)
        assert store.traces_dir == temp_dir
        assert temp_dir.exists()

    def test_set_episode(self, store):
        """Test setting an episode."""
        episode_id = store.set_episode("agent1", "ep_test")
        assert episode_id == "ep_test"
        assert store.get_episode("agent1") == "ep_test"

    def test_set_episode_auto_generate(self, store):
        """Test auto-generating episode ID."""
        episode_id = store.set_episode("agent1")
        assert episode_id.startswith("ep_")
        assert store.get_episode("agent1") == episode_id

    def test_start_trace(self, store):
        """Test starting a trace."""
        store.set_episode("agent1", "ep1")
        trace = store.start_trace("agent1", tick=42)

        assert trace.agent_id == "agent1"
        assert trace.tick == 42
        assert trace.episode_id == "ep1"

    def test_add_step(self, store):
        """Test adding a step."""
        store.set_episode("agent1", "ep1")
        step = store.add_step("agent1", tick=42, name="test", data={"key": "value"})

        assert step is not None
        assert step.name == "test"

    def test_end_trace_writes_file(self, store, temp_dir):
        """Test ending a trace writes to file."""
        store.set_episode("agent1", "ep1")
        store.add_step("agent1", tick=42, name="test", data={"key": "value"})
        trace = store.end_trace("agent1")

        assert trace is not None
        trace_file = temp_dir / "agent1" / "ep1.jsonl"
        assert trace_file.exists()

        with open(trace_file) as f:
            lines = f.readlines()
            assert len(lines) == 1
            data = json.loads(lines[0])
            assert data["agent_id"] == "agent1"
            assert data["tick"] == 42

    def test_get_last_decision(self, store, temp_dir):
        """Test getting the last decision."""
        store.set_episode("agent1", "ep1")

        # Add multiple traces
        store.add_step("agent1", tick=1, name="step1", data="data1")
        store.end_trace("agent1")

        store.add_step("agent1", tick=2, name="step2", data="data2")
        store.end_trace("agent1")

        last = store.get_last_decision("agent1")
        assert last is not None
        assert last.tick == 2

    def test_get_episode_traces(self, store):
        """Test getting all traces for an episode."""
        store.set_episode("agent1", "ep1")

        store.add_step("agent1", tick=1, name="s1", data="d1")
        store.end_trace("agent1")

        store.add_step("agent1", tick=2, name="s2", data="d2")
        store.end_trace("agent1")

        traces = store.get_episode_traces("agent1", "ep1")
        assert len(traces) == 2
        assert traces[0].tick == 1
        assert traces[1].tick == 2

    def test_list_agents(self, store):
        """Test listing agents."""
        store.set_episode("agent1", "ep1")
        store.add_step("agent1", tick=1, name="s1", data="d1")
        store.end_trace("agent1")

        store.set_episode("agent2", "ep1")
        store.add_step("agent2", tick=1, name="s1", data="d1")
        store.end_trace("agent2")

        agents = store.list_agents()
        assert set(agents) == {"agent1", "agent2"}

    def test_list_episodes(self, store):
        """Test listing episodes."""
        store.set_episode("agent1", "ep1")
        store.add_step("agent1", tick=1, name="s1", data="d1")
        store.end_trace("agent1")

        store.set_episode("agent1", "ep2")
        store.add_step("agent1", tick=1, name="s1", data="d1")
        store.end_trace("agent1")

        episodes = store.list_episodes("agent1")
        assert "ep1" in episodes
        assert "ep2" in episodes

    def test_no_traces_returns_none(self, store):
        """Test getting traces when none exist."""
        assert store.get_last_decision("nonexistent") is None
        assert store.get_episode_traces("agent1", "nonexistent") == []

    def test_singleton_pattern(self, temp_dir):
        """Test singleton pattern."""
        TraceStore.reset_instance()
        store1 = TraceStore.get_instance(temp_dir)
        store2 = TraceStore.get_instance()
        assert store1 is store2

        TraceStore.reset_instance()


class TestAgentBehaviorTracing:
    """Tests for tracing integration with AgentBehavior."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for traces."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_enable_tracing(self, temp_dir):
        """Test enabling tracing on an agent behavior."""
        # Import directly to avoid heavy dependencies
        schemas_module = load_module_directly(
            "agent_runtime.schemas", python_dir / "agent_runtime" / "schemas.py"
        )
        behavior_module = load_module_directly(
            "agent_runtime.behavior", python_dir / "agent_runtime" / "behavior.py"
        )

        AgentBehavior = behavior_module.AgentBehavior  # noqa: N806
        AgentDecision = schemas_module.AgentDecision  # noqa: N806
        Observation = schemas_module.Observation  # noqa: N806

        class TestAgent(AgentBehavior):
            def decide(self, observation, tools):
                self.log_step("test_step", {"data": "value"})
                return AgentDecision.idle()

        # Reset singleton to use our temp dir
        TraceStore.reset_instance()

        agent = TestAgent()
        agent.enable_tracing(temp_dir)
        agent._agent_id = "test_agent"
        agent._current_tick = 1

        # Create a mock observation
        obs = Observation(
            agent_id="test_agent",
            tick=1,
            position=(0, 0, 0),
        )

        # Make a decision
        agent.decide(obs, [])
        agent._end_trace()

        # Check trace was written
        trace_file = list(temp_dir.glob("test_agent/*.jsonl"))
        assert len(trace_file) == 1

        # Cleanup
        TraceStore.reset_instance()

    def test_log_step_without_tracing(self, temp_dir):
        """Test log_step is no-op when tracing is disabled."""
        # Use already loaded modules
        AgentBehavior = sys.modules["agent_runtime.behavior"].AgentBehavior  # noqa: N806
        AgentDecision = sys.modules["agent_runtime.schemas"].AgentDecision  # noqa: N806
        Observation = sys.modules["agent_runtime.schemas"].Observation  # noqa: N806

        class TestAgent(AgentBehavior):
            def decide(self, observation, tools):
                self.log_step("test_step", {"data": "value"})
                return AgentDecision.idle()

        agent = TestAgent()
        # Don't enable tracing

        obs = Observation(
            agent_id="test_agent",
            tick=1,
            position=(0, 0, 0),
        )

        # Should not raise
        agent.decide(obs, [])

        # No trace files should exist in temp_dir
        trace_files = list(temp_dir.glob("**/*.jsonl"))
        assert len(trace_files) == 0
