"""
Standalone test script for example agents.

This script tests the example agents with mock observations
without requiring a running Godot simulation.

Run with: python python/test_simple_agent.py
"""

import sys
from pathlib import Path

# Add python directory to path
sys.path.insert(0, str(Path(__file__).parent))

from agent_runtime.schemas import (  # noqa: E402
    HazardInfo,
    Observation,
    ResourceInfo,
    ToolSchema,
)
from user_agents.examples import SimpleForager, SimpleForagerSimple  # noqa: E402


def create_mock_tools():
    """Create mock tool schemas for testing."""
    return [
        ToolSchema(
            name="move_to",
            description="Move to a target position",
            parameters={
                "type": "object",
                "properties": {
                    "target_position": {"type": "array"},
                    "speed": {"type": "number"},
                },
            },
        ),
        ToolSchema(
            name="pickup",
            description="Pick up an item",
            parameters={
                "type": "object",
                "properties": {"item_id": {"type": "string"}},
            },
        ),
        ToolSchema(
            name="idle",
            description="Do nothing",
            parameters={"type": "object", "properties": {}},
        ),
    ]


def test_simple_forager():
    """Test SimpleForager (full AgentBehavior)."""
    print("=" * 60)
    print("Testing SimpleForager (Full AgentBehavior)")
    print("=" * 60)

    agent = SimpleForager(memory_capacity=5)
    tools = create_mock_tools()

    # Test 1: Resource nearby - should move to it
    print("\nTest 1: Resource nearby")
    obs1 = Observation(
        agent_id="test_agent",
        tick=1,
        position=(0.0, 0.0, 0.0),
        nearby_resources=[
            ResourceInfo(name="apple", type="food", position=(5.0, 0.0, 0.0), distance=5.0)
        ],
    )
    decision1 = agent.decide(obs1, tools)
    print(f"  Decision: {decision1.tool}")
    print(f"  Params: {decision1.params}")
    print(f"  Reasoning: {decision1.reasoning}")
    assert decision1.tool == "move_to", f"Expected move_to, got {decision1.tool}"
    assert "apple" in decision1.reasoning.lower(), "Reasoning should mention the resource"
    print("  PASSED")

    # Test 2: Hazard nearby - should escape
    print("\nTest 2: Hazard nearby")
    obs2 = Observation(
        agent_id="test_agent",
        tick=2,
        position=(0.0, 0.0, 0.0),
        nearby_hazards=[
            HazardInfo(
                name="lava",
                type="environmental",
                position=(2.0, 0.0, 0.0),
                distance=2.0,
                damage=50.0,
            )
        ],
    )
    decision2 = agent.decide(obs2, tools)
    print(f"  Decision: {decision2.tool}")
    print(f"  Params: {decision2.params}")
    print(f"  Reasoning: {decision2.reasoning}")
    assert decision2.tool == "move_to", f"Expected move_to, got {decision2.tool}"
    assert "avoid" in decision2.reasoning.lower() or "lava" in decision2.reasoning.lower()
    print("  PASSED")

    # Test 3: Nothing nearby - should idle
    print("\nTest 3: Nothing nearby")
    obs3 = Observation(
        agent_id="test_agent",
        tick=3,
        position=(0.0, 0.0, 0.0),
    )
    decision3 = agent.decide(obs3, tools)
    print(f"  Decision: {decision3.tool}")
    print(f"  Reasoning: {decision3.reasoning}")
    assert decision3.tool == "idle", f"Expected idle, got {decision3.tool}"
    print("  PASSED")

    # Test 4: Memory is working
    print("\nTest 4: Memory tracking")
    assert len(agent.memory) == 3, f"Expected 3 observations in memory, got {len(agent.memory)}"
    print(f"  Memory contains {len(agent.memory)} observations")
    print("  PASSED")

    print("\n" + "=" * 60)
    print("SimpleForager: All tests passed!")
    print("=" * 60)


def test_simple_forager_simple():
    """Test SimpleForagerSimple (SimpleAgentBehavior)."""
    print("\n" + "=" * 60)
    print("Testing SimpleForagerSimple (SimpleAgentBehavior)")
    print("=" * 60)

    agent = SimpleForagerSimple()
    tools = create_mock_tools()

    # Test 1: Resource nearby - should move to it
    print("\nTest 1: Resource nearby")
    obs1 = Observation(
        agent_id="test_agent",
        tick=1,
        position=(0.0, 0.0, 0.0),
        nearby_resources=[
            ResourceInfo(name="apple", type="food", position=(5.0, 0.0, 0.0), distance=5.0)
        ],
    )
    decision1 = agent._internal_decide(obs1, tools)
    print(f"  Decision: {decision1.tool}")
    print(f"  Params: {decision1.params}")
    assert decision1.tool == "move_to", f"Expected move_to, got {decision1.tool}"
    assert "target_position" in decision1.params, "Params should include target_position"
    print("  PASSED")

    # Test 2: Resource very close - should pickup
    print("\nTest 2: Resource very close")
    obs2 = Observation(
        agent_id="test_agent",
        tick=2,
        position=(0.0, 0.0, 0.0),
        nearby_resources=[
            ResourceInfo(name="apple", type="food", position=(0.5, 0.0, 0.0), distance=0.5)
        ],
    )
    decision2 = agent._internal_decide(obs2, tools)
    print(f"  Decision: {decision2.tool}")
    print(f"  Params: {decision2.params}")
    assert decision2.tool == "pickup", f"Expected pickup, got {decision2.tool}"
    print("  PASSED")

    # Test 3: Hazard nearby - should move away
    print("\nTest 3: Hazard nearby")
    obs3 = Observation(
        agent_id="test_agent",
        tick=3,
        position=(0.0, 0.0, 0.0),
        nearby_hazards=[
            HazardInfo(
                name="lava",
                type="environmental",
                position=(2.0, 0.0, 0.0),
                distance=2.0,
                damage=50.0,
            )
        ],
    )
    decision3 = agent._internal_decide(obs3, tools)
    print(f"  Decision: {decision3.tool}")
    assert decision3.tool == "move_to", f"Expected move_to, got {decision3.tool}"
    print("  PASSED")

    # Test 4: Nothing nearby - should idle
    print("\nTest 4: Nothing nearby")
    obs4 = Observation(
        agent_id="test_agent",
        tick=4,
        position=(0.0, 0.0, 0.0),
    )
    decision4 = agent._internal_decide(obs4, tools)
    print(f"  Decision: {decision4.tool}")
    assert decision4.tool == "idle", f"Expected idle, got {decision4.tool}"
    print("  PASSED")

    # Test 5: Memory is working
    print("\nTest 5: Memory tracking")
    assert len(agent._observations) == 4, f"Expected 4 observations, got {len(agent._observations)}"
    print(f"  Memory contains {len(agent._observations)} observations")
    print("  PASSED")

    print("\n" + "=" * 60)
    print("SimpleForagerSimple: All tests passed!")
    print("=" * 60)


def main():
    """Run all tests."""
    print("\nTesting Example Agents\n")

    try:
        test_simple_forager()
        test_simple_forager_simple()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        print("\nThe example agents are working correctly!")
        print("You can now use them as templates for your own agents.\n")
        return 0

    except AssertionError as e:
        print(f"\nTEST FAILED: {e}\n")
        return 1
    except Exception as e:
        print(f"\nERROR: {e}\n")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
