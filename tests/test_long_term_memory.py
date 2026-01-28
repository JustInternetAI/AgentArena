"""
Unit tests for LongTermMemory implementation.
"""

import tempfile
from pathlib import Path

import numpy as np
import pytest

from long_term_memory_module.long_term_memory import LongTermMemory


class TestLongTermMemoryInitialization:
    """Tests for LongTermMemory initialization."""

    def test_basic_initialization(self):
        """Test basic initialization with defaults."""
        memory = LongTermMemory()
        assert memory.embedding_model_name == "all-MiniLM-L6-v2"
        assert memory.embedding_dim == 384  # MiniLM-L6-v2 dimension
        assert memory.index_type == "Flat"
        assert len(memory) == 0

    def test_custom_embedding_model(self):
        """Test initialization with custom embedding model."""
        memory = LongTermMemory(embedding_model="all-MiniLM-L6-v2")
        assert memory.embedding_model_name == "all-MiniLM-L6-v2"
        assert memory.embedding_dim > 0

    def test_custom_index_type(self):
        """Test initialization with different index types."""
        memory = LongTermMemory(index_type="FlatIP")
        assert memory.index_type == "FlatIP"

    def test_invalid_embedding_model(self):
        """Test that invalid embedding model raises error."""
        with pytest.raises(ValueError, match="Failed to load embedding model"):
            LongTermMemory(embedding_model="invalid-model-name-xyz")

    def test_invalid_index_type(self):
        """Test that invalid index type raises error."""
        with pytest.raises(ValueError, match="Unsupported index type"):
            LongTermMemory(index_type="InvalidIndex")

    def test_persist_path_setting(self):
        """Test that persist_path is properly set."""
        memory = LongTermMemory(persist_path="./data/test.faiss")
        assert memory.persist_path == "./data/test.faiss"


class TestLongTermMemoryStorage:
    """Tests for storing memories."""

    @pytest.fixture
    def memory(self):
        """Create a fresh memory instance for each test."""
        return LongTermMemory()

    def test_store_single_memory(self, memory):
        """Test storing a single memory."""
        memory_id = memory.store_memory("I found berries near the forest.")
        assert memory_id is not None
        assert len(memory) == 1
        assert memory_id in memory.memories

    def test_store_with_metadata(self, memory):
        """Test storing memory with metadata."""
        metadata = {"episode": 42, "reward": 25.0, "outcome": "success"}
        memory_id = memory.store_memory("Successfully avoided hazard.", metadata=metadata)

        stored = memory.memories[memory_id]
        assert stored["text"] == "Successfully avoided hazard."
        assert stored["metadata"] == metadata

    def test_store_multiple_memories(self, memory):
        """Test storing multiple memories."""
        texts = [
            "Found apples in the north.",
            "Discovered water source near rocks.",
            "Encountered dangerous predator in the south.",
        ]

        ids = []
        for text in texts:
            memory_id = memory.store_memory(text)
            ids.append(memory_id)

        assert len(memory) == 3
        assert len(set(ids)) == 3  # All IDs are unique

    def test_store_generates_unique_ids(self, memory):
        """Test that each memory gets a unique ID."""
        id1 = memory.store_memory("Memory one")
        id2 = memory.store_memory("Memory two")
        id3 = memory.store_memory("Memory one")  # Same text, different ID

        assert id1 != id2
        assert id1 != id3
        assert id2 != id3

    def test_store_empty_text(self, memory):
        """Test storing memory with empty text."""
        memory_id = memory.store_memory("")
        assert memory_id is not None
        assert len(memory) == 1

    def test_store_long_text(self, memory):
        """Test storing memory with very long text."""
        long_text = "This is a very long memory. " * 100
        memory_id = memory.store_memory(long_text)
        assert memory_id is not None
        assert memory.memories[memory_id]["text"] == long_text


