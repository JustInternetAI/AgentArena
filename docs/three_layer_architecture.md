# Three-Layer Memory Architecture

## Overview

Agent Arena's memory system uses a **three-layer architecture** that cleanly separates concerns and maximizes reusability:

1. **Layer 1: Pure Vector Store** (`LongTermMemory`) - Generic text + metadata
2. **Layer 2: Generic Object Storage** (`SemanticMemory`) - Works with any Python objects
3. **Layer 3: Domain-Specific** (`RAGMemoryV2`) - Agent observations

This architecture allows the core vector store to be completely generic and reusable, while providing convenient domain-specific interfaces for agents.

## Architecture Diagram

```
+---------------------------------------------------------------+
|  LAYER 3: Domain-Specific (agent_runtime.memory)            |
|                                                               |
|  RAGMemoryV2          ObservationConverter                   |
|  - Agent observations - to_text()                            |
|  - AgentMemory API    - to_metadata()                        |
|  - save/load          - from_dict()                          |
+---------------------------+-----------------------------------+
                            | Uses
+---------------------------+-----------------------------------+
|  LAYER 2: Generic Object Storage                             |
|                                                               |
|  SemanticMemory<T>    MemoryConverter                        |
|  - store(object)      - Abstract base class                  |
|  - query_objects()    - Helper for converters                |
|  - Type-safe          - create_memory()                      |
+---------------------------+-----------------------------------+
                            | Uses
+---------------------------+-----------------------------------+
|  LAYER 1: Pure Vector Store                                  |
|                                                               |
|  LongTermMemory                                              |
|  - store_memory(text, metadata)                              |
|  - query_memory(query, k)                                    |
|  - FAISS + sentence-transformers                             |
+---------------------------------------------------------------+
```

## Layer 1: Pure Vector Store

### `LongTermMemory`

**Location**: `python/long_term_memory_module/long_term_memory.py`

**Purpose**: Generic vector storage with no domain knowledge.

**Key Features**:
- Takes plain `text` and `metadata`
- Generates embeddings using sentence-transformers
- Stores vectors in FAISS for similarity search
- Completely domain-agnostic
- Can be used standalone

**API**:
```python
from long_term_memory_module import LongTermMemory

memory = LongTermMemory(
    embedding_model="all-MiniLM-L6-v2",
    index_type="FlatIP"
)

# Store plain text
memory_id = memory.store_memory(
    text="Found valuable resources at coordinates 10,5",
    metadata={"type": "discovery", "importance": "high"}
)

# Query by similarity
results = memory.query_memory("Where are resources?", k=5)
# Returns: [{'id': ..., 'text': ..., 'metadata': ..., 'score': ...}, ...]

# Recall by ID
memory = memory.recall_by_id(memory_id)

# Persistence
memory.save("./data/memory.faiss")
memory.load("./data/memory.faiss")
```

**When to use directly**:
- Simple text storage without objects
- Custom domains that don't fit Layer 2/3
- Maximum control over text representation

---

## Layer 2: Generic Object Storage

### `SemanticMemory<T>`

**Location**: `python/long_term_memory_module/semantic_memory.py`

**Purpose**: Generic memory for **any** Python objects using converter functions.

**Key Features**:
- Type-safe generic storage (`SemanticMemory[T]`)
- Uses converter functions to transform objects
- Works with ANY domain (logs, events, metrics, etc.)
- Queries return typed objects

**API**:
```python
from long_term_memory_module import SemanticMemory

# Define converters
def to_text(event):
    return f"{event.type}: {event.description}"

def to_metadata(event):
    return {"type": event.type, "timestamp": event.timestamp}

def from_dict(data):
    return Event(type=data['metadata']['type'], ...)

# Create memory
memory = SemanticMemory(
    to_text=to_text,
    to_metadata=to_metadata,
    from_dict=from_dict,
    embedding_model="all-MiniLM-L6-v2"
)

# Store objects
memory.store(my_event)

# Query returns raw dicts
results = memory.query("error events", k=5)

# Query returns typed objects
events = memory.query_objects("error events", k=5)
# Type: list[Event]
```

### `MemoryConverter`

**Purpose**: Helper base class for bundling converters.

