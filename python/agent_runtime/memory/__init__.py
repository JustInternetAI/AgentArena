"""
Agent memory implementations.

Memory Types:
- SlidingWindowMemory: Simple FIFO buffer of recent observations
- SummarizingMemory: LLM-based compression of old memories
- RAGMemory: Vector-based semantic retrieval (original implementation)
- RAGMemoryV2: Cleaner RAG using three-layer architecture (recommended)
- SpatialMemory: World mapping for tracking object positions (resources, hazards)
"""

from .base import AgentMemory
from .observation_converter import ObservationConverter
from .rag import RAGMemory
from .rag_v2 import RAGMemoryV2
from .sliding_window import SlidingWindowMemory
from .spatial import SpatialMemory, SpatialQueryResult
from .summarizing import SummarizingMemory

__all__ = [
    "AgentMemory",
    "SlidingWindowMemory",
    "SummarizingMemory",
    "RAGMemory",
    "RAGMemoryV2",
    "ObservationConverter",
    "SpatialMemory",
    "SpatialQueryResult",
]
