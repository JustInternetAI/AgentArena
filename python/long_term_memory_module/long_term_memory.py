"""
Long-term memory implementation with FAISS vector store.

Provides RAG-based episodic memory storage and retrieval using vector embeddings
for semantic similarity search.
"""

import logging
import pickle
import uuid
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class LongTermMemory:
    """
    Vector-based long-term memory with FAISS for episodic storage and retrieval.

    This class provides semantic similarity search over stored memories using
    sentence embeddings. Memories are indexed by FAISS for efficient retrieval
    and can be persisted to disk for long-term storage.

    Example:
        >>> memory = LongTermMemory(
        ...     embedding_model="all-MiniLM-L6-v2",
        ...     persist_path="./data/memory.faiss"
        ... )
        >>> memory_id = memory.store_memory(
        ...     text="I found 5 berries near the forest edge.",
        ...     metadata={"episode": 42, "reward": 25.0}
        ... )
        >>> results = memory.query_memory("Where can I find berries?", k=3)
        >>> for result in results:
        ...     print(result['text'], result['score'])

    Attributes:
        embedding_model: Name of the sentence-transformers model to use
        embedding_dim: Dimension of the embedding vectors
        index: FAISS index for vector storage
        memories: Dictionary mapping memory IDs to memory data
        persist_path: Path to save/load the memory index
    """

    def __init__(
        self,
        embedding_model: str = "all-MiniLM-L6-v2",
        embedding_dim: int | None = None,
        index_type: str = "Flat",
        persist_path: str | None = None,
    ):
        """
        Initialize the long-term memory system.

        Args:
            embedding_model: Name of sentence-transformers model
            embedding_dim: Dimension of embeddings (auto-detected if None)
            index_type: Type of FAISS index ("Flat", "IVF", etc.)
            persist_path: Path to persist memory index to disk

        Raises:
            ValueError: If embedding_model is invalid or index_type is unsupported
        """
        self.embedding_model_name = embedding_model
        self.index_type = index_type
        self.persist_path = persist_path

        # Initialize embedding model
        try:
            logger.info(f"Loading embedding model: {embedding_model}")
            self.encoder = SentenceTransformer(embedding_model)
            self.embedding_dim = embedding_dim or self.encoder.get_sentence_embedding_dimension()
        except Exception as e:
            raise ValueError(f"Failed to load embedding model '{embedding_model}': {e}")

        # Initialize FAISS index
        self._init_index()

        # Memory storage: {memory_id: {text, embedding, metadata}}
        self.memories: dict[str, dict[str, Any]] = {}
        self.memory_ids: list[str] = []  # Ordered list of IDs matching FAISS index

        logger.info(
            f"Initialized LongTermMemory with {embedding_model} "
            f"(dim={self.embedding_dim}, index={index_type})"
        )

    def _init_index(self) -> None:
        """Initialize the FAISS index based on index_type."""
        if self.index_type == "Flat":
            # Simple brute-force L2 distance (exact search)
            self.index = faiss.IndexFlatL2(self.embedding_dim)
        elif self.index_type == "FlatIP":
            # Inner product (cosine similarity with normalized vectors)
            self.index = faiss.IndexFlatIP(self.embedding_dim)
        elif self.index_type.startswith("IVF"):
            # Inverted file index for larger datasets (approximate search)
            # Format: "IVF<nlist>" e.g., "IVF100"
            try:
                nlist = int(self.index_type[3:]) if len(self.index_type) > 3 else 100
                quantizer = faiss.IndexFlatL2(self.embedding_dim)
                self.index = faiss.IndexIVFFlat(quantizer, self.embedding_dim, nlist)
                self.index.nprobe = 10  # Number of clusters to search
            except ValueError:
                raise ValueError(f"Invalid IVF index format: {self.index_type}")
        else:
            raise ValueError(f"Unsupported index type: {self.index_type}")

        logger.debug(f"Initialized FAISS index: {self.index_type}")

    def store_memory(self, text: str, metadata: dict[str, Any] | None = None) -> str:
        """
        Store a memory with text and optional metadata.

        Args:
            text: The text content of the memory
            metadata: Optional dictionary of metadata (e.g., episode, reward, timestamp)

        Returns:
            Unique memory ID (UUID string)

        Example:
            >>> memory_id = memory.store_memory(
            ...     text="Successfully avoided fire hazard while collecting berries",
            ...     metadata={"episode": 42, "outcome": "success", "reward": 25.0}
            ... )
        """
        # Generate unique ID
        memory_id = str(uuid.uuid4())

        # Generate embedding
        embedding = self.encoder.encode(text, convert_to_numpy=True)
        embedding = np.array(embedding, dtype=np.float32).reshape(1, -1)

        # Normalize for cosine similarity if using FlatIP
        if self.index_type == "FlatIP":
            faiss.normalize_L2(embedding)

        # Train IVF index if needed
        if self.index_type.startswith("IVF") and not self.index.is_trained:
            # IVF indices need training before use
            # Need at least nlist training points (e.g., 50 for IVF50)
            nlist = int(self.index_type[3:]) if len(self.index_type) > 3 else 100

            # Accumulate embeddings until we have enough
            if len(self.memories) + 1 >= nlist:
                # Gather existing embeddings plus new one
                training_vectors = []
                for mem_data in self.memories.values():
                    training_vectors.append(mem_data["embedding"])
                training_vectors.append(embedding[0])
                training_data = np.array(training_vectors, dtype=np.float32)

                # Train the index
                self.index.train(training_data)

                # Re-add all existing vectors to the newly trained index
                for mem_data in self.memories.values():
                    self.index.add(mem_data["embedding"].reshape(1, -1))

                logger.debug(f"Trained IVF index on {len(training_vectors)} vectors")
            else:
                # Not enough vectors yet - will train later
                logger.debug(
                    f"Waiting for more vectors to train IVF ({len(self.memories)+1}/{nlist})"
                )

        # Add to FAISS index (only if trained, or if not an IVF index)
        if not self.index_type.startswith("IVF") or self.index.is_trained:
            self.index.add(embedding)

        # Store memory data
        self.memories[memory_id] = {
            "id": memory_id,
            "text": text,
            "embedding": embedding[0],
            "metadata": metadata or {},
        }
        self.memory_ids.append(memory_id)

        logger.debug(f"Stored memory {memory_id}: {text[:50]}...")
        return memory_id

    def query_memory(
        self,
        query: str,
        k: int = 5,
        threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        """
        Query memories using semantic similarity search.

        Args:
            query: Query text to search for
            k: Number of top results to return
            threshold: Optional similarity threshold (only for FlatIP/cosine similarity)

        Returns:
            List of memory dictionaries with keys: id, text, metadata, score, distance
            Sorted by relevance (highest score/lowest distance first)

        Example:
            >>> results = memory.query_memory("How do I avoid hazards?", k=3)
            >>> for result in results:
            ...     print(f"Score: {result['score']:.3f} - {result['text']}")
        """
        if len(self.memories) == 0:
            logger.warning("No memories stored, returning empty results")
            return []

        # Generate query embedding
        query_embedding = self.encoder.encode(query, convert_to_numpy=True)
        query_embedding = np.array(query_embedding, dtype=np.float32).reshape(1, -1)

        # Normalize for cosine similarity if using FlatIP
        if self.index_type == "FlatIP":
            faiss.normalize_L2(query_embedding)

        # Search FAISS index
        k = min(k, len(self.memories))  # Can't retrieve more than stored
        distances, indices = self.index.search(query_embedding, k)

        # Build results
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:  # FAISS returns -1 for not found
                continue

            memory_id = self.memory_ids[idx]
            memory = self.memories[memory_id]

            # Calculate score (higher is better)
            # For L2 distance: convert to similarity score
            # For IP (cosine): distance is already similarity
            if self.index_type == "FlatIP":
                score = float(dist)  # Already a similarity score [0, 1]
            else:
                # Convert L2 distance to similarity (inverse)
                score = 1.0 / (1.0 + float(dist))

            # Apply threshold if specified
            if threshold is not None and score < threshold:
                continue

            results.append(
                {
                    "id": memory_id,
                    "text": memory["text"],
                    "metadata": memory["metadata"],
                    "score": score,
                    "distance": float(dist),
                }
            )

        logger.debug(f"Query '{query[:30]}...' returned {len(results)} results")
        return results

    def recall_by_id(self, memory_id: str) -> dict[str, Any] | None:
        """
        Retrieve a specific memory by its ID.

        Args:
            memory_id: The UUID of the memory to retrieve

        Returns:
            Memory dictionary with keys: id, text, metadata, or None if not found

        Example:
            >>> memory = memory.recall_by_id("a1b2c3d4-...")
            >>> print(memory['text'])
        """
        if memory_id not in self.memories:
            logger.warning(f"Memory ID {memory_id} not found")
            return None

        memory = self.memories[memory_id]
        return {
            "id": memory["id"],
            "text": memory["text"],
            "metadata": memory["metadata"],
        }

    def get_all_memories(self) -> list[dict[str, Any]]:
        """
        Get all stored memories.

        Returns:
            List of all memory dictionaries (without embeddings)

        Example:
            >>> all_memories = memory.get_all_memories()
            >>> print(f"Total memories: {len(all_memories)}")
        """
        return [
            {"id": mem["id"], "text": mem["text"], "metadata": mem["metadata"]}
            for mem in self.memories.values()
        ]

    def clear_memories(self) -> None:
        """
        Clear all stored memories and reset the index.

        Example:
            >>> memory.clear_memories()
            >>> assert len(memory) == 0
        """
        self.memories.clear()
        self.memory_ids.clear()
        self._init_index()
        logger.info("Cleared all memories")

    def save(self, filepath: str | None = None) -> None:
        """
        Save the memory index and data to disk.

        Args:
            filepath: Path to save to (uses persist_path if None)

        Raises:
            ValueError: If no filepath provided and persist_path not set

        Example:
            >>> memory.save("./data/agent_001_memory.faiss")
        """
        filepath = filepath or self.persist_path
        if filepath is None:
            raise ValueError("No filepath provided and persist_path not set")

        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Save FAISS index
        index_path = str(path.with_suffix(".index"))
        faiss.write_index(self.index, index_path)

        # Save memory metadata (without embeddings to save space)
        metadata_path = str(path.with_suffix(".metadata"))
        metadata = {
            "embedding_model": self.embedding_model_name,
            "embedding_dim": self.embedding_dim,
            "index_type": self.index_type,
            "memory_ids": self.memory_ids,
            "memories": {
                mem_id: {"id": mem["id"], "text": mem["text"], "metadata": mem["metadata"]}
                for mem_id, mem in self.memories.items()
            },
        }

        with open(metadata_path, "wb") as f:
            pickle.dump(metadata, f)

        logger.info(f"Saved {len(self.memories)} memories to {filepath}")

    def load(self, filepath: str | None = None) -> None:
        """
        Load the memory index and data from disk.

        Args:
            filepath: Path to load from (uses persist_path if None)

        Raises:
            ValueError: If no filepath provided and persist_path not set
            FileNotFoundError: If the files don't exist

        Example:
            >>> memory.load("./data/agent_001_memory.faiss")
        """
        filepath = filepath or self.persist_path
        if filepath is None:
            raise ValueError("No filepath provided and persist_path not set")

        path = Path(filepath)
        index_path = str(path.with_suffix(".index"))
        metadata_path = str(path.with_suffix(".metadata"))

        # Load FAISS index
        if not Path(index_path).exists():
            raise FileNotFoundError(f"Index file not found: {index_path}")

        self.index = faiss.read_index(index_path)

        # Load metadata
        if not Path(metadata_path).exists():
            raise FileNotFoundError(f"Metadata file not found: {metadata_path}")

        with open(metadata_path, "rb") as f:
            metadata = pickle.load(f)

        # Verify compatibility
        if metadata["embedding_model"] != self.embedding_model_name:
            logger.warning(
                f"Loaded memory uses different embedding model: "
                f"{metadata['embedding_model']} vs {self.embedding_model_name}"
            )

        if metadata["embedding_dim"] != self.embedding_dim:
            raise ValueError(
                f"Embedding dimension mismatch: "
                f"{metadata['embedding_dim']} vs {self.embedding_dim}"
            )

        # Restore memories (regenerate embeddings if needed)
        self.memory_ids = metadata["memory_ids"]
        self.memories = {}

        for mem_id, mem_data in metadata["memories"].items():
            # Regenerate embedding from text
            embedding = self.encoder.encode(mem_data["text"], convert_to_numpy=True)
            embedding = np.array(embedding, dtype=np.float32)

            self.memories[mem_id] = {
                "id": mem_data["id"],
                "text": mem_data["text"],
                "metadata": mem_data["metadata"],
                "embedding": embedding,
            }

        logger.info(f"Loaded {len(self.memories)} memories from {filepath}")

    def __len__(self) -> int:
        """Return the number of stored memories."""
        return len(self.memories)

    def __repr__(self) -> str:
        """String representation of the memory system."""
        return (
            f"LongTermMemory(model={self.embedding_model_name}, "
            f"dim={self.embedding_dim}, count={len(self.memories)})"
        )