class TestLongTermMemoryRetrieval:
    """Tests for querying and retrieving memories."""

    @pytest.fixture
    def populated_memory(self):
        """Create memory populated with test data."""
        memory = LongTermMemory()

        # Add diverse memories
        memory.store_memory(
            "I found 5 berries near the forest edge.",
            metadata={"episode": 1, "reward": 10.0},
        )
        memory.store_memory(
            "Discovered a water source near the rocky area.",
            metadata={"episode": 2, "reward": 15.0},
        )
        memory.store_memory(
            "Avoided fire hazard while collecting wood.",
            metadata={"episode": 3, "reward": 20.0},
        )
        memory.store_memory(
            "Successfully crafted a tool using stones.",
            metadata={"episode": 4, "reward": 25.0},
        )
        memory.store_memory(
            "Found more berries in a different location.",
            metadata={"episode": 5, "reward": 12.0},
        )

        return memory

    def test_query_empty_memory(self):
        """Test querying when no memories stored."""
        memory = LongTermMemory()
        results = memory.query_memory("test query")
        assert results == []

    def test_query_basic(self, populated_memory):
        """Test basic similarity search."""
        results = populated_memory.query_memory("Where can I find berries?", k=2)
        assert len(results) == 2
        assert "berries" in results[0]["text"].lower()

    def test_query_returns_correct_structure(self, populated_memory):
        """Test that query results have correct structure."""
        results = populated_memory.query_memory("water", k=1)
        assert len(results) == 1

        result = results[0]
        assert "id" in result
        assert "text" in result
        assert "metadata" in result
        assert "score" in result
        assert "distance" in result

    def test_query_k_parameter(self, populated_memory):
        """Test that k parameter limits results."""
        results = populated_memory.query_memory("collecting resources", k=3)
        assert len(results) <= 3

        results_all = populated_memory.query_memory("collecting resources", k=10)
        assert len(results_all) == 5  # All stored memories

    def test_query_semantic_similarity(self, populated_memory):
        """Test that semantically similar memories rank higher."""
        results = populated_memory.query_memory("How do I avoid dangerous situations?", k=5)

        # The hazard avoidance memory should rank high
        top_texts = [r["text"] for r in results[:2]]
        assert any("hazard" in text.lower() or "avoid" in text.lower() for text in top_texts)

    def test_query_scores_are_reasonable(self, populated_memory):
        """Test that similarity scores are in reasonable range."""
        results = populated_memory.query_memory("berries", k=5)

        for result in results:
            assert "score" in result
            assert result["score"] > 0  # Scores should be positive
            # Note: exact range depends on index type (L2 vs IP)

    def test_query_with_threshold(self, populated_memory):
        """Test filtering results by threshold (if using FlatIP)."""
        memory = LongTermMemory(index_type="FlatIP")

        # Store some memories
        memory.store_memory("Apples are delicious fruits.")
        memory.store_memory("Bananas are yellow and curved.")
        memory.store_memory("The weather is sunny today.")

        # Query with threshold
        results = memory.query_memory("fruit", k=10, threshold=0.3)

        # Should filter out irrelevant memories
        assert len(results) > 0
        for result in results:
            assert result["score"] >= 0.3

    def test_recall_by_id(self, populated_memory):
        """Test retrieving memory by ID."""
        # Get an ID from stored memories
        memory_id = list(populated_memory.memories.keys())[0]

        memory = populated_memory.recall_by_id(memory_id)
        assert memory is not None
        assert memory["id"] == memory_id
        assert "text" in memory
        assert "metadata" in memory

    def test_recall_by_invalid_id(self, populated_memory):
        """Test recalling with invalid ID returns None."""
        memory = populated_memory.recall_by_id("invalid-uuid-12345")
        assert memory is None

    def test_get_all_memories(self, populated_memory):
        """Test retrieving all memories."""
        all_memories = populated_memory.get_all_memories()
        assert len(all_memories) == 5

        for memory in all_memories:
            assert "id" in memory
            assert "text" in memory
            assert "metadata" in memory
            assert "embedding" not in memory  # Embeddings should not be included


