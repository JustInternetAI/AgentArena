# Memory System Documentation

## Overview

Agent Arena provides a comprehensive memory system for LLM-driven agents to store, retrieve, and leverage past experiences. The memory system supports multiple strategies ranging from simple sliding windows to advanced vector-based semantic retrieval.

## Memory Types

### 1. Sliding Window Memory (`SlidingWindowMemory`)

A simple FIFO (First-In-First-Out) memory that keeps the most recent N observations.

**Use Cases:**
- Simple reactive agents
- Resource-constrained environments
- When only recent history matters

**Example:**
```python
from agent_runtime.memory import SlidingWindowMemory

memory = SlidingWindowMemory(capacity=10)
memory.store(observation)
recent = memory.retrieve(limit=5)
```

### 2. Summarizing Memory (`SummarizingMemory`)

Uses an LLM to compress older observations into summaries while keeping recent observations intact.

**Use Cases:**
- Long-running agents
- When context window is limited
- When semantic compression is acceptable

**Example:**
```python
from agent_runtime.memory import SummarizingMemory

memory = SummarizingMemory(
    backend=llm_backend,
    buffer_capacity=20,
    compression_trigger=15
)
memory.store(observation)
summary = memory.summarize()  # Includes compressed + recent observations
```

### 3. RAG Memory (`RAGMemory`)

Vector-based semantic retrieval using FAISS and sentence transformers for similarity search.

**Use Cases:**
- Agents that need to recall relevant past experiences
- Large knowledge bases
- When semantic similarity matters more than recency

**Example:**
```python
from agent_runtime.memory import RAGMemory

memory = RAGMemory(
    embedding_model="all-MiniLM-L6-v2",
    index_type="FlatIP",  # Cosine similarity
    similarity_threshold=0.3,
    default_k=5,
    persist_path="./data/memory/agent_001.faiss"
)

# Store observations
memory.store(observation)

# Semantic search
relevant = memory.retrieve(query="Where can I find resources?", limit=3)

# Save/load
memory.save()
memory.load()
```

## Long-Term Memory (Standalone)

The `LongTermMemory` class provides a standalone vector store for episodic memory without the agent runtime dependencies.

### Features

- **Vector Embeddings**: Uses sentence-transformers for semantic embeddings
- **FAISS Integration**: Efficient similarity search with multiple index types
- **Persistence**: Save/load memory across sessions
- **Flexible Retrieval**: Query by similarity or retrieve by ID
- **Metadata Support**: Attach structured data to memories

### Installation

The long-term memory system requires:
```bash
pip install faiss-cpu sentence-transformers
```

For GPU acceleration:
```bash
pip install faiss-gpu sentence-transformers
```

### Usage

#### Basic Usage

```python
from long_term_memory_module.long_term_memory import LongTermMemory

# Initialize
memory = LongTermMemory(
    embedding_model="all-MiniLM-L6-v2",
    persist_path="./data/memory.faiss"
)

# Store experience
memory_id = memory.store_memory(
    text="I collected 5 berries near the forest edge and avoided the fire hazard.",
    metadata={
        "episode": 42,
        "outcome": "success",
        "reward": 25.0,
        "timestamp": "2025-01-15T10:30:00Z"
    }
)

# Query similar experiences
similar = memory.query_memory(
    query="How do I avoid hazards while collecting resources?",
    k=3
)

for mem in similar:
    print(f"Memory: {mem['text']}")
    print(f"Similarity: {mem['score']}")
    print(f"Metadata: {mem['metadata']}")

# Save to disk
memory.save("./data/agent_001_memory.faiss")

# Load later
memory.load("./data/agent_001_memory.faiss")
```

#### Advanced Configuration

```python
# Use cosine similarity (recommended for semantic search)
memory = LongTermMemory(
    embedding_model="all-MiniLM-L6-v2",
    index_type="FlatIP",  # Inner product for cosine similarity
    persist_path="./data/memory.faiss"
)

# For large datasets (>10K memories), use approximate search
memory = LongTermMemory(
    embedding_model="all-MiniLM-L6-v2",
    index_type="IVF100",  # Inverted file index with 100 clusters
    persist_path="./data/memory.faiss"
)

# Use higher quality embeddings (slower but better)
memory = LongTermMemory(
    embedding_model="all-mpnet-base-v2",  # 768D embeddings
    index_type="FlatIP",
    persist_path="./data/memory.faiss"
)
```

### API Reference

#### `store_memory(text, metadata=None) -> str`

Store a memory with optional metadata.

**Parameters:**
- `text` (str): The text content to store
- `metadata` (dict, optional): Structured metadata

**Returns:**
- `str`: Unique memory ID (UUID)

#### `query_memory(query, k=5, threshold=None) -> list[dict]`

Query memories using semantic similarity.

**Parameters:**
- `query` (str): Query text
- `k` (int): Number of results to return
- `threshold` (float, optional): Minimum similarity threshold

