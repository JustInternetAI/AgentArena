"""
Long-term memory module for Agent Arena.

This module provides a three-layer architecture for memory storage:

Layer 1 (Core): LongTermMemory - Pure vector store (text + metadata)
Layer 2 (Generic): SemanticMemory - Works with any Python objects via converters
Layer 3 (Domain): RAGMemory - Agent-specific observations (in agent_runtime)

Example:
    # Layer 1: Direct vector storage
    >>> from long_term_memory_module import LongTermMemory
    >>> memory = LongTermMemory()
    >>> memory.store_memory("some text", {"key": "value"})

    # Layer 2: Generic object storage
    >>> from long_term_memory_module import SemanticMemory
    >>> memory = SemanticMemory(
    ...     to_text=lambda obj: str(obj),
    ...     to_metadata=lambda obj: {"type": type(obj).__name__}
    ... )
    >>> memory.store(my_object)

    # Layer 3: Domain-specific (see agent_runtime.memory.RAGMemory)
"""

from .long_term_memory import LongTermMemory
from .semantic_memory import MemoryConverter, SemanticMemory

__all__ = ["LongTermMemory", "SemanticMemory", "MemoryConverter"]
__version__ = "0.1.0"
