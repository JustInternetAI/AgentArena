# Agent Memory System

This document covers the design philosophy, implementation details, and API reference for Agent Arena's memory system.

## Table of Contents

- [Why Agents Need Memory](#why-agents-need-memory)
- [The Core Insight](#the-core-insight)
- [Memory Types](#memory-types)
- [Architecture](#architecture)
- [API Reference](#api-reference)
- [Embedding Models & FAISS Indexes](#embedding-models--faiss-indexes)
- [Configuration](#configuration)
- [Common Pitfalls](#common-pitfalls)
- [Best Practices](#best-practices)
- [Performance](#performance)
- [Troubleshooting](#troubleshooting)
- [Future Considerations](#future-considerations)

---

## Why Agents Need Memory

An LLM by itself is **stateless**. Each call starts fresh with no knowledge of previous interactions. This creates problems for agents that need to:

- Remember where things are in the world
- Learn from past mistakes
- Track progress toward goals
- Maintain context across many decisions

Without memory, an agent would:
- Forget resources it saw 5 seconds ago
- Repeat the same failed actions
- Lose track of its current objective
- Be unable to navigate back to known locations

Memory bridges the gap between a stateless LLM and a persistent, learning agent.

---

## The Core Insight

> **Vector memory is for meaning and similarity.**
> **Structured memory is for state and truth.**

### When to Use Vector/Semantic Memory

Vector memory (embeddings + similarity search) excels at:

- "Have I seen something **like** this before?"
- "What past experiences are **relevant** to my current situation?"
- "Find memories **related** to 'dangerous enemies'"

The key word is **similarity**. You're searching by meaning, not exact match.

### When to Use Structured Memory

Structured memory (dictionaries, databases, spatial indexes) excels at:

- "What is at position (10, 5)?"
- "Is this resource collected?"
- "What's the nearest hazard?"

These are **deterministic queries**. The answer should be the same every time given the same state. You don't want fuzzy similarity here.

### The Mistake Many Make

A common anti-pattern is forcing everything into a vector store:

```python
# BAD: Using vector search for exact state queries
def is_hazard_at_position(x, y):
    results = vector_memory.search(f"hazard at position {x}, {y}")
    return len(results) > 0 and results[0].score > 0.8
```

This is slow, non-deterministic, and can give wrong answers. Compare to:

```python
# GOOD: Using structured storage for state
def is_hazard_at_position(x, y):
    return world_map.get_object_at(x, y, type="hazard") is not None
```

The second version is O(1), deterministic, and always correct.

---

## Memory Types

### 1. Working Memory (Implicit)

**What it is:** The current observation and immediate context.

**Where it lives:** Directly in the agent's prompt each tick.

**Characteristics:**
- Very small (fits in context window)
- Refreshed every tick
- No persistence needed

### 2. Sliding Window Memory (`SlidingWindowMemory`)

A simple FIFO (First-In-First-Out) memory that keeps the most recent N observations.

**Use Cases:**
- Simple reactive agents
- Resource-constrained environments
- When only recent history matters
- Debugging and prototyping

**Example:**
```python
from agent_runtime.memory import SlidingWindowMemory

memory = SlidingWindowMemory(capacity=10)
memory.store(observation)
recent = memory.retrieve(limit=5)
```

### 3. Summarizing Memory (`SummarizingMemory`)

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

### 4. Spatial Memory (`SpatialMemory`)

Structured world map for tracking object positions. Uses grid-based spatial indexing for fast proximity queries.

**Use Cases:**
- Remembering where resources and hazards are located
- Navigating back to known locations
- Tracking collected/destroyed objects
- Building a mental map of the environment

**Example:**
```python
from agent_runtime.memory import SpatialMemory

memory = SpatialMemory()

# Update with current observation (call each tick)
memory.update_from_observation(observation)

# Query by position
nearby = memory.query_near_position(
    position=(10, 0, 5),
    radius=30,
    object_type="resource"
)

# Query by type
resources = memory.get_resources()
hazards = memory.get_hazards()

# Mark objects as collected
memory.mark_collected("Berry1")

# Get summary for LLM context
summary = memory.summarize()
```

**Key Properties:**
- Deterministic queries (not fuzzy like vector search)
- O(1) grid-based spatial lookups
- Tracks object status (active, collected, destroyed)
- Remembers objects even when out of line-of-sight

### 5. RAG Memory (`RAGMemory` / `RAGMemoryV2`)

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

---

## Architecture

### Data Flow

```
                    +-------------------------------------+
                    |         Agent Behavior              |
                    |  (Your decision-making code)        |
                    +-----------------+-------------------+
                                      |
                    +-----------------+-------------------+
                    |                                      |
           +-------v--------+                 +-----------v-----------+
           |  SpatialMemory  |                 |    RAGMemoryV2        |
           |  (World Map)    |                 |  (Experience Log)     |
           +-------+--------+                 +-----------+-----------+
                    |                                      |
           +-------v--------+                 +-----------v-----------+
           |   Grid Index    |                 |   SemanticMemory      |
           |  (Spatial Hash) |                 |  (Layer 2 - Generic)  |
           +----------------+                 +-----------+-----------+
                                                          |
                                               +-----------v-----------+
                                               |   LongTermMemory      |
                                               |  (FAISS + Embeddings) |
                                               +-----------------------+
```

### Observation Processing

```
Godot sends observation
        |
        v
+---------------------------------------------------+
| Agent receives Observation                         |
| - position, health, energy                        |
| - nearby_resources (what's visible now)           |
| - nearby_hazards (what's visible now)             |
+---------------------------------------------------+
        |
        +-----------------------------+
        v                             v
+-------------------+       +---------------------+
| SpatialMemory     |       | RAGMemory           |
| .update_from_     |       | .store(observation) |
|  observation()    |       |                     |
|                   |       | Embeds full obs     |
| Extracts objects, |       | for similarity      |
| updates positions |       | search later        |
+-------------------+       +---------------------+
```

### Key Files

| File | Purpose |
|------|---------|
| `agent_runtime/schemas.py` | `WorldObject`, `Observation`, and other data structures |
| `agent_runtime/memory/spatial.py` | `SpatialMemory` - structured world map |
| `agent_runtime/memory/rag_v2.py` | `RAGMemoryV2` - vector-based experience memory |
| `agent_runtime/memory/sliding_window.py` | Simple FIFO buffer |
| `long_term_memory_module/` | Low-level vector store (FAISS + embeddings) |

---

## API Reference

### Long-Term Memory (Standalone)

The `LongTermMemory` class provides a standalone vector store for episodic memory without the agent runtime dependencies.

#### `store_memory(text, metadata=None) -> str`

Store a memory with optional metadata.

- `text` (str): The text content to store
- `metadata` (dict, optional): Structured metadata
- Returns: `str` - Unique memory ID (UUID)

#### `query_memory(query, k=5, threshold=None) -> list[dict]`

Query memories using semantic similarity.

- `query` (str): Query text
- `k` (int): Number of results to return
- `threshold` (float, optional): Minimum similarity threshold
- Returns: List of dicts with keys: `id`, `text`, `metadata`, `score`, `distance`

#### `recall_by_id(memory_id) -> dict | None`

Retrieve a specific memory by ID.

#### `get_all_memories() -> list[dict]`

Get all stored memories.

#### `clear_memories() -> None`

Clear all memories and reset the index.

#### `save(filepath=None) -> None`

Save memory to disk. Uses `persist_path` if no filepath given.

#### `load(filepath=None) -> None`

Load memory from disk.

---

## Embedding Models & FAISS Indexes

### Recommended Models

| Model | Dimension | Speed | Quality | Use Case |
|-------|-----------|-------|---------|----------|
| `all-MiniLM-L6-v2` | 384 | Fast | Good | General purpose |
| `all-MiniLM-L12-v2` | 384 | Medium | Better | Better quality, still fast |
| `all-mpnet-base-v2` | 768 | Slow | Best | High quality |
| `multi-qa-MiniLM-L6-cos-v1` | 384 | Fast | Good | Optimized for Q&A |

**Guidelines:**
- **Small agents (<1K memories)**: Use `all-MiniLM-L6-v2`
- **Medium agents (1K-10K memories)**: Use `all-MiniLM-L12-v2`
- **Large agents (>10K memories)**: Use `all-mpnet-base-v2`

### FAISS Index Types

**Flat (Exact Search)** — Best for <10K memories:
```python
memory = LongTermMemory(index_type="Flat")    # L2 distance
memory = LongTermMemory(index_type="FlatIP")  # Cosine similarity (recommended)
```

**IVF (Approximate Search)** — Best for 10K-1M+ memories:
```python
memory = LongTermMemory(index_type="IVF100")   # 10K memories
memory = LongTermMemory(index_type="IVF316")   # 100K memories
memory = LongTermMemory(index_type="IVF1000")  # 1M memories
```

Use `IVF{n}` where `n` = sqrt(num_memories).

---

## Configuration

### YAML Configuration

See [`configs/memory/long_term.yaml`](../configs/memory/long_term.yaml):

```yaml
memory:
  type: faiss
  embedding:
    model: "all-MiniLM-L6-v2"
    dim: 384
  index:
    type: "FlatIP"
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

---

## Common Pitfalls

### 1. Putting Everything in Vectors

```python
# BAD: Storing position as text for vector search
memory.store(f"Berry at position 10, 5")
results = memory.search("what's at position 10, 5")  # Unreliable!

# GOOD: Use structured storage for positional data
world_map.store_object(name="Berry", position=(10, 5))
obj = world_map.get_object_at(10, 5)  # Exact match
```

### 2. Forgetting to Update Memory

```python
# BAD
def decide(self, observation, tools):
    nearby = self.world_map.query_near_position(observation.position)
    # Returns stale data!

# GOOD
def decide(self, observation, tools):
    self.world_map.update_from_observation(observation)  # First!
    nearby = self.world_map.query_near_position(observation.position)
```

### 3. Not Tracking Object Status

```python
# Mark objects when their status changes
world_map.mark_collected("Berry1")
# Now queries exclude it by default
```

### 4. Trusting Stale Information

```python
obj = world_map.get_object("Enemy1")
staleness = current_tick - obj.last_seen_tick
if staleness > 50:
    confidence = "low"  # Information is stale
```

### 5. Memory Bloat

```python
# Option 1: Sliding window (automatic)
memory = SlidingWindowMemory(max_size=100)

# Option 2: Periodic cleanup
if len(memory) > 1000:
    memory.prune_old(keep_recent=500)

# Option 3: Summarization
if len(memory) > 100:
    summary = memory.summarize()
    memory.clear()
    memory.store_summary(summary)
```

### 6. Over-Engineering Memory

Start simple, add complexity when pain demands it:
```python
# Start with this:
world_map = SpatialMemory()
recent_obs = SlidingWindowMemory(max_size=10)

# Add more ONLY when you hit specific problems
```

### 7. Not Using Memory in Prompts

```python
# BAD: Memory exists but LLM never sees it!
prompt = f"You are at {observation.position}. What do you do?"

# GOOD: Include relevant memory in the prompt
map_summary = self.world_map.summarize()
relevant = self.memory.retrieve(query="current situation", limit=3)
prompt = f"""You are at {observation.position}.
World Map: {map_summary}
Past experiences: {format_experiences(relevant)}
What do you do?"""
```

---

## Best Practices

### Choose the Right Memory Type

| Query Type | Use This |
|------------|----------|
| "What's at position X?" | Structured (SpatialMemory) |
| "What's near me?" | Spatial index (grid/k-d tree) |
| "Have I seen something like this?" | Vector similarity (RAGMemory) |
| "What just happened?" | Sliding window |
| "What are the key facts?" | Summarization |

### Optimize Retrieval

```python
# Good: Specific, focused queries
results = memory.query_memory("Where did I find berries?", k=3)

# Bad: Vague, broad queries
results = memory.query_memory("What happened?", k=10)
```

### Use Metadata Effectively

```python
memory.store_memory(
    text="Found berries at (10, 0, 5)",
    metadata={
        "type": "resource_discovery",
        "resource": "berries",
        "location": (10, 0, 5),
        "episode": 42,
    }
)
```

### Integration with Agent Runtime

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
        self.memory.store(observation)
        relevant_memories = self.memory.retrieve(query="What resources are nearby?", limit=3)
        context = self._build_context(observation, relevant_memories)
        response = self.backend.generate(context)
        return AgentDecision.from_llm_response(response)
```

---

## Performance

### Memory Usage

- **Embeddings**: ~1.5 KB per memory (384D) or ~3 KB (768D)
- **Metadata**: Varies based on content
- **Index overhead**: ~10-20% additional storage

### Query Latency

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

---

## Troubleshooting

### Import Errors

```bash
pip install --force-reinstall faiss-cpu sentence-transformers torch
# For GPU: pip install --force-reinstall faiss-gpu sentence-transformers torch
```

### Slow Queries

1. Use IVF index instead of Flat for large datasets
2. Reduce `k` (number of results)
3. Use a smaller embedding model
4. Enable GPU acceleration

### High Memory Usage

1. Clear old memories periodically
2. Use a smaller embedding model (384D instead of 768D)
3. Archive memories to disk and load selectively

---

## Future Considerations

- Multi-modal embeddings (text + images)
- Hierarchical memory (episodes -> scenes -> observations)
- Automatic memory consolidation
- Remote vector store support
- Memory importance scoring
- Forgetting mechanisms
- Memory graphs (knowledge graphs from memories)
- Semantic memory (distilled facts from experience)
- Skill/procedural memory (reusable strategies)
- Cross-episode learning
- Confidence decay over time

---

## Design Philosophy

1. **Separate concerns:** Vector memory for similarity, structured memory for state
2. **Start simple:** Add memory types only when you hit real problems
3. **Update consistently:** Memory must stay in sync with the world
4. **Use it in prompts:** Memory only helps if the LLM sees it
5. **Track staleness:** Old information may no longer be true

The goal is agents that remember what matters, forget what doesn't, and make better decisions because of it.

## References

- [FAISS Documentation](https://faiss.ai/)
- [Sentence Transformers](https://www.sbert.net/)
- [HuggingFace Models](https://huggingface.co/sentence-transformers)