**Returns:**
- List of dictionaries with keys: `id`, `text`, `metadata`, `score`, `distance`

#### `recall_by_id(memory_id) -> dict | None`

Retrieve a specific memory by ID.

**Parameters:**
- `memory_id` (str): The UUID of the memory

**Returns:**
- Dictionary with `id`, `text`, `metadata`, or `None` if not found

#### `get_all_memories() -> list[dict]`

Get all stored memories.

**Returns:**
- List of all memory dictionaries

#### `clear_memories() -> None`

Clear all memories and reset the index.

#### `save(filepath=None) -> None`

Save memory to disk.

**Parameters:**
- `filepath` (str, optional): Path to save to (uses `persist_path` if None)

#### `load(filepath=None) -> None`

Load memory from disk.

**Parameters:**
- `filepath` (str, optional): Path to load from (uses `persist_path` if None)

## Embedding Models

### Recommended Models

| Model | Dimension | Speed | Quality | Use Case |
|-------|-----------|-------|---------|----------|
| `all-MiniLM-L6-v2` | 384 | ⚡⚡⚡ | ⭐⭐ | General purpose, fast |
| `all-MiniLM-L12-v2` | 384 | ⚡⚡ | ⭐⭐⭐ | Better quality, still fast |
| `all-mpnet-base-v2` | 768 | ⚡ | ⭐⭐⭐⭐ | High quality, slower |
| `multi-qa-MiniLM-L6-cos-v1` | 384 | ⚡⚡⚡ | ⭐⭐ | Optimized for Q&A |

### Model Selection Guidelines

- **Small agents (<1K memories)**: Use `all-MiniLM-L6-v2` for speed
- **Medium agents (1K-10K memories)**: Use `all-MiniLM-L12-v2` for balance
- **Large agents (>10K memories)**: Use `all-mpnet-base-v2` for quality
- **Question answering**: Use `multi-qa-MiniLM-L6-cos-v1`

## FAISS Index Types

### Flat (Exact Search)

- **Type**: `Flat` (L2 distance) or `FlatIP` (cosine similarity)
- **Best for**: <10K memories
- **Speed**: O(n) per query
- **Accuracy**: 100% (exact)

```python
memory = LongTermMemory(index_type="Flat")  # L2 distance
memory = LongTermMemory(index_type="FlatIP")  # Cosine similarity (recommended)
```

### IVF (Approximate Search)

- **Type**: `IVF{nlist}` (e.g., `IVF100`, `IVF1000`)
- **Best for**: 10K-1M+ memories
- **Speed**: O(log n) per query
- **Accuracy**: ~95-99% (configurable)

```python
memory = LongTermMemory(index_type="IVF100")  # 100 clusters
memory = LongTermMemory(index_type="IVF1000")  # 1000 clusters (for larger datasets)
```

**Guidelines:**
- Use `IVF{n}` where `n` = sqrt(num_memories)
- For 10K memories: Use `IVF100`
- For 100K memories: Use `IVF316`
- For 1M memories: Use `IVF1000`

## Configuration

### YAML Configuration

See [`configs/memory/long_term.yaml`](../configs/memory/long_term.yaml) for a complete configuration example.

```yaml
memory:
  type: faiss
  embedding:
    model: "all-MiniLM-L6-v2"
    dim: 384
  index:
    type: "FlatIP"  # Use cosine similarity
  persistence:
    data_dir: "./data/memory"
    autosave_interval: 100
  retrieval:
    default_k: 5
    min_similarity: 0.3
```

### Loading Configuration

```python
import yaml
from long_term_memory_module.long_term_memory import LongTermMemory

with open("configs/memory/long_term.yaml") as f:
    config = yaml.safe_load(f)

memory_config = config["memory"]
memory = LongTermMemory(
    embedding_model=memory_config["embedding"]["model"],
    index_type=memory_config["index"]["type"],
    persist_path=f"{memory_config['persistence']['data_dir']}/agent.faiss"
)
```

## Performance Considerations

### Memory Usage

- **Embeddings**: ~1.5 KB per memory (384D) or ~3 KB (768D)
- **Metadata**: Varies based on content
- **Index overhead**: ~10-20% additional storage

### Query Latency

Benchmark on standard CPU:

| Memories | Index Type | Latency (k=5) |
|----------|-----------|---------------|
| 1K | Flat | <10ms |
| 10K | Flat | <50ms |
| 10K | IVF100 | <20ms |
| 100K | IVF316 | <30ms |
| 1M | IVF1000 | <50ms |

### Optimization Tips

1. **Use FlatIP for cosine similarity** - Better semantic matching than L2
2. **Batch embedding generation** - Process multiple memories at once
3. **Use IVF for large datasets** - Dramatically faster with minimal accuracy loss
4. **Persist frequently** - Save memory periodically to avoid data loss
5. **Monitor index size** - Rebuild with larger nlist as memories grow

