"""
Generic semantic memory layer for any domain.

This provides a middle layer between raw vector storage (LongTermMemory)
and domain-specific adapters (like RAGMemory). It works with any Python
objects by using converter functions.
"""

import logging
from collections.abc import Callable
from typing import Any, Generic, TypeVar

from .long_term_memory import LongTermMemory

logger = logging.getLogger(__name__)

# Generic type for objects stored in memory
T = TypeVar("T")


class SemanticMemory(Generic[T]):
    """
    Generic semantic memory that works with any type of object.

    Uses converter functions to transform objects to/from text representations
    suitable for vector embedding and retrieval.

    This layer provides:
    - Object → text conversion for embedding
    - Object → metadata extraction
    - Dictionary → object reconstruction
    - Query interface that returns typed objects

    Example:
        >>> # Define converters for your domain
        >>> def log_to_text(log):
        ...     return f"{log.level}: {log.message}"
        >>>
        >>> def log_to_metadata(log):
        ...     return {"level": log.level, "timestamp": log.timestamp}
        >>>
        >>> # Create memory
        >>> memory = SemanticMemory(
        ...     to_text=log_to_text,
        ...     to_metadata=log_to_metadata,
        ...     embedding_model="all-MiniLM-L6-v2"
        ... )
        >>>
        >>> # Store objects
        >>> memory.store(log_entry)
        >>>
        >>> # Query returns raw results
        >>> results = memory.query("network errors", k=5)
    """

    def __init__(
        self,
        to_text: Callable[[T], str],
        to_metadata: Callable[[T], dict[str, Any]] | None = None,
        from_dict: Callable[[dict[str, Any]], T] | None = None,
        embedding_model: str = "all-MiniLM-L6-v2",
        index_type: str = "Flat",
        persist_path: str | None = None,
        **ltm_kwargs,
    ):
        """
        Initialize generic semantic memory.

        Args:
            to_text: Function to convert object → text for embedding
            to_metadata: Optional function to extract metadata from object
            from_dict: Optional function to reconstruct object from stored dict
            embedding_model: Sentence transformer model name
            index_type: FAISS index type ("Flat", "FlatIP", "IVF100", etc.)
            persist_path: Optional path for persistence
            **ltm_kwargs: Additional kwargs passed to LongTermMemory

        Note:
            - to_text is required for storage and querying
            - to_metadata is optional (defaults to empty dict)
            - from_dict is only required if you use query_objects()
        """
        self.to_text = to_text
        self.to_metadata = to_metadata or (lambda obj: {})
        self.from_dict = from_dict

        # Initialize underlying vector store
        self.long_term_memory = LongTermMemory(
            embedding_model=embedding_model,
            index_type=index_type,
            persist_path=persist_path,
            **ltm_kwargs,
        )

        logger.info(
            f"Initialized SemanticMemory with {embedding_model} "
            f"(converter: {to_text.__name__ if hasattr(to_text, '__name__') else 'lambda'})"
        )

    def store(self, obj: T, additional_metadata: dict[str, Any] | None = None) -> str:
        """
        Store an object in semantic memory.

        Args:
            obj: Object to store
            additional_metadata: Optional extra metadata to merge with object metadata

        Returns:
            Unique memory ID (UUID)

        Example:
            >>> memory_id = memory.store(my_object)
            >>> # Or with extra metadata
            >>> memory_id = memory.store(my_object, {"source": "sensor_1"})
        """
        # Convert object to text for embedding
        text = self.to_text(obj)

        # Extract metadata from object
        metadata = self.to_metadata(obj)

        # Merge additional metadata if provided
        if additional_metadata:
            metadata.update(additional_metadata)

        # Store in vector store
        memory_id = self.long_term_memory.store_memory(text, metadata)

        logger.debug(f"Stored object as memory {memory_id}")
        return memory_id

    def query(
        self, query_text: str, k: int = 5, threshold: float | None = None
    ) -> list[dict[str, Any]]:
        """
        Query semantic memory and get raw results.

        Args:
            query_text: Natural language query
            k: Number of results to return
            threshold: Optional similarity threshold

        Returns:
            List of dictionaries with keys: id, text, metadata, score, distance

        Example:
            >>> results = memory.query("find errors", k=10)
            >>> for result in results:
            ...     print(result['text'], result['score'])
        """
        return self.long_term_memory.query_memory(query_text, k, threshold)

    def query_objects(self, query_text: str, k: int = 5, threshold: float | None = None) -> list[T]:
        """
        Query semantic memory and reconstruct typed objects.

        Requires that from_dict converter was provided during initialization.

        Args:
            query_text: Natural language query
            k: Number of results to return
            threshold: Optional similarity threshold

        Returns:
            List of reconstructed objects of type T

        Raises:
            ValueError: If from_dict converter not provided

        Example:
            >>> objects = memory.query_objects("find errors", k=10)
            >>> for obj in objects:
            ...     print(obj.level, obj.message)  # Type-safe!
        """
        if not self.from_dict:
            raise ValueError(
                "query_objects() requires from_dict converter. "
                "Either provide from_dict during initialization, or use query() instead."
            )

        # Get raw results
        results = self.query(query_text, k, threshold)

        # Reconstruct objects
        objects = []
        for result in results:
            try:
                obj = self.from_dict(result)
                objects.append(obj)
            except Exception as e:
                logger.warning(f"Failed to reconstruct object from memory {result['id']}: {e}")

        return objects

    def recall_by_id(self, memory_id: str) -> dict[str, Any] | None:
        """
        Retrieve a specific memory by ID.

        Args:
            memory_id: UUID of the memory

        Returns:
            Memory dictionary or None if not found

        Example:
            >>> memory = memory.recall_by_id(memory_id)
            >>> if memory:
            ...     print(memory['text'])
        """
        return self.long_term_memory.recall_by_id(memory_id)

    def get_all_memories(self) -> list[dict[str, Any]]:
        """
        Get all stored memories (without embeddings).

        Returns:
            List of all memory dictionaries

        Example:
            >>> all_memories = memory.get_all_memories()
            >>> print(f"Total: {len(all_memories)}")
        """
        return self.long_term_memory.get_all_memories()

    def clear(self) -> None:
        """
        Clear all stored memories.

        Example:
            >>> memory.clear()
            >>> assert len(memory) == 0
        """
        self.long_term_memory.clear_memories()
        logger.info("Cleared all semantic memories")

    def save(self, filepath: str | None = None) -> None:
        """
        Save memory to disk.

        Args:
            filepath: Optional path (uses persist_path if None)

        Example:
            >>> memory.save("./data/my_memory.faiss")
        """
        self.long_term_memory.save(filepath)

    def load(self, filepath: str | None = None) -> None:
        """
        Load memory from disk.

        Args:
            filepath: Optional path (uses persist_path if None)

        Example:
            >>> memory.load("./data/my_memory.faiss")
        """
        self.long_term_memory.load(filepath)

    def __len__(self) -> int:
        """Return the number of stored memories."""
        return len(self.long_term_memory)

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"SemanticMemory("
            f"converter={self.to_text.__name__ if hasattr(self.to_text, '__name__') else 'lambda'}, "
            f"count={len(self)})"
        )


