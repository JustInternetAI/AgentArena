"""
Tests for agent memory implementations.
"""

import pytest

from agent_runtime.memory import (
    AgentMemory,
    RAGMemory,
    SlidingWindowMemory,
    SummarizingMemory,
)
from agent_runtime.schemas import HazardInfo, ItemInfo, Observation, ResourceInfo


class TestAgentMemory:
    """Tests for AgentMemory abstract base class."""

    def test_cannot_instantiate_directly(self):
        """Test that AgentMemory cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            AgentMemory()

    def test_requires_method_implementations(self):
        """Test that subclasses must implement all abstract methods."""

        class IncompleteMemory(AgentMemory):
            pass

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteMemory()

    def test_concrete_implementation_works(self):
        """Test that concrete implementation can be instantiated."""

        class ConcreteMemory(AgentMemory):
            def __init__(self):
                self._obs = []

            def store(self, observation):
                self._obs.append(observation)

            def retrieve(self, query=None, limit=None):
                return self._obs

            def summarize(self):
                return f"{len(self._obs)} observations"

            def clear(self):
                self._obs.clear()

        memory = ConcreteMemory()
        assert isinstance(memory, AgentMemory)

        obs = Observation(agent_id="test", tick=0, position=(0.0, 0.0, 0.0))
        memory.store(obs)
        assert len(memory) == 1
        assert memory.summarize() == "1 observations"

        memory.clear()
        assert len(memory) == 0


class TestSlidingWindowMemory:
    """Tests for SlidingWindowMemory implementation."""

    def test_initialization(self):
        """Test basic initialization."""
        memory = SlidingWindowMemory(capacity=5)
        assert memory.capacity == 5
        assert len(memory) == 0

    def test_default_capacity(self):
        """Test default capacity value."""
        memory = SlidingWindowMemory()
        assert memory.capacity == 10

    def test_invalid_capacity(self):
        """Test that invalid capacity raises error."""
        with pytest.raises(ValueError, match="Capacity must be at least 1"):
            SlidingWindowMemory(capacity=0)

        with pytest.raises(ValueError, match="Capacity must be at least 1"):
            SlidingWindowMemory(capacity=-1)

    def test_store_single_observation(self):
        """Test storing a single observation."""
        memory = SlidingWindowMemory(capacity=5)
        obs = Observation(agent_id="agent_1", tick=1, position=(1.0, 0.0, 0.0))

        memory.store(obs)
        assert len(memory) == 1

    def test_store_multiple_observations(self):
        """Test storing multiple observations."""
        memory = SlidingWindowMemory(capacity=5)

        for i in range(3):
            obs = Observation(agent_id="agent_1", tick=i, position=(i, 0.0, 0.0))
            memory.store(obs)

        assert len(memory) == 3

    def test_capacity_enforcement(self):
        """Test that capacity limit is enforced."""
        memory = SlidingWindowMemory(capacity=3)

        # Store 5 observations
        for i in range(5):
            obs = Observation(agent_id="agent_1", tick=i, position=(i, 0.0, 0.0))
            memory.store(obs)

        # Should only keep last 3
        assert len(memory) == 3

        # Verify oldest were discarded
        observations = memory.retrieve()
        assert observations[0].tick == 4  # Most recent first
        assert observations[1].tick == 3
        assert observations[2].tick == 2

    def test_retrieve_all(self):
        """Test retrieving all observations."""
        memory = SlidingWindowMemory(capacity=5)

        for i in range(3):
            obs = Observation(agent_id="agent_1", tick=i, position=(i, 0.0, 0.0))
            memory.store(obs)

        observations = memory.retrieve()
        assert len(observations) == 3
        # Most recent first
        assert observations[0].tick == 2
        assert observations[1].tick == 1
        assert observations[2].tick == 0

    def test_retrieve_with_limit(self):
        """Test retrieving limited number of observations."""
        memory = SlidingWindowMemory(capacity=10)

        for i in range(5):
            obs = Observation(agent_id="agent_1", tick=i, position=(i, 0.0, 0.0))
            memory.store(obs)

        observations = memory.retrieve(limit=2)
        assert len(observations) == 2
        assert observations[0].tick == 4  # Most recent
        assert observations[1].tick == 3

    def test_retrieve_ignores_query(self):
        """Test that retrieve ignores query parameter."""
        memory = SlidingWindowMemory(capacity=5)

        obs = Observation(agent_id="agent_1", tick=1, position=(1.0, 0.0, 0.0))
        memory.store(obs)

        # Query should be ignored
        observations = memory.retrieve(query="some query")
        assert len(observations) == 1

    def test_summarize_empty(self):
        """Test summarize with no observations."""
        memory = SlidingWindowMemory(capacity=5)
        summary = memory.summarize()
        assert "No observations" in summary

    def test_summarize_with_observations(self):
        """Test summarize with observations."""
        memory = SlidingWindowMemory(capacity=5)

        obs1 = Observation(
            agent_id="agent_1",
            tick=1,
            position=(1.0, 0.0, 0.0),
            health=90.0,
            energy=80.0,
        )
        obs2 = Observation(
            agent_id="agent_1",
            tick=2,
            position=(2.0, 0.0, 0.0),
            nearby_resources=[
                ResourceInfo(name="apple", type="food", position=(3.0, 0.0, 0.0), distance=1.0)
            ],
            health=85.0,
            energy=75.0,
        )

        memory.store(obs1)
        memory.store(obs2)

        summary = memory.summarize()
        assert "Tick 1" in summary
        assert "Tick 2" in summary
        assert "apple" in summary
        assert "Health: 85" in summary

    def test_summarize_with_inventory(self):
        """Test summarize includes inventory."""
        memory = SlidingWindowMemory(capacity=5)

        obs = Observation(
            agent_id="agent_1",
            tick=1,
            position=(1.0, 0.0, 0.0),
            inventory=[
                ItemInfo(id="item_1", name="sword", quantity=1),
                ItemInfo(id="item_2", name="potion", quantity=3),
            ],
        )

        memory.store(obs)
        summary = memory.summarize()
        assert "swordx1" in summary
        assert "potionx3" in summary

    def test_summarize_with_hazards(self):
        """Test summarize includes hazards."""
        memory = SlidingWindowMemory(capacity=5)

        obs = Observation(
            agent_id="agent_1",
            tick=1,
            position=(1.0, 0.0, 0.0),
            nearby_hazards=[
                HazardInfo(
                    name="lava", type="environmental", position=(5.0, 0.0, 0.0), distance=4.0, damage=50.0
                )
            ],
        )

        memory.store(obs)
        summary = memory.summarize()
        assert "lava" in summary
        assert "damage: 50" in summary

    def test_clear(self):
        """Test clearing all memories."""
        memory = SlidingWindowMemory(capacity=5)

        for i in range(3):
            obs = Observation(agent_id="agent_1", tick=i, position=(i, 0.0, 0.0))
            memory.store(obs)

        assert len(memory) == 3

        memory.clear()
        assert len(memory) == 0
        assert memory.summarize() == "No observations in memory."


class MockBackend:
    """Mock LLM backend for testing."""

    def __init__(self, response="Test summary"):
        self.response = response
        self.last_prompt = None

    def generate(self, prompt):
        self.last_prompt = prompt
        return self.response


class TestSummarizingMemory:
    """Tests for SummarizingMemory implementation."""

    def test_initialization(self):
        """Test basic initialization."""
        backend = MockBackend()
        memory = SummarizingMemory(backend=backend, buffer_capacity=10, compression_trigger=5)

        assert memory.backend == backend
        assert memory.buffer_capacity == 10
        assert memory.compression_trigger == 5
        assert len(memory) == 0

    def test_default_parameters(self):
        """Test default parameter values."""
        backend = MockBackend()
        memory = SummarizingMemory(backend=backend)

        assert memory.buffer_capacity == 20
        assert memory.compression_trigger == 15

    def test_invalid_parameters(self):
        """Test that invalid parameters raise errors."""
        backend = MockBackend()

        with pytest.raises(ValueError, match="Buffer capacity must be at least 1"):
            SummarizingMemory(backend=backend, buffer_capacity=0)

        with pytest.raises(ValueError, match="Compression trigger must be at least 1"):
            SummarizingMemory(backend=backend, compression_trigger=0)

        with pytest.raises(ValueError, match="Compression trigger must be <= buffer capacity"):
            SummarizingMemory(backend=backend, buffer_capacity=10, compression_trigger=15)

    def test_store_single_observation(self):
        """Test storing a single observation."""
        backend = MockBackend()
        memory = SummarizingMemory(backend=backend, buffer_capacity=10, compression_trigger=5)

        obs = Observation(agent_id="agent_1", tick=1, position=(1.0, 0.0, 0.0))
        memory.store(obs)

        assert len(memory) == 1
        assert len(memory._buffer) == 1

    def test_store_below_compression_trigger(self):
        """Test storing observations below compression trigger."""
        backend = MockBackend()
        memory = SummarizingMemory(backend=backend, buffer_capacity=10, compression_trigger=5)

        for i in range(4):
            obs = Observation(agent_id="agent_1", tick=i, position=(i, 0.0, 0.0))
            memory.store(obs)

        assert len(memory) == 4
        assert len(memory._buffer) == 4
        assert memory._summary == ""  # No compression yet

    def test_compression_trigger(self):
        """Test that compression is triggered at threshold."""
        backend = MockBackend(response="Compressed summary")
        memory = SummarizingMemory(backend=backend, buffer_capacity=10, compression_trigger=3)

        # Store observations up to trigger
        for i in range(3):
            obs = Observation(agent_id="agent_1", tick=i, position=(i, 0.0, 0.0))
            memory.store(obs)

        # Compression should have been triggered
        assert memory._summary == "Compressed summary"
        assert backend.last_prompt is not None
        assert "Summarize" in backend.last_prompt

    def test_compression_keeps_recent_observations(self):
        """Test that compression keeps some recent observations."""
        backend = MockBackend(response="Summary")
        memory = SummarizingMemory(backend=backend, buffer_capacity=10, compression_trigger=5)

        # Store 5 observations to trigger compression
        for i in range(5):
            obs = Observation(agent_id="agent_1", tick=i, position=(i, 0.0, 0.0))
            memory.store(obs)

        # Should keep (buffer_capacity - compression_trigger) = 5 observations
        assert len(memory._buffer) == 5

    def test_multiple_compressions(self):
        """Test multiple compression cycles."""
        backend = MockBackend(response="Summary iteration")
        memory = SummarizingMemory(backend=backend, buffer_capacity=8, compression_trigger=4)

        # First batch
        for i in range(4):
            obs = Observation(agent_id="agent_1", tick=i, position=(i, 0.0, 0.0))
            memory.store(obs)

        first_summary = memory._summary
        assert "Summary iteration" in first_summary

        # Second batch
        for i in range(4, 8):
            obs = Observation(agent_id="agent_1", tick=i, position=(i, 0.0, 0.0))
            memory.store(obs)

        # Should have compressed again
        assert memory._summary != ""

    def test_retrieve_returns_buffer_only(self):
        """Test that retrieve returns only buffer observations."""
        backend = MockBackend()
        memory = SummarizingMemory(backend=backend, buffer_capacity=10, compression_trigger=5)

        for i in range(7):
            obs = Observation(agent_id="agent_1", tick=i, position=(i, 0.0, 0.0))
            memory.store(obs)

        # Retrieve should only return buffer contents
        observations = memory.retrieve()
        assert len(observations) <= len(memory._buffer)

    def test_retrieve_with_limit(self):
        """Test retrieve with limit parameter."""
        backend = MockBackend()
        memory = SummarizingMemory(backend=backend, buffer_capacity=10, compression_trigger=5)

        for i in range(3):
            obs = Observation(agent_id="agent_1", tick=i, position=(i, 0.0, 0.0))
            memory.store(obs)

        observations = memory.retrieve(limit=2)
        assert len(observations) == 2
        assert observations[0].tick == 2  # Most recent first

    def test_summarize_with_no_data(self):
        """Test summarize with no observations."""
        backend = MockBackend()
        memory = SummarizingMemory(backend=backend)

        summary = memory.summarize()
        assert "No observations" in summary

    def test_summarize_with_buffer_only(self):
        """Test summarize with only buffer observations."""
        backend = MockBackend()
        memory = SummarizingMemory(backend=backend, buffer_capacity=10, compression_trigger=5)

        obs = Observation(agent_id="agent_1", tick=1, position=(1.0, 0.0, 0.0))
        memory.store(obs)

        summary = memory.summarize()
        assert "Recent Observations" in summary
        assert "Tick 1" in summary

    def test_summarize_with_compressed_and_buffer(self):
        """Test summarize includes both compressed summary and buffer."""
        backend = MockBackend(response="Old events summary")
        memory = SummarizingMemory(backend=backend, buffer_capacity=10, compression_trigger=3)

        # Trigger compression
        for i in range(3):
            obs = Observation(agent_id="agent_1", tick=i, position=(i, 0.0, 0.0))
            memory.store(obs)

        # Add new observation
        obs = Observation(agent_id="agent_1", tick=10, position=(10.0, 0.0, 0.0))
        memory.store(obs)

        summary = memory.summarize()
        assert "Compressed Memory Summary" in summary
        assert "Old events summary" in summary
        assert "Recent Observations" in summary

    def test_clear(self):
        """Test clearing all memories."""
        backend = MockBackend(response="Summary")
        memory = SummarizingMemory(backend=backend, buffer_capacity=10, compression_trigger=3)

        # Store and compress
        for i in range(5):
            obs = Observation(agent_id="agent_1", tick=i, position=(i, 0.0, 0.0))
            memory.store(obs)

        assert len(memory) > 0
        assert memory._summary != ""

        memory.clear()
        assert len(memory) == 0
        assert memory._summary == ""
        assert len(memory._buffer) == 0

    def test_fallback_compression(self):
        """Test fallback compression when backend fails."""

        class FailingBackend:
            def generate(self, prompt):
                raise Exception("Backend error")

        backend = FailingBackend()
        memory = SummarizingMemory(backend=backend, buffer_capacity=10, compression_trigger=3)

        # Store observations to trigger compression
        for i in range(3):
            obs = Observation(
                agent_id="agent_1",
                tick=i,
                position=(i, 0.0, 0.0),
                nearby_resources=[
                    ResourceInfo(name="wood", type="material", position=(i + 1, 0.0, 0.0), distance=1.0)
                ],
            )
            memory.store(obs)

        # Should use fallback compression
        assert memory._summary != ""
        assert "Ticks" in memory._summary

    def test_fallback_compression_no_backend_generate(self):
        """Test fallback when backend has no generate method."""

        class NoGenerateBackend:
            pass

        backend = NoGenerateBackend()
        memory = SummarizingMemory(backend=backend, buffer_capacity=10, compression_trigger=3)

        for i in range(3):
            obs = Observation(agent_id="agent_1", tick=i, position=(i, 0.0, 0.0))
            memory.store(obs)

        # Should use fallback compression
        assert memory._summary != ""


class TestRAGMemory:
    """Tests for RAGMemory implementation."""

    def test_initialization(self):
        """Test that RAGMemory initializes correctly."""
        memory = RAGMemory()
        assert isinstance(memory, AgentMemory)
        assert len(memory) == 0

    def test_initialization_with_args(self):
        """Test that RAGMemory accepts configuration args."""
        memory = RAGMemory(
            embedding_model="all-MiniLM-L6-v2",
            similarity_threshold=0.5,
            default_k=3
        )
        assert memory.similarity_threshold == 0.5
        assert memory.default_k == 3

    def test_basic_store_and_retrieve(self):
        """Test basic store and retrieve functionality."""
        memory = RAGMemory()

        # Store an observation
        obs = Observation(
            agent_id="test_agent",
            tick=1,
            position=(0.0, 0.0, 0.0),
            health=100.0,
            energy=100.0
        )
        memory.store(obs)

        assert len(memory) == 1

        # Retrieve recent observations
        results = memory.retrieve(limit=5)
        assert len(results) == 1
        assert results[0].agent_id == "test_agent"