## Integration with Agent Runtime

### Using RAGMemory in Agents

```python
from agent_runtime import AgentBehavior, RAGMemory
from agent_runtime.schemas import Observation, AgentDecision

class MyAgent(AgentBehavior):
    def __init__(self, backend, persist_path="./data/memory/my_agent.faiss"):
        self.backend = backend
        self.memory = RAGMemory(
            embedding_model="all-MiniLM-L6-v2",
            index_type="FlatIP",
            persist_path=persist_path
        )

    def decide(self, observation: Observation, tools: list) -> AgentDecision:
        # Store current observation
        self.memory.store(observation)

        # Retrieve relevant past experiences
        query = "What resources are nearby?"
        relevant_memories = self.memory.retrieve(query=query, limit=3)

        # Build context with relevant memories
        context = self._build_context(observation, relevant_memories)

        # Query LLM
        response = self.backend.generate(context)

        return AgentDecision.from_llm_response(response)

    def _build_context(self, observation, memories):
        context = f"Current state: {observation}\n\n"

        if memories:
            context += "Relevant past experiences:\n"
            for i, mem in enumerate(memories, 1):
                context += f"{i}. {mem}\n"

        return context
```

### Periodic Saving

```python
class MyAgent(AgentBehavior):
    def __init__(self, backend, persist_path):
        self.backend = backend
        self.memory = RAGMemory(persist_path=persist_path)
        self.decisions_since_save = 0
        self.save_interval = 100

    def decide(self, observation, tools):
        self.memory.store(observation)

        # ... decision logic ...

        # Periodic save
        self.decisions_since_save += 1
        if self.decisions_since_save >= self.save_interval:
            self.memory.save()
            self.decisions_since_save = 0

        return decision
```

## Best Practices

### 1. Choose the Right Memory Type

- **Reactive agents**: Use `SlidingWindowMemory` (fast, simple)
- **Planning agents**: Use `SummarizingMemory` (compressed context)
- **Learning agents**: Use `RAGMemory` (semantic retrieval)

### 2. Optimize Retrieval

```python
# Good: Specific, focused queries
results = memory.query_memory("Where did I find berries?", k=3)

# Bad: Vague, broad queries
results = memory.query_memory("What happened?", k=10)
```

### 3. Use Metadata Effectively

```python
# Good: Structured, searchable metadata
memory.store_memory(
    text="Found berries at (10, 0, 5)",
    metadata={
        "type": "resource_discovery",
        "resource": "berries",
        "location": (10, 0, 5),
        "episode": 42,
        "timestamp": "2025-01-15T10:30:00Z"
    }
)

# Can later filter by metadata
all_memories = memory.get_all_memories()
berry_memories = [m for m in all_memories if m["metadata"].get("resource") == "berries"]
```

### 4. Monitor Memory Growth

```python
# Check memory size periodically
print(f"Total memories: {len(memory)}")

# Clear old memories if needed
if len(memory) > 100000:
    # Archive old memories or clear
    memory.save("./data/archive/old_memories.faiss")
    memory.clear_memories()
```

### 5. Test Retrieval Quality

```python
# Verify that similar memories are retrieved
test_query = "How do I collect wood safely?"
results = memory.query_memory(test_query, k=5)

for i, result in enumerate(results, 1):
    print(f"{i}. Score: {result['score']:.3f}")
    print(f"   Text: {result['text'][:80]}...")
    print()
```

## Troubleshooting

### Import Errors

If you encounter import errors with FAISS or sentence-transformers:

```bash
# Reinstall dependencies
pip install --force-reinstall faiss-cpu sentence-transformers torch

# For GPU support
pip install --force-reinstall faiss-gpu sentence-transformers torch
```

### Slow Queries

If queries are slow:

1. Use IVF index instead of Flat for large datasets
2. Reduce `k` (number of results)
3. Use a smaller embedding model
4. Enable GPU acceleration (if available)

### High Memory Usage

If memory usage is too high:

1. Clear old memories periodically
2. Use a smaller embedding model (384D instead of 768D)
3. Archive memories to disk and load selectively
4. Use metadata-based filtering before semantic search

## Examples

See [`python/test_ltm_basic.py`](../python/test_ltm_basic.py) for a complete working example.

## Future Enhancements

Planned improvements:

- [ ] Multi-modal embeddings (text + images)
- [ ] Hierarchical memory (episodes → scenes → observations)
- [ ] Automatic memory consolidation
- [ ] Remote vector store support (Pinecone, Weaviate)
- [ ] Memory importance scoring
- [ ] Forgetting mechanisms
- [ ] Memory graphs (knowledge graphs from memories)

## References

- [FAISS Documentation](https://faiss.ai/)
- [Sentence Transformers](https://www.sbert.net/)
- [HuggingFace Models](https://huggingface.co/sentence-transformers)

## Support

For issues or questions, please file an issue on GitHub or contact the maintainers.
