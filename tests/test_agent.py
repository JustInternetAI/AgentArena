"""
Tests for Agent class.
"""

import pytest
from agent_runtime.agent import Agent, Observation, Action, AgentState


def test_agent_initialization():
    """Test agent creation."""
    agent = Agent(
        agent_id="test_agent",
        goals=["explore", "collect"],
    )

    assert agent.state.agent_id == "test_agent"
    assert len(agent.state.goals) == 2
    assert agent.state.goals[0] == "explore"


def test_agent_perception():
    """Test agent perception."""
    agent = Agent(agent_id="test_agent")

    obs_data = {
        "position": [1.0, 2.0, 3.0],
        "entities": ["tree", "rock"],
    }

    agent.perceive(obs_data, source="vision")

    assert len(agent.state.observations) == 1
    assert agent.state.observations[0].data == obs_data
    assert agent.state.observations[0].source == "vision"


def test_agent_memory_capacity():
    """Test that agent respects memory capacity."""
    agent = Agent(agent_id="test_agent")
    agent.memory_capacity = 5

    # Add more observations than capacity
    for i in range(10):
        agent.perceive({"tick": i})

    # Should only keep last 5
    assert len(agent.state.observations) == 5
    assert agent.state.observations[0].data["tick"] == 5
    assert agent.state.observations[-1].data["tick"] == 9


def test_agent_goals():
    """Test goal management."""
    agent = Agent(agent_id="test_agent")

    agent.add_goal("find resources")
    assert "find resources" in agent.state.goals

    agent.add_goal("build shelter")
    assert len(agent.state.goals) == 2

    agent.clear_goals()
    assert len(agent.state.goals) == 0


def test_agent_context_building():
    """Test context building for LLM."""
    agent = Agent(
        agent_id="test_agent",
        goals=["test goal"],
        tools=["move_to", "pickup_item"],
    )

    agent.perceive({"position": [0, 0, 0]})

    context = agent._build_context()

    assert "test_agent" in context
    assert "test goal" in context
    assert "move_to" in context
    assert "pickup_item" in context


def test_action_parsing():
    """Test parsing LLM response into Action."""
    agent = Agent(agent_id="test_agent")

    # Valid JSON response
    response = '{"tool": "move_to", "params": {"target": [1, 2, 3]}, "reasoning": "test"}'
    action = agent._parse_action(response)

    assert action is not None
    assert action.tool_name == "move_to"
    assert action.parameters["target"] == [1, 2, 3]
    assert action.reasoning == "test"


def test_action_parsing_invalid():
    """Test parsing invalid JSON."""
    agent = Agent(agent_id="test_agent")

    response = "invalid json {"
    action = agent._parse_action(response)

    assert action is None


def test_agent_state():
    """Test agent state retrieval."""
    agent = Agent(
        agent_id="test_agent",
        goals=["goal1"],
    )

    agent.perceive({"test": "data"})

    state = agent.get_state()
    assert isinstance(state, AgentState)
    assert state.agent_id == "test_agent"
    assert len(state.observations) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
