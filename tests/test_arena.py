"""
Tests for AgentArena orchestrator and IPC integration.
"""

import pytest

from agent_runtime import AgentArena
from agent_runtime.behavior import AgentBehavior
from agent_runtime.schemas import AgentDecision, Observation


class MockBehavior(AgentBehavior):
    """Mock agent behavior for testing."""

    def __init__(self, decision=None):
        self.decision = decision or AgentDecision.idle()
        self.observations = []
        self.tool_schemas = []

    def decide(self, observation, tools):
        self.observations.append(observation)
        self.tool_schemas = tools
        return self.decision


class TestAgentArena:
    """Tests for AgentArena class."""

    def test_initialization(self):
        """Test basic initialization."""
        arena = AgentArena(max_workers=8)
        assert arena.runtime is not None
        assert arena.behaviors == {}
        assert arena.ipc_server is None
        assert not arena.is_running()

    def test_default_workers(self):
        """Test default worker count."""
        arena = AgentArena()
        assert arena.runtime.executor._max_workers == 4

    def test_custom_workers(self):
        """Test custom worker count."""
        arena = AgentArena(max_workers=8)
        assert arena.runtime.executor._max_workers == 8

    def test_register_behavior(self):
        """Test registering agent behaviors."""
        arena = AgentArena()
        behavior = MockBehavior()

        arena.register('agent_001', behavior)
        assert 'agent_001' in arena.behaviors
        assert arena.behaviors['agent_001'] == behavior

    def test_register_multiple_behaviors(self):
        """Test registering multiple agent behaviors."""
        arena = AgentArena()
        behavior1 = MockBehavior()
        behavior2 = MockBehavior()

        arena.register('agent_001', behavior1)
        arena.register('agent_002', behavior2)

        assert len(arena.behaviors) == 2
        assert arena.behaviors['agent_001'] == behavior1
        assert arena.behaviors['agent_002'] == behavior2

    def test_register_replaces_existing(self):
        """Test that registering same ID replaces existing behavior."""
        arena = AgentArena()
        behavior1 = MockBehavior()
        behavior2 = MockBehavior()

        arena.register('agent_001', behavior1)
        arena.register('agent_001', behavior2)

        assert len(arena.behaviors) == 1
        assert arena.behaviors['agent_001'] == behavior2

    def test_unregister(self):
        """Test unregistering agents."""
        arena = AgentArena()
        behavior = MockBehavior()

        arena.register('agent_001', behavior)
        assert 'agent_001' in arena.behaviors

        arena.unregister('agent_001')
        assert 'agent_001' not in arena.behaviors

    def test_unregister_nonexistent(self):
        """Test unregistering nonexistent agent doesn't error."""
        arena = AgentArena()
        # Should not raise
        arena.unregister('nonexistent')

    def test_get_registered_agents(self):
        """Test getting list of registered agents."""
        arena = AgentArena()
        behavior1 = MockBehavior()
        behavior2 = MockBehavior()

        assert arena.get_registered_agents() == []

        arena.register('agent_001', behavior1)
        arena.register('agent_002', behavior2)

        agents = arena.get_registered_agents()
        assert len(agents) == 2
        assert 'agent_001' in agents
        assert 'agent_002' in agents

    def test_get_behavior(self):
        """Test getting behavior for an agent."""
        arena = AgentArena()
        behavior = MockBehavior()

        arena.register('agent_001', behavior)

        assert arena.get_behavior('agent_001') == behavior
        assert arena.get_behavior('nonexistent') is None

    def test_is_running(self):
        """Test running state tracking."""
        arena = AgentArena()
        assert not arena.is_running()

        # We can't easily test running state without actually starting the server
        # Just verify the property exists and returns False initially

    def test_run_without_connection_raises(self):
        """Test that run() raises if not connected."""
        arena = AgentArena()

        with pytest.raises(RuntimeError, match="Not connected"):
            arena.run()

    def test_run_async_without_connection_raises(self):
        """Test that run_async() raises if not connected."""
        import asyncio

        arena = AgentArena()

        with pytest.raises(RuntimeError, match="Not connected"):
            asyncio.run(arena.run_async())

    def test_stop(self):
        """Test stopping arena."""
        arena = AgentArena()

        # Should not raise even if not running
        arena.stop()

        assert not arena.is_running()


# Integration tests for IPC converters

from ipc.converters import decision_to_action, perception_to_observation
from ipc.messages import PerceptionMessage


