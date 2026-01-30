"""Tests for the Prompt Inspector functionality."""

import json
from pathlib import Path
import pytest
import tempfile
from agent_runtime.prompt_inspector import (
    PromptInspector,
    InspectorStage,
    DecisionCapture,
    get_global_inspector,
    set_global_inspector
)


@pytest.fixture
def inspector():
    """Create a PromptInspector instance for testing."""
    return PromptInspector(enabled=True, max_entries=10, log_to_file=False)


@pytest.fixture
def temp_log_dir():
    """Create a temporary directory for file logging tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_inspector_initialization():
    """Test PromptInspector initialization."""
    inspector = PromptInspector(enabled=True, max_entries=100, log_to_file=False)
    assert inspector.enabled is True
    assert inspector.max_entries == 100
    assert inspector.log_to_file is False
    assert len(inspector.captures) == 0


def test_start_capture(inspector):
    """Test starting a capture."""
    capture = inspector.start_capture("agent_001", 1)

    assert capture is not None
    assert capture.agent_id == "agent_001"
    assert capture.tick == 1
    assert len(capture.entries) == 0

    # Verify it's stored in the inspector
    retrieved = inspector.get_capture("agent_001", 1)
    assert retrieved is capture


def test_start_capture_when_disabled():
    """Test that starting a capture when disabled returns None."""
    inspector = PromptInspector(enabled=False)
    capture = inspector.start_capture("agent_001", 1)

    assert capture is None
    assert len(inspector.captures) == 0


def test_add_entries_to_capture(inspector):
    """Test adding entries to a capture."""
    capture = inspector.start_capture("agent_001", 1)

    # Add observation entry
    capture.add_entry(InspectorStage.OBSERVATION, {
        "agent_id": "agent_001",
        "tick": 1,
        "position": [0.0, 0.0, 0.0]
    })

    # Add prompt building entry
    capture.add_entry(InspectorStage.PROMPT_BUILDING, {
        "system_prompt": "You are a test agent",
        "final_prompt": "Test prompt"
    })

    assert len(capture.entries) == 2
    assert capture.entries[0].stage == InspectorStage.OBSERVATION
    assert capture.entries[1].stage == InspectorStage.PROMPT_BUILDING


def test_max_entries_limit(inspector):
    """Test that max_entries limit is enforced."""
    inspector.max_entries = 3

    # Create 5 captures (exceeding the limit)
    for i in range(5):
        inspector.start_capture("agent_001", i)

    # Should only keep the last 3
    assert len(inspector.captures) == 3

    # Oldest captures should be removed
    assert inspector.get_capture("agent_001", 0) is None
    assert inspector.get_capture("agent_001", 1) is None
    assert inspector.get_capture("agent_001", 2) is not None
    assert inspector.get_capture("agent_001", 3) is not None
    assert inspector.get_capture("agent_001", 4) is not None


def test_get_captures_for_agent(inspector):
    """Test retrieving captures for a specific agent."""
    # Create captures for multiple agents
    inspector.start_capture("agent_001", 1)
    inspector.start_capture("agent_001", 2)
    inspector.start_capture("agent_002", 1)
    inspector.start_capture("agent_001", 3)

    # Get captures for agent_001
    captures = inspector.get_captures_for_agent("agent_001")

    assert len(captures) == 3
    assert all(c.agent_id == "agent_001" for c in captures)
    # Should be sorted by tick
    assert captures[0].tick == 1
    assert captures[1].tick == 2
    assert captures[2].tick == 3


def test_get_captures_with_tick_range(inspector):
    """Test retrieving captures filtered by tick range."""
    # Create captures at different ticks
    for tick in range(1, 11):
        inspector.start_capture("agent_001", tick)

    # Get captures in range [3, 7]
    captures = inspector.get_captures_for_agent("agent_001", tick_start=3, tick_end=7)

    assert len(captures) == 5
    assert captures[0].tick == 3
    assert captures[-1].tick == 7


def test_get_all_captures(inspector):
    """Test retrieving all captures."""
    inspector.start_capture("agent_001", 1)
    inspector.start_capture("agent_002", 1)
    inspector.start_capture("agent_001", 2)

    captures = inspector.get_all_captures()

    assert len(captures) == 3
    # Should be sorted by (tick, agent_id)
    assert captures[0].tick == 1
    assert captures[2].tick == 2


def test_clear_captures(inspector):
    """Test clearing all captures."""
    inspector.start_capture("agent_001", 1)
    inspector.start_capture("agent_002", 1)

    assert len(inspector.captures) == 2

    inspector.clear()

    assert len(inspector.captures) == 0


def test_to_json(inspector):
    """Test JSON export functionality."""
    capture = inspector.start_capture("agent_001", 1)
    capture.add_entry(InspectorStage.OBSERVATION, {
        "agent_id": "agent_001",
        "tick": 1
    })

    # Export specific capture
    json_str = inspector.to_json(agent_id="agent_001", tick=1)
    data = json.loads(json_str)

    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["agent_id"] == "agent_001"
    assert data[0]["tick"] == 1


def test_file_logging(temp_log_dir):
    """Test logging captures to files."""
    inspector = PromptInspector(
        enabled=True,
        log_to_file=True,
        log_dir=temp_log_dir
    )

    capture = inspector.start_capture("agent_001", 1)
    capture.add_entry(InspectorStage.OBSERVATION, {"test": "data"})

    inspector.finish_capture("agent_001", 1)

    # Check that file was created
    expected_file = temp_log_dir / "agent_001_tick_000001.json"
    assert expected_file.exists()

    # Verify file contents
    with open(expected_file) as f:
        data = json.load(f)

    assert data["agent_id"] == "agent_001"
    assert data["tick"] == 1
    assert len(data["entries"]) == 1


def test_global_inspector():
    """Test global inspector singleton."""
    # Get global inspector
    inspector1 = get_global_inspector()
    inspector2 = get_global_inspector()

    # Should be the same instance
    assert inspector1 is inspector2

    # Set a new global inspector
    new_inspector = PromptInspector(enabled=False)
    set_global_inspector(new_inspector)

    inspector3 = get_global_inspector()
    assert inspector3 is new_inspector
    assert inspector3.enabled is False


def test_capture_to_dict():
    """Test converting capture to dictionary."""
    capture = DecisionCapture(
        agent_id="agent_001",
        tick=42,
        start_time="2026-01-30T00:00:00Z"
    )

    capture.add_entry(InspectorStage.OBSERVATION, {"test": "data"})

    capture_dict = capture.to_dict()

    assert capture_dict["agent_id"] == "agent_001"
    assert capture_dict["tick"] == 42
    assert capture_dict["start_time"] == "2026-01-30T00:00:00Z"
    assert len(capture_dict["entries"]) == 1
    assert capture_dict["entries"][0]["stage"] == "observation"
    assert capture_dict["entries"][0]["data"]["test"] == "data"


def test_full_decision_pipeline(inspector):
    """Test capturing a complete decision pipeline."""
    capture = inspector.start_capture("agent_001", 1)

    # Simulate the 5 stages
    capture.add_entry(InspectorStage.OBSERVATION, {
        "agent_id": "agent_001",
        "tick": 1,
        "position": [10.0, 0.0, 5.0],
        "health": 100.0
    })

    capture.add_entry(InspectorStage.PROMPT_BUILDING, {
        "system_prompt": "You are an agent",
        "final_prompt": "Full prompt text"
    })

    capture.add_entry(InspectorStage.LLM_REQUEST, {
        "model": "test-model",
        "temperature": 0.7
    })

    capture.add_entry(InspectorStage.LLM_RESPONSE, {
        "raw_text": "LLM response",
        "tokens_used": 50,
        "latency_ms": 100
    })

    capture.add_entry(InspectorStage.DECISION, {
        "tool": "move_to",
        "params": {"position": [12.0, 0.0, 6.0]},
        "reasoning": "Moving to resource"
    })

    inspector.finish_capture("agent_001", 1)

    # Verify complete capture
    retrieved = inspector.get_capture("agent_001", 1)
    assert retrieved is not None
    assert len(retrieved.entries) == 5

    # Verify stages are in order
    stages = [entry.stage for entry in retrieved.entries]
    assert stages == [
        InspectorStage.OBSERVATION,
        InspectorStage.PROMPT_BUILDING,
        InspectorStage.LLM_REQUEST,
        InspectorStage.LLM_RESPONSE,
        InspectorStage.DECISION
    ]