**Example**:
```python
from long_term_memory_module import MemoryConverter

class LogConverter(MemoryConverter):
    def to_text(self, log):
        return f"{log.level}: {log.message}"

    def to_metadata(self, log):
        return {"level": log.level, "timestamp": log.timestamp}

    def from_dict(self, data):
        return LogEntry(...)

# Use converter
converter = LogConverter()
memory = converter.create_memory(embedding_model="all-MiniLM-L6-v2")
```

**When to use**:
- Storing custom Python objects
- Need type-safe retrieval
- Want to separate converter logic
- Multiple domains beyond agents

---

## Layer 3: Domain-Specific (Agent Runtime)

### `RAGMemoryV2`

**Location**: `python/agent_runtime/memory/rag_v2.py`

**Purpose**: Specialized memory for Agent Arena observations.

**Key Features**:
- Works with `Observation` objects
- Implements `AgentMemory` interface
- Uses `ObservationConverter` internally
- Optimized for agent decision-making

**API**:
```python
from agent_runtime.memory import RAGMemoryV2

memory = RAGMemoryV2(
    embedding_model="all-MiniLM-L6-v2",
    index_type="FlatIP",
    similarity_threshold=0.3
)

# Store observations
memory.store(observation)

# Semantic query
relevant = memory.retrieve(query="Where is food?", limit=5)
# Returns: list[Observation]

# Recency-based (no query)
recent = memory.retrieve(limit=5)

# Get summary for LLM
context = memory.summarize()

# Persistence
memory.save("./data/memory/agent_001.faiss")
```

### `ObservationConverter`

**Location**: `python/agent_runtime/memory/observation_converter.py`

**Purpose**: Converts observations to/from semantic memory format.

**Methods**:
- `to_text(observation)`: Creates searchable text representation
- `to_metadata(observation)`: Extracts structured metadata
- `from_dict(data)`: Reconstructs observation from stored data

**Example**:
```python
from agent_runtime.memory import ObservationConverter

converter = ObservationConverter()

# Convert to text for embedding
text = converter.to_text(observation)
# "At position (10.0, 0.0, 5.0) with health 100 and energy 90.
#  Nearby resources: berries at distance 2.0. ..."

# Extract metadata
metadata = converter.to_metadata(observation)
# {'agent_id': 'agent_1', 'tick': 42, 'position': (10, 0, 5), ...}

# Reconstruct observation
obs = converter.from_dict(memory_result)
```

**When to use**:
- Creating agent behaviors
- Need semantic search over observations
- Want automatic storage on every tick
- Integration with agent runtime

---

## Comparison: Which Layer to Use?

| Use Case | Layer | Class | Example |
|----------|-------|-------|---------|
| Store plain text logs | 1 | `LongTermMemory` | System logs, notes |
| Store custom objects (events, metrics) | 2 | `SemanticMemory` | Game events, analytics |
| Store agent observations | 3 | `RAGMemoryV2` | Agent decision-making |
| Maximum flexibility | 1 | `LongTermMemory` | Custom domain |
| Type-safe object queries | 2 | `SemanticMemory` | Domain objects |
| Agent-specific convenience | 3 | `RAGMemoryV2` | Agent behaviors |

---

## Creating Custom Memories for New Domains

### Option 1: Use Layer 2 Directly

For custom domains, create a `SemanticMemory` with converters:

```python
from long_term_memory_module import SemanticMemory, MemoryConverter

class MetricsConverter(MemoryConverter):
    def to_text(self, metric):
        return f"{metric.name}: {metric.value} at {metric.timestamp}"

    def to_metadata(self, metric):
        return {
            "metric_name": metric.name,
            "value": metric.value,
            "timestamp": metric.timestamp
        }

    def from_dict(self, data):
        return Metric(
            name=data['metadata']['metric_name'],
            value=data['metadata']['value'],
            timestamp=data['metadata']['timestamp']
        )

# Create memory
converter = MetricsConverter()
metrics_memory = converter.create_memory(
    embedding_model="all-MiniLM-L6-v2",
    persist_path="./data/metrics.faiss"
)

# Use it
metrics_memory.store(my_metric)
similar_metrics = metrics_memory.query_objects("cpu usage spikes", k=10)
```

### Option 2: Create Domain-Specific Wrapper (Like Layer 3)

For domains that need special interfaces:

```python
from long_term_memory_module import SemanticMemory

class GameEventMemory:
    """Domain-specific wrapper for game events."""

    def __init__(self, **kwargs):
        self.converter = GameEventConverter()
        self.semantic_memory = SemanticMemory(
            to_text=self.converter.to_text,
            to_metadata=self.converter.to_metadata,
            from_dict=self.converter.from_dict,
            **kwargs
        )

    def record_event(self, event):
        """Domain-specific method."""
        self.semantic_memory.store(event)

    def find_similar_events(self, description, limit=5):
        """Domain-specific query method."""
        return self.semantic_memory.query_objects(description, k=limit)

    def get_events_by_type(self, event_type):
        """Domain-specific filtering."""
        all_events = self.semantic_memory.get_all_memories()
        return [e for e in all_events if e['metadata']['type'] == event_type]
```

---

## Benefits of Three-Layer Architecture

### ✅ **Separation of Concerns**
- Layer 1: Pure vector operations
- Layer 2: Generic object handling
- Layer 3: Domain-specific logic

### ✅ **Reusability**
- LongTermMemory can be used in ANY project
- SemanticMemory works with ANY objects
- Easy to create new domain adapters

### ✅ **Testability**
- Each layer can be tested independently
- Mock converters for testing
- Unit tests don't require full stack

### ✅ **Maintainability**
- Changes to domain logic don't affect Layer 1
- Changes to vector store don't affect Layer 3
- Clear boundaries and interfaces

### ✅ **Extensibility**
- Add new domains without modifying existing layers
- Swap FAISS for other vector stores (change Layer 1 only)
- Add new converter strategies (change Layer 2 only)

---

## Migration Guide

### From RAGMemory (Original) to RAGMemoryV2

The new `RAGMemoryV2` has the same API, so migration is simple:

```python
# Old
from agent_runtime.memory import RAGMemory
memory = RAGMemory(embedding_model="all-MiniLM-L6-v2")

# New (recommended)
from agent_runtime.memory import RAGMemoryV2
memory = RAGMemoryV2(embedding_model="all-MiniLM-L6-v2")

# API is identical
memory.store(observation)
results = memory.retrieve(query="...", limit=5)
```

**Benefits of V2**:
- Cleaner code (uses SemanticMemory layer)
- Better separation of concerns
- Easier to customize converter logic
- More maintainable

---

## Examples

See the following test files for complete examples:

- [`test_three_layer_architecture.py`](../python/test_three_layer_architecture.py) - All three layers
- [`test_ltm_basic.py`](../python/test_ltm_basic.py) - Layer 1 only
- [`test_rag_agent.py`](../python/test_rag_agent.py) - Layer 3 with agents
- [`test_rag_with_llm_simulation.py`](../python/test_rag_with_llm_simulation.py) - Full agent loop

---

## Best Practices

1. **Use the appropriate layer**:
   - Layer 1: When you need maximum control
   - Layer 2: For custom objects and domains
   - Layer 3: For agent observations

2. **Keep converters simple**:
   - Focus on creating good text representations
   - Extract meaningful metadata
   - Don't try to reconstruct everything in `from_dict()`

3. **Test each layer independently**:
   - Unit test converters separately
   - Test Layer 1 without objects
   - Mock converters for Layer 2/3 tests

4. **Document your converters**:
   - Explain what text representation means
   - Document metadata schema
   - Provide examples

5. **Consider performance**:
   - Keep text representations concise
   - Only extract metadata you'll filter on
   - Use appropriate FAISS index type

---

## Future Enhancements

Potential improvements to the architecture:

- [ ] Add caching layer between Layer 2 and Layer 3
- [ ] Support multiple converters per memory (multi-modal)
- [ ] Add query builders for complex metadata filtering
- [ ] Support remote vector stores (Pinecone, Weaviate)
- [ ] Add memory versioning for schema changes
- [ ] Implement memory importance scoring
- [ ] Add automatic memory consolidation

---

## Summary

The three-layer architecture provides:

✅ **Layer 1**: Generic, reusable vector store
✅ **Layer 2**: Flexible object storage for any domain
✅ **Layer 3**: Convenient agent-specific interface

This design is **production-ready** and **extensible**, allowing Agent Arena to support diverse memory use cases while keeping the core generic and maintainable.
