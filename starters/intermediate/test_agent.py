"""
Tests for the Intermediate Agent.

Run without Godot:
    pytest test_agent.py -v

Uses mock observations from the SDK — no game connection needed.
"""

import sys
from pathlib import Path

# Ensure the starter directory is on the path
sys.path.insert(0, str(Path(__file__).parent))
# Ensure the SDK is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "python" / "sdk"))

from agent_arena_sdk import MetricDefinition, Objective
from agent_arena_sdk.testing import (
    assert_valid_decision,
    distance_between,
    mock_hazard,
    mock_observation,
    mock_resource,
)

from agent import Agent

FORAGING_OBJECTIVE = Objective(
    description="Collect resources while staying healthy.",
    success_metrics={
        "resources_collected": MetricDefinition(target=10.0, weight=1.0, required=True),
        "health_remaining": MetricDefinition(target=50.0, weight=0.5),
    },
    time_limit=600,
)


class TestIntermediateAgent:
    """Tests for intermediate agent with memory and planning."""

    def setup_method(self):
        self.agent = Agent()

    def test_escapes_nearby_hazard(self):
        """Agent should move away from a close hazard."""
        hazard = mock_hazard("fire", position=(1.0, 0.0, 0.0), distance=1.5)
        obs = mock_observation(
            tick=1,
            nearby_hazards=[hazard],
        )

        decision = self.agent.decide(obs)

        assert_valid_decision(decision)
        assert decision.tool == "move_to"
        target = decision.params["target_position"]
        assert distance_between(target, hazard.position) > hazard.distance

    def test_moves_toward_resource(self):
        """Agent should move toward a visible resource when pursuing an objective."""
        resource = mock_resource("berry", position=(10.0, 0.0, 5.0), distance=8.0)
        obs = mock_observation(
            tick=1,
            nearby_resources=[resource],
            objective=FORAGING_OBJECTIVE,
            current_progress={"resources_collected": 0.0, "health_remaining": 100.0},
        )

        decision = self.agent.decide(obs)

        assert_valid_decision(decision)
        assert decision.tool in {"move_to", "collect"}

    def test_memory_stores_observations(self):
        """After decide(), memory should contain the observation."""
        resource = mock_resource("berry")
        obs = mock_observation(tick=1, nearby_resources=[resource])

        self.agent.decide(obs)

        assert self.agent.memory.count_observations() == 1

    def test_memory_accumulates_over_ticks(self):
        """Memory should accumulate observations over multiple ticks."""
        for tick in range(1, 6):
            obs = mock_observation(
                tick=tick,
                position=(tick * 2.0, 0.0, 0.0),
            )
            self.agent.decide(obs)

        assert self.agent.memory.count_observations() == 5

    def test_avoids_remembered_hazards(self):
        """Agent should avoid areas where hazards were seen recently."""
        # Tick 1: See a hazard
        hazard = mock_hazard(
            "fire", name="fire_001", position=(5.0, 0.0, 0.0), distance=2.0
        )
        obs1 = mock_observation(
            tick=1,
            nearby_hazards=[hazard],
            position=(3.0, 0.0, 0.0),
        )
        self.agent.decide(obs1)

        # Tick 2: Near same location, no visible hazards but memory should warn
        obs2 = mock_observation(
            tick=2,
            position=(4.0, 0.0, 0.0),
        )
        decision = self.agent.decide(obs2)

        assert_valid_decision(decision)
        # Should either escape or explore elsewhere, not move toward hazard
        if decision.tool == "move_to":
            target = decision.params["target_position"]
            assert distance_between(target, hazard.position) >= 3.0 or decision.tool == "idle"
