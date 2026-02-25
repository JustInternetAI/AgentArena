"""
Tests for the Beginner Agent.

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

from agent_arena_sdk.testing import (
    assert_valid_decision,
    distance_between,
    mock_hazard,
    mock_observation,
    mock_resource,
)

from agent import Agent


class TestBeginnerAgent:
    """Tests for beginner priority-based agent."""

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
        # Should move AWAY from the hazard
        assert distance_between(target, hazard.position) > hazard.distance

    def test_moves_toward_resource(self):
        """Agent should move toward a visible resource when safe."""
        resource = mock_resource("berry", position=(10.0, 0.0, 5.0), distance=8.0)
        obs = mock_observation(
            tick=1,
            nearby_resources=[resource],
        )

        decision = self.agent.decide(obs)

        assert_valid_decision(decision)
        assert decision.tool == "move_to"
        target = decision.params["target_position"]
        # Should move toward the resource
        assert distance_between(target, resource.position) < resource.distance

    def test_idles_when_nothing_visible(self):
        """Agent should idle when no resources, hazards, or exploration targets."""
        obs = mock_observation(tick=1)

        decision = self.agent.decide(obs)

        assert_valid_decision(decision)
        assert decision.tool == "idle"

    def test_hazard_priority_over_resource(self):
        """Agent should escape hazard even when resources are nearby."""
        hazard = mock_hazard("fire", position=(1.0, 0.0, 0.0), distance=1.5)
        resource = mock_resource("berry", position=(5.0, 0.0, 5.0), distance=5.0)
        obs = mock_observation(
            tick=1,
            nearby_hazards=[hazard],
            nearby_resources=[resource],
        )

        decision = self.agent.decide(obs)

        assert_valid_decision(decision)
        assert decision.tool == "move_to"
        target = decision.params["target_position"]
        # Should move away from hazard, not toward resource
        assert distance_between(target, hazard.position) > hazard.distance

    def test_returns_decision_type(self):
        """Agent should always return a Decision object."""
        from agent_arena_sdk import Decision

        obs = mock_observation(tick=1)
        decision = self.agent.decide(obs)
        assert isinstance(decision, Decision)
