"""
RAG (Retrieval-Augmented Generation) memory implementation v2.

This is Layer 3 (Domain-Specific) - uses SemanticMemory (Layer 2) with
ObservationConverter for agent-specific memory.

This version is cleaner and more maintainable than the original rag.py,
leveraging the three-layer architecture.
"""

import logging
from typing import TYPE_CHECKING

from .base import AgentMemory
from .observation_converter import ObservationConverter

if TYPE_CHECKING:
    from ..schemas import Observation

logger = logging.getLogger(__name__)


class RAGMemoryV2(AgentMemory):
    """
    Vector store memory with semantic retrieval for agent observations.

    This is a thin adapter that:
    1. Uses SemanticMemory (Layer 2) for generic object storage
    2. Uses ObservationConverter to handle agent-specific logic
    3. Implements AgentMemory interface for agent runtime compatibility

    Example:
        >>> memory = RAGMemoryV2(
        ...     embedding_model="all-MiniLM-L6-v2",
        ...     index_type="FlatIP",
        ...     persist_path="./data/memory/agent_001.faiss"
        ... )
        >>>
        >>> # Store observations
        >>> memory.store(observation)
        >>>
        >>> # Semantic retrieval
        >>> relevant = memory.retrieve(query="Where can I find food?", limit=3)
        >>>
        >>> # Persistence
        >>> memory.save()
    """

    def __init__(
        self,
        embedding_model: str = "all-MiniLM-L6-v2",
        index_type: str = "Flat",
        similarity_threshold: float = 0.3,
        default_k: int = 5,
        persist_path: str | None = None,
    ):
        """
        Initialize RAG memory with semantic search.

        Args:
            embedding_model: Sentence transformer model name
            index_type: FAISS index type ("Flat", "FlatIP", "IVF100", etc.)
            similarity_threshold: Minimum similarity score for retrieval
            default_k: Default number of results to return
            persist_path: Optional path for persistence

        Example:
            >>> memory = RAGMemoryV2(
            ...     embedding_model="all-MiniLM-L6-v2",
            ...     index_type="FlatIP",  # Cosine similarity
            ...     persist_path="./data/memory/explorer.faiss"
            ... )
        """
        from long_term_memory_module import SemanticMemory

        # Create observation converter
        self.converter = ObservationConverter()

        # Create semantic memory with observation converter
        self.semantic_memory = SemanticMemory(
            to_text=self.converter.to_text,
            to_metadata=self.converter.to_metadata,
            from_dict=self.converter.from_dict,
            embedding_model=embedding_model,
            index_type=index_type,
            persist_path=persist_path,
        )

        self.similarity_threshold = similarity_threshold
        self.default_k = default_k

        logger.info(
            f"Initialized RAGMemoryV2 with {embedding_model} "
            f"(threshold={similarity_threshold}, k={default_k})"
        )

    def store(self, observation: "Observation") -> None:
        """
        Store an observation in memory.

        Args:
            observation: The observation to store

        Example:
            >>> memory.store(observation)
        """
        self.semantic_memory.store(observation)
        logger.debug(f"Stored observation from tick {observation.tick}")

    def retrieve(self, query: str | None = None, limit: int | None = None) -> list["Observation"]:
        """
        Retrieve observations from memory.

        If query is provided, performs semantic search.
        Otherwise, returns most recent observations.

        Args:
            query: Optional query string for semantic retrieval
            limit: Optional maximum number of observations to return

        Returns:
            List of observations (most recent or most relevant)

        Example:
            >>> # Semantic search
            >>> results = memory.retrieve(query="Where are resources?", limit=3)
            >>>
            >>> # Get recent observations
            >>> recent = memory.retrieve(limit=5)
        """
        k = limit or self.default_k

        if query is None:
            # No query - return most recent observations
            all_memories = self.semantic_memory.get_all_memories()

            # Sort by tick (most recent first)
            all_memories.sort(key=lambda m: m["metadata"].get("tick", 0), reverse=True)

            # Take top k
            memories = all_memories[:k]

            # Convert to observations
            observations = []
            for mem in memories:
                obs = self.converter.from_dict(mem)
                if obs:
                    observations.append(obs)

            return observations
        else:
            # Semantic search - use query_objects for type safety
            try:
                observations = self.semantic_memory.query_objects(
                    query_text=query, k=k, threshold=self.similarity_threshold
                )
                return observations
            except Exception as e:
                logger.error(f"Error during semantic retrieval: {e}")
                return []

    def summarize(self) -> str:
        """
        Create a text summary of memory contents for LLM context.

        Returns:
            String representation suitable for LLM prompts

        Example:
            >>> context = memory.summarize()
            >>> print(context)
        """
        if len(self.semantic_memory) == 0:
            return "No observations in memory."

        # Get recent observations
        recent = self.retrieve(limit=5)

        summary_parts = [f"Memory contains {len(self.semantic_memory)} observations."]
        summary_parts.append("\nMost recent observations:")

        for i, obs in enumerate(recent, 1):
            summary_parts.append(f"\n{i}. Tick {obs.tick}:")
            summary_parts.append(f"   Position: {obs.position}")
            summary_parts.append(f"   Health: {obs.health:.0f}, Energy: {obs.energy:.0f}")

            if obs.nearby_resources:
                resources = ", ".join(r.name for r in obs.nearby_resources)
                summary_parts.append(f"   Resources: {resources}")

            if obs.nearby_hazards:
                hazards = ", ".join(h.name for h in obs.nearby_hazards)
                summary_parts.append(f"   Hazards: {hazards}")

            if obs.inventory:
                items = ", ".join(f"{item.name}x{item.quantity}" for item in obs.inventory)
                summary_parts.append(f"   Inventory: {items}")

        return "".join(summary_parts)

    def clear(self) -> None:
        """
        Clear all stored memories.

        Example:
            >>> memory.clear()
            >>> assert len(memory) == 0
        """
        self.semantic_memory.clear()
        logger.info("Cleared all RAG memories")

    def save(self, filepath: str | None = None) -> None:
        """
        Save memory to disk for persistence.

        Args:
            filepath: Optional path to save to (uses persist_path if None)

        Example:
            >>> memory.save("./data/memory/agent_001.faiss")
        """
        self.semantic_memory.save(filepath)

    def load(self, filepath: str | None = None) -> None:
        """
        Load memory from disk.

        Args:
            filepath: Optional path to load from (uses persist_path if None)

        Example:
            >>> memory.load("./data/memory/agent_001.faiss")
        """
        self.semantic_memory.load(filepath)
        logger.info(f"Loaded RAG memory with {len(self.semantic_memory)} observations")

    def dump(self) -> dict:
        """
        Dump full memory state for inspection/debugging.

        Returns:
            Dictionary containing memory state (limited to recent observations
            for practical JSON size)
        """
        recent = self.retrieve(limit=50)
        return {
            "type": "RAGMemoryV2",
            "stats": {
                "observation_count": len(self.semantic_memory),
            },
            "recent_observations": [obs.to_dict() for obs in recent],
        }

    def __len__(self) -> int:
        """Return the number of stored observations."""
        return len(self.semantic_memory)

    def __repr__(self) -> str:
        """String representation."""
        return f"RAGMemoryV2(count={len(self)})"
