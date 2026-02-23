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