class TestIPCConverters:
    """Tests for IPC converter functions."""

    def test_perception_to_observation_minimal(self):
        """Test converting minimal perception to observation."""
        perception = PerceptionMessage(
            agent_id="agent_001",
            tick=10,
            position=[1.0, 2.0, 3.0],
            rotation=[0.0, 90.0, 0.0],
        )

        obs = perception_to_observation(perception)

        assert obs.agent_id == "agent_001"
        assert obs.tick == 10
        assert obs.position == (1.0, 2.0, 3.0)
        assert obs.rotation == (0.0, 90.0, 0.0)
        assert obs.health == 100.0
        assert obs.energy == 100.0

    def test_perception_to_observation_with_custom_data(self):
        """Test converting perception with custom data."""
        perception = PerceptionMessage(
            agent_id="agent_001",
            tick=10,
            position=[1.0, 2.0, 3.0],
            rotation=[0.0, 0.0, 0.0],
            custom_data={
                "nearby_resources": [
                    {
                        "name": "apple",
                        "type": "food",
                        "position": [5.0, 0.0, 3.0],
                        "distance": 4.1,
                    }
                ],
                "nearby_hazards": [
                    {
                        "name": "lava",
                        "type": "environmental",
                        "position": [10.0, 0.0, 10.0],
                        "distance": 12.7,
                        "damage": 50.0,
                    }
                ],
                "custom_field": "value",
            },
        )

        obs = perception_to_observation(perception)

        assert len(obs.nearby_resources) == 1
        assert obs.nearby_resources[0].name == "apple"
        assert obs.nearby_resources[0].position == (5.0, 0.0, 3.0)

        assert len(obs.nearby_hazards) == 1
        assert obs.nearby_hazards[0].name == "lava"
        assert obs.nearby_hazards[0].damage == 50.0

        assert obs.custom["custom_field"] == "value"
        assert "nearby_resources" not in obs.custom
        assert "nearby_hazards" not in obs.custom

    def test_perception_to_observation_with_inventory(self):
        """Test converting perception with inventory."""
        perception = PerceptionMessage(
            agent_id="agent_001",
            tick=10,
            position=[0.0, 0.0, 0.0],
            rotation=[0.0, 0.0, 0.0],
            inventory=[
                {"id": "item_1", "name": "sword", "quantity": 1},
                {"id": "item_2", "name": "potion", "quantity": 5},
            ],
        )

        obs = perception_to_observation(perception)

        assert len(obs.inventory) == 2
        assert obs.inventory[0].name == "sword"
        assert obs.inventory[0].quantity == 1
        assert obs.inventory[1].name == "potion"
        assert obs.inventory[1].quantity == 5

    def test_perception_to_observation_with_entities(self):
        """Test converting perception with visible entities."""
        perception = PerceptionMessage(
            agent_id="agent_001",
            tick=10,
            position=[0.0, 0.0, 0.0],
            rotation=[0.0, 0.0, 0.0],
            visible_entities=[
                {
                    "id": "tree_1",
                    "type": "obstacle",
                    "position": [3.0, 0.0, 4.0],
                    "distance": 5.0,
                    "metadata": {"height": 10},
                }
            ],
        )

        obs = perception_to_observation(perception)

        assert len(obs.visible_entities) == 1
        assert obs.visible_entities[0].id == "tree_1"
        assert obs.visible_entities[0].type == "obstacle"
        assert obs.visible_entities[0].distance == 5.0
        assert obs.visible_entities[0].metadata["height"] == 10

    def test_decision_to_action(self):
        """Test converting decision to action message."""
        decision = AgentDecision(
            tool="move_to",
            params={"target_position": [10.0, 0.0, 5.0], "speed": 2.0},
            reasoning="Moving to resource",
        )

        action = decision_to_action(decision, "agent_001", 15)

        assert action.agent_id == "agent_001"
        assert action.tick == 15
        assert action.tool == "move_to"
        assert action.params == {"target_position": [10.0, 0.0, 5.0], "speed": 2.0}
        assert action.reasoning == "Moving to resource"

    def test_decision_to_action_idle(self):
        """Test converting idle decision to action."""
        decision = AgentDecision.idle()

        action = decision_to_action(decision, "agent_001", 5)

        assert action.tool == "idle"
        assert action.params == {}
        assert action.reasoning == ""

    def test_decision_to_action_no_reasoning(self):
        """Test converting decision without reasoning."""
        decision = AgentDecision(
            tool="pickup",
            params={"item_id": "apple"},
        )

        action = decision_to_action(decision, "agent_001", 10)

        assert action.tool == "pickup"
        assert action.reasoning == ""
