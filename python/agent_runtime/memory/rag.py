"""
RAG (Retrieval-Augmented Generation) memory implementation.

Uses FAISS-based vector store for semantic retrieval of agent observations.
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from .base import AgentMemory

if TYPE_CHECKING:
    from ..schemas import Observation

logger = logging.getLogger(__name__)


class RAGMemory(AgentMemory):
    """
    Vector store memory with semantic retrieval using FAISS.

    This memory system uses vector embeddings and semantic search to retrieve
    the most relevant past observations for the current context. It wraps the
    LongTermMemory class from the memory module.

    Features:
    - Embed observations into vector space using sentence transformers
    - Store embeddings in FAISS vector database
    - Semantic retrieval based on query relevance
    - Configurable similarity threshold and top-k retrieval
    - Persistence for saving/loading memory across sessions

    Example:
        >>> memory = RAGMemory(
        ...     embedding_model="all-MiniLM-L6-v2",
        ...     similarity_threshold=0.3,
        ...     default_k=5,
        ...     persist_path="./data/memory/agent_001.faiss"
        ... )
        >>>
        >>> # Store observations
        >>> memory.store(observation)
        >>>
        >>> # Retrieve relevant observations
        >>> relevant = memory.retrieve(query="found any resources?", limit=3)
        >>>
        >>> # Save to disk
        >>> memory.save()

    Note:
        This class is a wrapper around the standalone LongTermMemory class
        from the memory module. It adapts the LongTermMemory interface to
        work with the AgentMemory base class interface.
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
        Initialize RAGMemory with vector store backend.

        Args:
            embedding_model: Name of sentence-transformers model
            index_type: FAISS index type ("Flat", "FlatIP", "IVF100", etc.)
            similarity_threshold: Minimum similarity score for retrieval (0.0-1.0)
            default_k: Default number of results to return
            persist_path: Path to persist memory index to disk

        Example:
            >>> memory = RAGMemory(
            ...     embedding_model="all-MiniLM-L6-v2",
            ...     index_type="FlatIP",  # Use cosine similarity
            ...     persist_path="./data/memory/explorer.faiss"
            ... )
        """
        # Import here to avoid circular dependency and allow lazy loading
        try:
            from long_term_memory_module.long_term_memory import LongTermMemory
        except ImportError:
            raise ImportError(
                "LongTermMemory not found. Make sure the memory module is installed. "
                "The memory module should be in python/long_term_memory_module/long_term_memory.py"
            )

        self.similarity_threshold = similarity_threshold
        self.default_k = default_k

        # Initialize the underlying long-term memory
        self.long_term_memory = LongTermMemory(
            embedding_model=embedding_model,
            index_type=index_type,
            persist_path=persist_path,
        )

        # Keep track of observation ID to memory ID mapping
        self._observation_to_memory: dict[tuple[str, int], str] = {}

        logger.info(
            f"Initialized RAGMemory with {embedding_model} "
            f"(threshold={similarity_threshold}, k={default_k})"
        )

    def store(self, observation: "Observation") -> None:
        """
        Store an observation in memory with vector embedding.

        The observation is converted to a text representation and embedded
        into the vector space for semantic retrieval.

        Args:
            observation: The observation to store

        Example:
            >>> obs = Observation(
            ...     agent_id="agent_1",
            ...     tick=42,
            ...     position=(10.0, 0.0, 5.0),
            ...     nearby_resources=[ResourceInfo(...)]
            ... )
            >>> memory.store(obs)
        """
        # Convert observation to text
        text = self._observation_to_text(observation)

        # Create metadata
        metadata = {
            "agent_id": observation.agent_id,
            "tick": observation.tick,
            "position": observation.position,
            "health": observation.health,
            "energy": observation.energy,
        }

        # Store in long-term memory
        memory_id = self.long_term_memory.store_memory(text, metadata)

        # Keep mapping for later retrieval
        obs_key = (observation.agent_id, observation.tick)
        self._observation_to_memory[obs_key] = memory_id

        logger.debug(f"Stored observation from tick {observation.tick}")

    def retrieve(self, query: str | None = None, limit: int | None = None) -> list["Observation"]:
        """
        Retrieve observations from memory.

        If query is provided, performs semantic similarity search.
        Otherwise, returns most recent observations.

        Args:
            query: Optional query string for semantic retrieval
            limit: Optional maximum number of observations to return

        Returns:
            List of observations (most recent or most relevant)

        Example:
            >>> # Semantic search
            >>> results = memory.retrieve(
            ...     query="Where can I find resources?",
            ...     limit=3
            ... )
            >>>
            >>> # Get recent observations
            >>> recent = memory.retrieve(limit=5)
        """
        if len(self.long_term_memory) == 0:
            return []

        k = limit or self.default_k

        if query is None:
            # No query provided - return most recent observations
            all_memories = self.long_term_memory.get_all_memories()
            # Sort by tick (most recent first)
            all_memories.sort(key=lambda m: m["metadata"].get("tick", 0), reverse=True)
            memories = all_memories[:k]
        else:
            # Perform semantic search
            memories = self.long_term_memory.query_memory(
                query=query,
                k=k,
                threshold=self.similarity_threshold,
            )

        # Convert memories back to observations
        observations = []
        for mem in memories:
            obs = self._memory_to_observation(mem)
            if obs is not None:
                observations.append(obs)

        return observations

    def summarize(self) -> str:
        """
        Create a text summary of memory contents for LLM context.

        Returns:
            String representation suitable for including in LLM prompts

        Example:
            >>> summary = memory.summarize()
            >>> print(summary)
        """
        if len(self.long_term_memory) == 0:
            return "No observations in memory."

        # Get recent observations
        recent = self.retrieve(limit=5)

        summary_parts = [f"Memory contains {len(self.long_term_memory)} observations."]
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

        Used to reset state between episodes.

        Example:
            >>> memory.clear()
            >>> assert len(memory) == 0
        """
        self.long_term_memory.clear_memories()
        self._observation_to_memory.clear()
        logger.info("Cleared all RAG memories")

    def save(self, filepath: Optional[str] = None) -> None:
        """
        Save memory to disk for persistence.

        Args:
            filepath: Optional path to save to (uses persist_path if None)

        Example:
            >>> memory.save("./data/memory/agent_001.faiss")
        """
        self.long_term_memory.save(filepath)

    def load(self, filepath: Optional[str] = None) -> None:
        """
        Load memory from disk.

        Args:
            filepath: Optional path to load from (uses persist_path if None)

        Example:
            >>> memory.load("./data/memory/agent_001.faiss")
        """
        self.long_term_memory.load(filepath)
        # Rebuild observation mapping
        self._observation_to_memory.clear()
        for mem_id, mem_data in self.long_term_memory.memories.items():
            metadata = mem_data["metadata"]
            if "agent_id" in metadata and "tick" in metadata:
                obs_key = (metadata["agent_id"], metadata["tick"])
                self._observation_to_memory[obs_key] = mem_id

        logger.info(f"Loaded RAG memory with {len(self.long_term_memory)} observations")

    def _observation_to_text(self, observation: "Observation") -> str:
        """
        Convert an observation to a text representation for embedding.

        Args:
            observation: The observation to convert

        Returns:
            Text representation of the observation
        """
        parts = []

        # Basic state
        parts.append(f"At position {observation.position}")
        parts.append(f"with health {observation.health:.0f} and energy {observation.energy:.0f}")

        # Resources
        if observation.nearby_resources:
            resource_desc = ", ".join(
                f"{r.name} at distance {r.distance:.1f}" for r in observation.nearby_resources
            )
            parts.append(f"Nearby resources: {resource_desc}")

        # Hazards
        if observation.nearby_hazards:
            hazard_desc = ", ".join(
                f"{h.name} (damage {h.damage:.0f}) at distance {h.distance:.1f}"
                for h in observation.nearby_hazards
            )
            parts.append(f"Nearby hazards: {hazard_desc}")

        # Inventory
        if observation.inventory:
            inventory_desc = ", ".join(
                f"{item.name} x{item.quantity}" for item in observation.inventory
            )
            parts.append(f"Inventory: {inventory_desc}")

        # Visible entities
        if observation.visible_entities:
            entity_desc = ", ".join(
                f"{e.type} at distance {e.distance:.1f}" for e in observation.visible_entities
            )
            parts.append(f"Visible entities: {entity_desc}")

        return ". ".join(parts) + "."

    def _memory_to_observation(self, memory: dict[str, Any]) -> Optional["Observation"]:
        """
        Convert a memory entry back to an observation.

        Args:
            memory: Memory dictionary from long-term memory

        Returns:
            Observation object or None if conversion fails
        """
        from ..schemas import Observation

        try:
            metadata = memory["metadata"]

            # Create basic observation from metadata
            obs = Observation(
                agent_id=metadata["agent_id"],
                tick=metadata["tick"],
                position=metadata["position"],
                health=metadata.get("health", 100.0),
                energy=metadata.get("energy", 100.0),
            )

            return obs

        except (KeyError, TypeError) as e:
            logger.warning(f"Failed to convert memory to observation: {e}")
            return None

    def __len__(self) -> int:
        """Return the number of stored observations."""
        return len(self.long_term_memory)
