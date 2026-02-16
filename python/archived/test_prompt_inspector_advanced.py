"""
Advanced testing script for the Prompt Inspector.

Tests various scenarios including:
- Error handling
- Different response formats
- Multiple agents
- Filtering and querying
- Performance metrics
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dataclasses import dataclass, field  # noqa: E402

from agent_runtime.prompt_inspector import InspectorStage, PromptInspector  # noqa: E402


# Minimal standalone classes
@dataclass
class Observation:
    agent_id: str
    tick: int
    position: tuple[float, float, float]
    health: float = 100.0
    energy: float = 100.0
    nearby_resources: list = field(default_factory=list)
    nearby_hazards: list = field(default_factory=list)
    inventory: list = field(default_factory=list)
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    velocity: tuple[float, float, float] = (0.0, 0.0, 0.0)


def print_header(title: str):
    """Print section header."""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}\n")


def test_basic_functionality():
    """Test 1: Basic capture and retrieval."""
    print_header("TEST 1: Basic Functionality")

    inspector = PromptInspector(enabled=True, max_entries=10)

    # Create a simple capture
    capture = inspector.start_capture("agent_001", 1)
    capture.add_entry(
        InspectorStage.OBSERVATION,
        {"agent_id": "agent_001", "tick": 1, "position": [0.0, 0.0, 0.0]},
    )
    capture.add_entry(
        InspectorStage.DECISION,
        {
            "tool": "move_to",
            "params": {"target_position": [5.0, 0.0, 0.0]},
            "reasoning": "Moving towards target",
        },
    )
    inspector.finish_capture("agent_001", 1)

    # Retrieve and verify
    retrieved = inspector.get_capture("agent_001", 1)
    assert retrieved is not None, "Capture should exist"
    assert len(retrieved.entries) == 2, "Should have 2 entries"
    print(f"[PASS] Created and retrieved capture with {len(retrieved.entries)} entries")

    return inspector


def test_multiple_agents():
    """Test 2: Multiple agents and filtering."""
    print_header("TEST 2: Multiple Agents")

    inspector = PromptInspector(enabled=True, max_entries=100)

    # Create captures for 3 different agents
    agents = ["agent_001", "agent_002", "agent_003"]
    for agent_id in agents:
        for tick in range(1, 6):  # 5 ticks per agent
            capture = inspector.start_capture(agent_id, tick)
            capture.add_entry(InspectorStage.OBSERVATION, {"agent_id": agent_id, "tick": tick})
            capture.add_entry(InspectorStage.DECISION, {"tool": "idle", "params": {}})
            inspector.finish_capture(agent_id, tick)

    # Test filtering by agent
    agent_001_captures = inspector.get_captures_for_agent("agent_001")
    assert (
        len(agent_001_captures) == 5
    ), f"Should have 5 captures for agent_001, got {len(agent_001_captures)}"

    # Test filtering by tick range
    tick_filtered = inspector.get_captures_for_agent("agent_002", tick_start=2, tick_end=4)
    assert (
        len(tick_filtered) == 3
    ), f"Should have 3 captures in range [2,4], got {len(tick_filtered)}"

    # Test getting all captures
    all_captures = inspector.get_all_captures()
    assert len(all_captures) == 15, f"Should have 15 total captures, got {len(all_captures)}"

    print(f"[PASS] Created captures for {len(agents)} agents")
    print(f"[PASS] Filtered by agent: {len(agent_001_captures)} captures")
    print(f"[PASS] Filtered by tick range: {len(tick_filtered)} captures")
    print(f"[PASS] Retrieved all captures: {len(all_captures)} total")

    return inspector


def test_max_entries_limit():
    """Test 3: Max entries limit (FIFO)."""
    print_header("TEST 3: Max Entries Limit (FIFO)")

    inspector = PromptInspector(enabled=True, max_entries=5)

    # Create 10 captures (exceeding the limit)
    for tick in range(1, 11):
        capture = inspector.start_capture("agent_test", tick)
        capture.add_entry(InspectorStage.OBSERVATION, {"tick": tick})
        inspector.finish_capture("agent_test", tick)

    # Should only keep the last 5
    captures = inspector.get_captures_for_agent("agent_test")
    assert len(captures) == 5, f"Should keep only 5 captures, got {len(captures)}"
    assert captures[0].tick == 6, f"First capture should be tick 6, got {captures[0].tick}"
    assert captures[-1].tick == 10, f"Last capture should be tick 10, got {captures[-1].tick}"

    print("[PASS] FIFO limit working correctly")
    print(f"[PASS] Kept ticks: {[c.tick for c in captures]}")

    return inspector


def test_disabled_inspector():
    """Test 4: Disabled inspector."""
    print_header("TEST 4: Disabled Inspector")

    inspector = PromptInspector(enabled=False)

    # Try to create a capture
    capture = inspector.start_capture("agent_test", 1)
    assert capture is None, "Should return None when disabled"

    # Verify no captures were stored
    captures = inspector.get_all_captures()
    assert len(captures) == 0, "Should have 0 captures when disabled"

    print("[PASS] Inspector correctly disabled")
    print(f"[PASS] No captures stored: {len(captures)} captures")

    return inspector


def test_json_export():
    """Test 5: JSON export."""
    print_header("TEST 5: JSON Export")

    inspector = PromptInspector(enabled=True)

    # Create a capture with all stages
    capture = inspector.start_capture("agent_json", 1)
    capture.add_entry(InspectorStage.OBSERVATION, {"position": [1.0, 2.0, 3.0]})
    capture.add_entry(InspectorStage.PROMPT_BUILDING, {"prompt_length": 500})
    capture.add_entry(InspectorStage.LLM_REQUEST, {"model": "test-model"})
    capture.add_entry(InspectorStage.LLM_RESPONSE, {"tokens_used": 42})
    capture.add_entry(InspectorStage.DECISION, {"tool": "move_to"})
    inspector.finish_capture("agent_json", 1)

    # Export to JSON
    json_str = inspector.to_json(agent_id="agent_json", tick=1)
    data = json.loads(json_str)

    assert isinstance(data, list), "Should be a list"
    assert len(data) == 1, "Should have 1 capture"
    assert len(data[0]["entries"]) == 5, "Should have 5 entries"

    print("[PASS] JSON export successful")
    print(f"[PASS] Exported {len(data)} capture(s)")
    print(f"[PASS] JSON structure valid with {len(data[0]['entries'])} stages")

    # Pretty print first entry
    print("\nFirst entry (observation):")
    print(json.dumps(data[0]["entries"][0], indent=2)[:200] + "...")

    return inspector


def test_file_logging():
    """Test 6: File logging."""
    print_header("TEST 6: File Logging")

    import tempfile

    log_dir = Path(tempfile.mkdtemp())

    inspector = PromptInspector(enabled=True, log_to_file=True, log_dir=log_dir)

    # Create a few captures
    for tick in range(1, 4):
        capture = inspector.start_capture("agent_file", tick)
        capture.add_entry(InspectorStage.OBSERVATION, {"tick": tick})
        capture.add_entry(InspectorStage.DECISION, {"tool": "idle"})
        inspector.finish_capture("agent_file", tick)

    # Verify files were created
    log_files = list(log_dir.glob("*.json"))
    assert len(log_files) == 3, f"Should have 3 log files, got {len(log_files)}"

    # Verify file contents
    first_file = log_files[0]
    with open(first_file) as f:
        data = json.load(f)

    assert data["agent_id"] == "agent_file", "File should contain correct agent_id"
    assert len(data["entries"]) == 2, "File should have 2 entries"

    print(f"[PASS] Created {len(log_files)} log files")
    print(f"[PASS] Files located at: {log_dir}")
    print("[PASS] File contents validated")

    # Cleanup
    for f in log_files:
        f.unlink()
    log_dir.rmdir()

    return inspector


def test_clear_functionality():
    """Test 7: Clear functionality."""
    print_header("TEST 7: Clear Functionality")

    inspector = PromptInspector(enabled=True)

    # Create some captures
    for tick in range(1, 6):
        capture = inspector.start_capture("agent_clear", tick)
        capture.add_entry(InspectorStage.OBSERVATION, {"tick": tick})
        inspector.finish_capture("agent_clear", tick)

    before_count = len(inspector.get_all_captures())
    assert before_count == 5, "Should have 5 captures before clear"

    # Clear all
    inspector.clear()

    after_count = len(inspector.get_all_captures())
    assert after_count == 0, "Should have 0 captures after clear"

    print(f"[PASS] Before clear: {before_count} captures")
    print(f"[PASS] After clear: {after_count} captures")

    return inspector


def test_complex_filtering():
    """Test 8: Complex filtering scenarios."""
    print_header("TEST 8: Complex Filtering")

    inspector = PromptInspector(enabled=True)

    # Create captures for multiple agents across different tick ranges
    agents_ticks = {
        "agent_A": range(1, 11),  # ticks 1-10
        "agent_B": range(5, 16),  # ticks 5-15
        "agent_C": range(10, 21),  # ticks 10-20
    }

    for agent_id, ticks in agents_ticks.items():
        for tick in ticks:
            capture = inspector.start_capture(agent_id, tick)
            capture.add_entry(InspectorStage.OBSERVATION, {"agent_id": agent_id, "tick": tick})
            inspector.finish_capture(agent_id, tick)

    # Test 1: Specific agent, no tick filter
    agent_a_all = inspector.get_captures_for_agent("agent_A")
    assert len(agent_a_all) == 10, "agent_A should have 10 captures"

    # Test 2: Specific agent with tick range
    agent_b_filtered = inspector.get_captures_for_agent("agent_B", tick_start=10, tick_end=12)
    assert len(agent_b_filtered) == 3, "agent_B ticks 10-12 should have 3 captures"

    # Test 3: All agents in specific tick range
    all_in_range = inspector.get_all_captures(tick_start=8, tick_end=12)
    expected = 3 + 5 + 3  # agent_A: 8-10 (3), agent_B: 8-12 (5), agent_C: 10-12 (3)
    assert (
        len(all_in_range) == expected
    ), f"Ticks 8-12 should have {expected} captures, got {len(all_in_range)}"

    print(f"[PASS] agent_A all ticks: {len(agent_a_all)} captures")
    print(f"[PASS] agent_B ticks [10-12]: {len(agent_b_filtered)} captures")
    print(f"[PASS] All agents ticks [8-12]: {len(all_in_range)} captures")

    return inspector


def test_performance_metrics():
    """Test 9: Performance metrics extraction."""
    print_header("TEST 9: Performance Metrics")

    inspector = PromptInspector(enabled=True)

    # Create captures with timing data
    latencies = [50, 100, 75, 200, 150]
    token_counts = [30, 45, 38, 52, 41]

    for i, (latency, tokens) in enumerate(zip(latencies, token_counts), 1):
        capture = inspector.start_capture("agent_perf", i)
        capture.add_entry(InspectorStage.OBSERVATION, {"tick": i})
        capture.add_entry(
            InspectorStage.LLM_RESPONSE, {"latency_ms": latency, "tokens_used": tokens}
        )
        capture.add_entry(InspectorStage.DECISION, {"tool": "move_to", "total_latency_ms": latency})
        inspector.finish_capture("agent_perf", i)

    # Extract performance metrics
    captures = inspector.get_captures_for_agent("agent_perf")

    extracted_latencies = []
    extracted_tokens = []

    for capture in captures:
        for entry in capture.entries:
            if entry.stage == InspectorStage.LLM_RESPONSE:
                extracted_latencies.append(entry.data["latency_ms"])
                extracted_tokens.append(entry.data["tokens_used"])

    avg_latency = sum(extracted_latencies) / len(extracted_latencies)
    avg_tokens = sum(extracted_tokens) / len(extracted_tokens)

    print(f"[PASS] Extracted {len(extracted_latencies)} latency measurements")
    print(f"[PASS] Average latency: {avg_latency:.1f}ms")
    print(f"[PASS] Average tokens: {avg_tokens:.1f}")
    print(f"[PASS] Min/Max latency: {min(extracted_latencies)}ms / {max(extracted_latencies)}ms")

    return inspector


def test_error_scenarios():
    """Test 10: Error handling scenarios."""
    print_header("TEST 10: Error Handling")

    inspector = PromptInspector(enabled=True)

    # Test 1: Get non-existent capture
    result = inspector.get_capture("nonexistent", 999)
    assert result is None, "Should return None for non-existent capture"
    print("[PASS] Non-existent capture returns None")

    # Test 2: Finish capture that was never started
    inspector.finish_capture("ghost_agent", 1)  # Should not crash
    print("[PASS] Finishing non-existent capture doesn't crash")

    # Test 3: Capture with error stage
    capture = inspector.start_capture("agent_error", 1)
    capture.add_entry(InspectorStage.OBSERVATION, {"tick": 1})
    capture.add_entry(
        InspectorStage.DECISION,
        {
            "tool": "idle",
            "params": {},
            "reasoning": "Error occurred",
            "error": "Backend connection failed",
        },
    )
    inspector.finish_capture("agent_error", 1)

    retrieved = inspector.get_capture("agent_error", 1)
    has_error = any("error" in entry.data for entry in retrieved.entries)
    assert has_error, "Should contain error information"
    print("[PASS] Error information captured correctly")

    # Test 4: Empty tick range
    empty_results = inspector.get_all_captures(tick_start=1000, tick_end=2000)
    assert len(empty_results) == 0, "Should return empty list for out-of-range query"
    print("[PASS] Empty tick range returns empty list")

    return inspector


def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("  PROMPT INSPECTOR ADVANCED TESTING SUITE")
    print("=" * 80)

    tests = [
        ("Basic Functionality", test_basic_functionality),
        ("Multiple Agents", test_multiple_agents),
        ("Max Entries Limit", test_max_entries_limit),
        ("Disabled Inspector", test_disabled_inspector),
        ("JSON Export", test_json_export),
        ("File Logging", test_file_logging),
        ("Clear Functionality", test_clear_functionality),
        ("Complex Filtering", test_complex_filtering),
        ("Performance Metrics", test_performance_metrics),
        ("Error Handling", test_error_scenarios),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"\n[FAIL] {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"\n[ERROR] {name}: {e}")
            failed += 1

    print_header("TEST SUMMARY")
    print(f"Total tests: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed == 0:
        print("\n[SUCCESS] All tests passed! The Prompt Inspector is working perfectly.")
    else:
        print(f"\n[WARNING] {failed} test(s) failed. Please review the output above.")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