class MemoryConverter:
    """
    Helper class to bundle converter functions together.

    This provides a cleaner way to define converters, especially
    when they share state or need to be reused.

    Example:
        >>> class LogConverter(MemoryConverter):
        ...     def to_text(self, log):
        ...         return f"{log.level}: {log.message}"
        ...
        ...     def to_metadata(self, log):
        ...         return {"level": log.level, "time": log.timestamp}
        ...
        ...     def from_dict(self, data):
        ...         return LogEntry(
        ...             level=data['metadata']['level'],
        ...             message=data['text'].split(': ', 1)[1]
        ...         )
        >>>
        >>> converter = LogConverter()
        >>> memory = SemanticMemory(
        ...     to_text=converter.to_text,
        ...     to_metadata=converter.to_metadata,
        ...     from_dict=converter.from_dict
        ... )
    """

    def to_text(self, obj: T) -> str:
        """Convert object to searchable text."""
        raise NotImplementedError("Subclass must implement to_text()")

    def to_metadata(self, obj: T) -> dict[str, Any]:
        """Extract metadata from object."""
        return {}

    def from_dict(self, data: dict[str, Any]) -> T:
        """Reconstruct object from stored dictionary."""
        raise NotImplementedError("Subclass must implement from_dict()")

    def create_memory(self, **kwargs) -> SemanticMemory[T]:
        """
        Convenience method to create SemanticMemory with this converter.

        Args:
            **kwargs: Passed to SemanticMemory constructor

        Returns:
            Configured SemanticMemory instance
        """
        return SemanticMemory(
            to_text=self.to_text, to_metadata=self.to_metadata, from_dict=self.from_dict, **kwargs
        )
