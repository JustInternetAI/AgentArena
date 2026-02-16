"""
Tests for the agent-arena-sdk package.

These tests verify the core SDK functionality:
- Schema creation and serialization
- Decision construction
- Observation parsing
- Objective system
"""

import pytest

from agent_arena_sdk import Decision, MetricDefinition, Observation, Objective


class TestDecision:
    """Tests for Decision schema."""

    def test_create_decision(self):
        """Test creating a basic decision."""
        decision = Decision(
            tool="move_to",
            params={"target_position": [10.0, 0.0, 5.0]},
            reasoning="Moving toward resource",
        )

        assert decision.tool == "move_to"
        assert decision.params["target_position"] == [10.0, 0.0, 5.0]
        assert decision.reasoning == "Moving toward resource"

    def test_idle_decision(self):
        """Test creating an idle decision."""
        decision = Decision.idle(reasoning="Nothing to do")

        assert decision.tool == "idle"
        assert decision.params == {}
        assert decision.reasoning == "Nothing to do"

    def test_decision_without_reasoning(self):
        """Test that reasoning is optional."""
        decision = Decision(tool="collect", params={"target_name": "berry_001"})

        assert decision.tool == "collect"
        assert decision.reasoning is None


class TestObjective:
    """Tests for Objective system."""

    def test_create_metric_definition(self):
        """Test creating a metric definition."""
        metric = MetricDefinition(
            target=100.0, weight=1.5, lower_is_better=False, required=True
        )

        assert metric.target == 100.0
        assert metric.weight == 1.5
        assert metric.lower_is_better is False
        assert metric.required is True

    def test_metric_definition_defaults(self):
        """Test metric definition defaults."""
        metric = MetricDefinition(target=50.0)

        assert metric.target == 50.0
        assert metric.weight == 1.0
        assert metric.lower_is_better is False
        assert metric.required is False

    def test_create_objective(self):
        """Test creating an objective."""
        objective = Objective(
            description="Collect 10 berries within 100 ticks",
            success_metrics={
                "berries_collected": MetricDefinition(target=10.0, required=True),
                "time_taken": MetricDefinition(target=100.0, lower_is_better=True),
            },
            time_limit=100,
        )

        assert objective.description == "Collect 10 berries within 100 ticks"
        assert len(objective.success_metrics) == 2
        assert objective.success_metrics["berries_collected"].target == 10.0
        assert objective.time_limit == 100

    def test_objective_defaults(self):
        """Test objective defaults."""
        objective = Objective(description="Explore the environment")

        assert objective.description == "Explore the environment"
        assert objective.success_metrics == {}
        assert objective.time_limit == 0

    def test_objective_serialization(self):
        """Test objective to_dict and from_dict."""
        original = Objective(
            description="Test objective",
            success_metrics={"score": MetricDefinition(target=100.0, weight=2.0)},
            time_limit=200,
        )

        # Convert to dict
        obj_dict = original.to_dict()

        assert obj_dict["description"] == "Test objective"
        assert "score" in obj_dict["success_metrics"]
        assert obj_dict["time_limit"] == 200

        # Convert back from dict
        reconstructed = Objective.from_dict(obj_dict)

        assert reconstructed.description == original.description
        assert reconstructed.time_limit == original.time_limit
        assert "score" in reconstructed.success_metrics


class TestObservation:
    """Tests for Observation schema."""

    def test_create_basic_observation(self):
        """Test creating a basic observation."""
        obs = Observation(
            agent_id="agent_001",
            tick=5,
            position=(10.0, 0.0, 5.0),
            rotation=(0.0, 90.0, 0.0),
            velocity=(1.0, 0.0, 0.5),
            health=100.0,
            energy=80.0,
        )

        assert obs.agent_id == "agent_001"
        assert obs.tick == 5
        assert obs.position == (10.0, 0.0, 5.0)
        assert obs.health == 100.0

    def test_observation_with_objective(self):
        """Test observation with objective field."""
        objective = Objective(
            description="Collect resources",
            success_metrics={"resources": MetricDefinition(target=50.0)},
        )

        obs = Observation(
            agent_id="agent_001",
            tick=1,
            position=(0.0, 0.0, 0.0),
            scenario_name="resource_collection",
            objective=objective,
            current_progress={"resources": 25.0},
        )

        assert obs.scenario_name == "resource_collection"
        assert obs.objective is not None
        assert obs.objective.description == "Collect resources"
        assert obs.current_progress["resources"] == 25.0

    def test_observation_defaults(self):
        """Test observation default values."""
        obs = Observation(
            agent_id="agent_001", tick=0, position=(0.0, 0.0, 0.0)
        )

        assert obs.rotation is None
        assert obs.velocity is None
        assert obs.visible_entities == []
        assert obs.nearby_resources == []
        assert obs.nearby_hazards == []
        assert obs.inventory == []
        assert obs.health == 100.0
        assert obs.energy == 100.0
        assert obs.scenario_name == ""
        assert obs.objective is None
        assert obs.current_progress == {}

    def test_observation_serialization(self):
        """Test observation to_dict and from_dict with objective."""
        objective = Objective(
            description="Test", success_metrics={"score": MetricDefinition(target=10.0)}
        )

        original = Observation(
            agent_id="test_agent",
            tick=10,
            position=(1.0, 2.0, 3.0),
            scenario_name="test_scenario",
            objective=objective,
            current_progress={"score": 5.0},
        )

        # Convert to dict
        obs_dict = original.to_dict()

        assert obs_dict["agent_id"] == "test_agent"
        assert obs_dict["scenario_name"] == "test_scenario"
        assert "objective" in obs_dict
        assert obs_dict["current_progress"]["score"] == 5.0

        # Convert back from dict
        reconstructed = Observation.from_dict(obs_dict)

        assert reconstructed.agent_id == original.agent_id
        assert reconstructed.scenario_name == original.scenario_name
        assert reconstructed.objective is not None
        assert reconstructed.current_progress == original.current_progress


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
