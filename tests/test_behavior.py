"""
Tests for agent behavior interfaces.
"""

import pytest

from agent_runtime.behavior import AgentBehavior, SimpleAgentBehavior
from agent_runtime.schemas import (
    AgentDecision,
    ItemInfo,
    Observation,
    ResourceInfo,
    SimpleContext,
    ToolSchema,
)


class TestAgentBehavior:
    """Tests for AgentBehavior abstract base class."""

    def test_cannot_instantiate_directly(self):
        """Test that AgentBehavior cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            AgentBehavior()

    def test_requires_decide_implementation(self):
        """Test that subclasses must implement decide()."""

        class IncompleteAgent(AgentBehavior):
            pass

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteAgent()

    def test_concrete_implementation_works(self):
        """Test that concrete implementation can be instantiated."""

        class ConcreteAgent(AgentBehavior):
            def decide(self, observation, tools):
                return AgentDecision.idle()

        agent = ConcreteAgent()
        assert isinstance(agent, AgentBehavior)

        # Test decide method works
        obs = Observation(agent_id="test", tick=0, position=(0.0, 0.0, 0.0))
        decision = agent.decide(obs, [])
        assert decision.tool == "idle"

    def test_lifecycle_methods_have_defaults(self):
        """Test that lifecycle methods have default implementations."""

        class MinimalAgent(AgentBehavior):
            def decide(self, observation, tools):
                return AgentDecision.idle()

        agent = MinimalAgent()

        # Should not raise - default implementations do nothing
        agent.on_episode_start()
        agent.on_episode_end(success=True)
        agent.on_episode_end(success=False, metrics={"score": 100})
        agent.on_tool_result("move", {"success": True})

    def test_lifecycle_methods_can_be_overridden(self):
        """Test that lifecycle methods can be overridden."""

        class LifecycleAgent(AgentBehavior):
            def __init__(self):
                self.started = False
                self.ended = False
                self.tool_results = []

            def decide(self, observation, tools):
                return AgentDecision.idle()

            def on_episode_start(self):
                self.started = True

            def on_episode_end(self, success, metrics=None):
                self.ended = True
                self.success = success
                self.metrics = metrics

            def on_tool_result(self, tool, result):
                self.tool_results.append((tool, result))

        agent = LifecycleAgent()
        assert not agent.started
        assert not agent.ended

        agent.on_episode_start()
        assert agent.started

        agent.on_tool_result("move", {"distance": 5})
        assert len(agent.tool_results) == 1
        assert agent.tool_results[0] == ("move", {"distance": 5})

        agent.on_episode_end(success=True, metrics={"score": 95})
        assert agent.ended
        assert agent.success is True
        assert agent.metrics == {"score": 95}


class TestSimpleAgentBehavior:
    """Tests for SimpleAgentBehavior simplified interface."""

    def test_cannot_instantiate_directly(self):
        """Test that SimpleAgentBehavior cannot be instantiated without decide()."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            SimpleAgentBehavior()

    def test_requires_decide_implementation(self):
        """Test that subclasses must implement decide()."""

        class IncompleteSimpleAgent(SimpleAgentBehavior):
            pass

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteSimpleAgent()

    def test_concrete_simple_agent_works(self):
        """Test that concrete SimpleAgentBehavior can be instantiated."""

        class ConcreteSimpleAgent(SimpleAgentBehavior):
            def decide(self, context):
                return "idle"

        agent = ConcreteSimpleAgent()
        assert isinstance(agent, SimpleAgentBehavior)
        assert isinstance(agent, AgentBehavior)

        # Test decide method works
        context = SimpleContext(
            position=(0.0, 0.0, 0.0),
            nearby_resources=[],
            nearby_hazards=[],
            inventory=[],
        )
        tool_name = agent.decide(context)
        assert tool_name == "idle"

    def test_system_prompt_default(self):
        """Test that system_prompt has a default value."""

        class SimpleAgent(SimpleAgentBehavior):
            def decide(self, context):
                return "idle"

        agent = SimpleAgent()
        assert agent.system_prompt == "You are an autonomous agent."

    def test_system_prompt_can_be_overridden(self):
        """Test that system_prompt can be overridden."""

        class CustomAgent(SimpleAgentBehavior):
            system_prompt = "You are a foraging agent."

            def decide(self, context):
                return "idle"

        agent = CustomAgent()
        assert agent.system_prompt == "You are a foraging agent."

    def test_memory_capacity_default(self):
        """Test that memory_capacity has a default value."""

        class SimpleAgent(SimpleAgentBehavior):
            def decide(self, context):
                return "idle"

        agent = SimpleAgent()
        assert agent.memory_capacity == 10

    def test_memory_capacity_can_be_overridden(self):
        """Test that memory_capacity can be overridden."""

        class CustomAgent(SimpleAgentBehavior):
            memory_capacity = 20

            def decide(self, context):
                return "idle"

        agent = CustomAgent()
        assert agent.memory_capacity == 20

    def test_goal_setting(self):
        """Test that goals can be set and retrieved."""

        class SimpleAgent(SimpleAgentBehavior):
            def decide(self, context):
                return "idle"

        agent = SimpleAgent()
        assert agent._goal is None

        agent.set_goal("Collect resources")
        assert agent._goal == "Collect resources"

    def test_internal_decide_creates_simple_context(self):
        """Test that _internal_decide creates SimpleContext from Observation."""

        class SimpleAgent(SimpleAgentBehavior):
            def decide(self, context):
                # Store context for verification
                self.last_context = context
                return "idle"

        agent = SimpleAgent()
        agent.set_goal("Test goal")

        obs = Observation(
            agent_id="agent_1",
            tick=5,
            position=(10.0, 0.0, 5.0),
            nearby_resources=[
                ResourceInfo(name="wood", type="material", position=(12.0, 0.0, 6.0), distance=2.2)
            ],
            inventory=[ItemInfo(id="item_1", name="axe", quantity=1)],
        )

        decision = agent._internal_decide(obs, [])

        # Verify context was created correctly
        assert agent.last_context.position == (10.0, 0.0, 5.0)
        assert agent.last_context.tick == 5
        assert agent.last_context.goal == "Test goal"
        assert len(agent.last_context.nearby_resources) == 1
        assert agent.last_context.nearby_resources[0]["name"] == "wood"
        assert "axe" in agent.last_context.inventory

        # Verify decision was returned
        assert decision.tool == "idle"

    def test_memory_management(self):
        """Test that observations are stored and capacity is enforced."""

        class SimpleAgent(SimpleAgentBehavior):
            memory_capacity = 3

            def decide(self, context):
                return "idle"

        agent = SimpleAgent()

        # Add 5 observations
        for i in range(5):
            obs = Observation(agent_id="agent_1", tick=i, position=(i, 0.0, 0.0))
            agent._internal_decide(obs, [])

        # Should only keep last 3
        assert len(agent._observations) == 3
        assert agent._observations[0].tick == 2
        assert agent._observations[1].tick == 3
        assert agent._observations[2].tick == 4

    def test_infer_parameters_move_to_resource(self):
        """Test parameter inference for move_to with nearby resources."""

        class SimpleAgent(SimpleAgentBehavior):
            def decide(self, context):
                return "move_to"

        agent = SimpleAgent()

        context = SimpleContext(
            position=(0.0, 0.0, 0.0),
            nearby_resources=[
                {"name": "apple", "distance": 10.0, "position": (10.0, 0.0, 0.0)},
                {"name": "wood", "distance": 5.0, "position": (5.0, 0.0, 0.0)},
            ],
            nearby_hazards=[],
            inventory=[],
        )

        params = agent._infer_parameters("move_to", context, [])

        # Should target nearest resource (wood at distance 5)
        assert "target_position" in params
        assert params["target_position"] == (5.0, 0.0, 0.0)

    def test_infer_parameters_move_to_no_resources(self):
        """Test parameter inference for move_to with no resources."""

        class SimpleAgent(SimpleAgentBehavior):
            def decide(self, context):
                return "move_to"

        agent = SimpleAgent()

        context = SimpleContext(
            position=(5.0, 2.0, 3.0),
            nearby_resources=[],
            nearby_hazards=[],
            inventory=[],
        )

        params = agent._infer_parameters("move_to", context, [])

        # Should default to current position
        assert params["target_position"] == (5.0, 2.0, 3.0)

    def test_infer_parameters_pickup(self):
        """Test parameter inference for pickup."""

        class SimpleAgent(SimpleAgentBehavior):
            def decide(self, context):
                return "pickup"

        agent = SimpleAgent()

        context = SimpleContext(
            position=(0.0, 0.0, 0.0),
            nearby_resources=[
                {"name": "apple", "distance": 3.0},
                {"name": "wood", "distance": 1.0},
            ],
            nearby_hazards=[],
            inventory=[],
        )

        params = agent._infer_parameters("pickup", context, [])

        # Should pick up nearest resource (wood at distance 1)
        assert params["item_id"] == "wood"

    def test_infer_parameters_pickup_no_resources(self):
        """Test parameter inference for pickup with no resources."""

        class SimpleAgent(SimpleAgentBehavior):
            def decide(self, context):
                return "pickup"

        agent = SimpleAgent()

        context = SimpleContext(
            position=(0.0, 0.0, 0.0),
            nearby_resources=[],
            nearby_hazards=[],
            inventory=[],
        )

        params = agent._infer_parameters("pickup", context, [])

        # Should return empty params
        assert params == {}

    def test_infer_parameters_drop(self):
        """Test parameter inference for drop."""

        class SimpleAgent(SimpleAgentBehavior):
            def decide(self, context):
                return "drop"

        agent = SimpleAgent()

        context = SimpleContext(
            position=(0.0, 0.0, 0.0),
            nearby_resources=[],
            nearby_hazards=[],
            inventory=["sword", "shield", "potion"],
        )

        params = agent._infer_parameters("drop", context, [])

        # Should drop first item
        assert params["item_name"] == "sword"

    def test_infer_parameters_drop_empty_inventory(self):
        """Test parameter inference for drop with empty inventory."""

        class SimpleAgent(SimpleAgentBehavior):
            def decide(self, context):
                return "drop"

        agent = SimpleAgent()

        context = SimpleContext(
            position=(0.0, 0.0, 0.0),
            nearby_resources=[],
            nearby_hazards=[],
            inventory=[],
        )

        params = agent._infer_parameters("drop", context, [])

        # Should return empty params
        assert params == {}

    def test_infer_parameters_use(self):
        """Test parameter inference for use."""

        class SimpleAgent(SimpleAgentBehavior):
            def decide(self, context):
                return "use"

        agent = SimpleAgent()

        context = SimpleContext(
            position=(0.0, 0.0, 0.0),
            nearby_resources=[],
            nearby_hazards=[],
            inventory=["potion", "scroll"],
        )

        params = agent._infer_parameters("use", context, [])

        # Should use first item
        assert params["item_name"] == "potion"

    def test_infer_parameters_idle(self):
        """Test parameter inference for idle (no parameters needed)."""

        class SimpleAgent(SimpleAgentBehavior):
            def decide(self, context):
                return "idle"

        agent = SimpleAgent()

        context = SimpleContext(
            position=(0.0, 0.0, 0.0),
            nearby_resources=[],
            nearby_hazards=[],
            inventory=[],
        )

        params = agent._infer_parameters("idle", context, [])

        # Should return empty params
        assert params == {}

    def test_full_integration(self):
        """Test full integration from observation to decision."""

        class ForagingAgent(SimpleAgentBehavior):
            system_prompt = "You are a foraging agent."

            def decide(self, context):
                if context.nearby_resources:
                    # If far away, move to resource
                    nearest = min(context.nearby_resources, key=lambda r: r["distance"])
                    if nearest["distance"] > 1.0:
                        return "move_to"
                    # If close, pick it up
                    return "pickup"
                return "idle"

        agent = ForagingAgent()
        agent.set_goal("Collect resources")

        # Scenario 1: Resource far away
        obs1 = Observation(
            agent_id="agent_1",
            tick=1,
            position=(0.0, 0.0, 0.0),
            nearby_resources=[
                ResourceInfo(name="apple", type="food", position=(10.0, 0.0, 0.0), distance=10.0)
            ],
        )

        decision1 = agent._internal_decide(obs1, [])
        assert decision1.tool == "move_to"
        assert decision1.params["target_position"] == (10.0, 0.0, 0.0)

        # Scenario 2: Resource close by
        obs2 = Observation(
            agent_id="agent_1",
            tick=2,
            position=(9.5, 0.0, 0.0),
            nearby_resources=[
                ResourceInfo(name="apple", type="food", position=(10.0, 0.0, 0.0), distance=0.5)
            ],
        )

        decision2 = agent._internal_decide(obs2, [])
        assert decision2.tool == "pickup"
        assert decision2.params["item_id"] == "apple"

        # Scenario 3: No resources
        obs3 = Observation(agent_id="agent_1", tick=3, position=(10.0, 0.0, 0.0))

        decision3 = agent._internal_decide(obs3, [])
        assert decision3.tool == "idle"

        # Verify memory
        assert len(agent._observations) == 3