class TestLongTermMemoryPersistence:
    """Tests for saving and loading memories."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_save_and_load(self, temp_dir):
        """Test basic save and load functionality."""
        filepath = str(temp_dir / "test_memory.faiss")

        # Create and populate memory
        memory1 = LongTermMemory(persist_path=filepath)
        memory1.store_memory("Memory one", metadata={"id": 1})
        memory1.store_memory("Memory two", metadata={"id": 2})
        memory1.save()

        # Load into new instance
        memory2 = LongTermMemory(persist_path=filepath)
        memory2.load()

        assert len(memory2) == 2
        assert len(memory2.memories) == 2

    def test_save_creates_files(self, temp_dir):
        """Test that save creates index and metadata files."""
        filepath = str(temp_dir / "test_memory.faiss")

        memory = LongTermMemory(persist_path=filepath)
        memory.store_memory("Test memory")
        memory.save()

        # Check that files were created
        assert Path(temp_dir / "test_memory.index").exists()
        assert Path(temp_dir / "test_memory.metadata").exists()

    def test_save_without_path_raises_error(self):
        """Test that save without filepath raises error."""
        memory = LongTermMemory()
        memory.store_memory("Test")

        with pytest.raises(ValueError, match="No filepath provided"):
            memory.save()

    def test_load_without_path_raises_error(self):
        """Test that load without filepath raises error."""
        memory = LongTermMemory()

        with pytest.raises(ValueError, match="No filepath provided"):
            memory.load()

    def test_load_nonexistent_file_raises_error(self, temp_dir):
        """Test that loading nonexistent file raises error."""
        filepath = str(temp_dir / "nonexistent.faiss")
        memory = LongTermMemory(persist_path=filepath)

        with pytest.raises(FileNotFoundError):
            memory.load()

    def test_loaded_memories_are_searchable(self, temp_dir):
        """Test that loaded memories can be queried."""
        filepath = str(temp_dir / "test_memory.faiss")

        # Create and save
        memory1 = LongTermMemory(persist_path=filepath)
        memory1.store_memory("I found berries in the forest.")
        memory1.store_memory("I found water near rocks.")
        memory1.save()

        # Load and query
        memory2 = LongTermMemory(persist_path=filepath)
        memory2.load()

        results = memory2.query_memory("Where are berries?", k=1)
        assert len(results) == 1
        assert "berries" in results[0]["text"].lower()

    def test_save_with_explicit_path(self, temp_dir):
        """Test saving with explicit filepath argument."""
        filepath = str(temp_dir / "explicit.faiss")

        memory = LongTermMemory()
        memory.store_memory("Test memory")
        memory.save(filepath)

        assert Path(temp_dir / "explicit.index").exists()

    def test_load_preserves_metadata(self, temp_dir):
        """Test that metadata is preserved through save/load."""
        filepath = str(temp_dir / "metadata_test.faiss")

        metadata = {"episode": 42, "reward": 100.0, "agent": "test_agent"}

        # Save
        memory1 = LongTermMemory(persist_path=filepath)
        mem_id = memory1.store_memory("Important memory", metadata=metadata)
        memory1.save()

        # Load
        memory2 = LongTermMemory(persist_path=filepath)
        memory2.load()

        loaded_memory = memory2.recall_by_id(mem_id)
        assert loaded_memory["metadata"] == metadata


class TestLongTermMemoryClear:
    """Tests for clearing memories."""

    def test_clear_memories(self):
        """Test clearing all memories."""
        memory = LongTermMemory()

        memory.store_memory("Memory 1")
        memory.store_memory("Memory 2")
        memory.store_memory("Memory 3")

        assert len(memory) == 3

        memory.clear_memories()

        assert len(memory) == 0
        assert len(memory.memories) == 0
        assert len(memory.memory_ids) == 0

    def test_clear_empty_memory(self):
        """Test clearing already empty memory."""
        memory = LongTermMemory()
        memory.clear_memories()  # Should not raise error
        assert len(memory) == 0

    def test_use_after_clear(self):
        """Test that memory can be used after clearing."""
        memory = LongTermMemory()

        memory.store_memory("Before clear")
        memory.clear_memories()
        memory.store_memory("After clear")

        assert len(memory) == 1
        results = memory.query_memory("clear", k=1)
        assert len(results) == 1
        assert "After clear" in results[0]["text"]


class TestLongTermMemoryIndexTypes:
    """Tests for different FAISS index types."""

    def test_flat_l2_index(self):
        """Test Flat L2 index (default)."""
        memory = LongTermMemory(index_type="Flat")
        memory.store_memory("Test memory")

        results = memory.query_memory("test", k=1)
        assert len(results) == 1

    def test_flat_ip_index(self):
        """Test Flat Inner Product index (cosine similarity)."""
        memory = LongTermMemory(index_type="FlatIP")
        memory.store_memory("Test memory for IP index")

        results = memory.query_memory("test", k=1)
        assert len(results) == 1
        # IP returns similarity scores in [-1, 1] range
        assert results[0]["score"] >= -1.0
        assert results[0]["score"] <= 1.0

    def test_ivf_index(self):
        """Test IVF index for approximate search."""
        memory = LongTermMemory(index_type="IVF50")

        # Need enough memories for IVF to work well
        for i in range(60):
            memory.store_memory(f"Memory number {i} with unique content.")

        results = memory.query_memory("unique content", k=5)
        assert len(results) == 5


class TestLongTermMemoryEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_large_number_of_memories(self):
        """Test storing and querying large number of memories."""
        memory = LongTermMemory()

        # Store 1000 memories
        num_memories = 1000
        for i in range(num_memories):
            memory.store_memory(f"Memory {i} about topic {i % 10}")

        assert len(memory) == num_memories

        # Query should still work
        results = memory.query_memory("topic 5", k=10)
        assert len(results) == 10

    def test_special_characters_in_text(self):
        """Test storing memories with special characters."""
        memory = LongTermMemory()

        special_text = "Memory with 特殊字符 and émojis 🚀🌟 and symbols !@#$%^&*()"
        memory_id = memory.store_memory(special_text)

        recalled = memory.recall_by_id(memory_id)
        assert recalled["text"] == special_text

    def test_very_similar_memories(self):
        """Test distinguishing very similar memories."""
        memory = LongTermMemory()

        memory.store_memory("I found red apples in the north.")
        memory.store_memory("I found green apples in the north.")
        memory.store_memory("I found red berries in the south.")

        results = memory.query_memory("red fruit in north", k=3)
        assert len(results) == 3
        # First result should be most relevant
        assert "red apples" in results[0]["text"] or "apples" in results[0]["text"]

    def test_repr(self):
        """Test string representation."""
        memory = LongTermMemory()
        memory.store_memory("Test")

        repr_str = repr(memory)
        assert "LongTermMemory" in repr_str
        assert "count=1" in repr_str


class TestLongTermMemoryPerformance:
    """Performance and benchmark tests."""

    def test_query_latency_1k_memories(self):
        """Test query latency with 1K memories (should be <50ms)."""
        import time

        memory = LongTermMemory()

        # Store 1000 memories
        for i in range(1000):
            memory.store_memory(f"Memory {i} about various topics in the simulation.")

        # Benchmark query time
        start = time.time()
        results = memory.query_memory("simulation topics", k=5)
        elapsed = time.time() - start

        assert len(results) == 5
        # Should be fast (adjust threshold as needed for different hardware)
        assert elapsed < 0.1, f"Query took {elapsed:.3f}s, expected <0.1s"

    def test_storage_efficiency(self):
        """Test that storage is reasonably efficient."""
        memory = LongTermMemory()

        # Store 100 memories
        for i in range(100):
            memory.store_memory(f"Memory number {i} with some content.")

        # Check that we're not using excessive memory
        # Each embedding is 384 floats = 1536 bytes
        # With 100 memories, should be ~150KB plus overhead
        import sys

        size = sys.getsizeof(memory.memories)
        assert size < 1_000_000, f"Memory size {size} bytes seems excessive for 100 entries"
