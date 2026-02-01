# Agent Memory Architecture

This document explains how memory works in Agent Arena, the design philosophy behind it, and common pitfalls to avoid when building AI agents with memory.

> **See also:** [Memory System Reference](memory_system.md) for detailed API documentation and configuration options.

## Table of Contents

- [Why Agents Need Memory](#why-agents-need-memory)
- [The Core Insight](#the-core-insight)
- [Memory Types in Agent Arena](#memory-types-in-agent-arena)
- [Current Implementation](#current-implementation)
- [Common Pitfalls](#common-pitfalls)
- [Design Philosophy](#design-philosophy)
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

This is the most important concept in agent memory design.

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

## Memory Types in Agent Arena

### 1. Working Memory (Implicit)

**What it is:** The current observation and immediate context.

**Where it lives:** Directly in the agent's prompt each tick.

**Example:**
```
Current position: (10.0, 0.0, 5.0)
Health: 85, Energy: 90
Nearby: Berry1 at 3.2 units, Fire1 at 8.1 units
```

**Characteristics:**
- Very small (fits in context window)
- Refreshed every tick
- No persistence needed

### 2. Spatial Memory (World Map)

**What it is:** A structured map of objects the agent has seen.

**Implementation:** `SpatialMemory` class with grid-based spatial indexing.

**Use cases:**
- "What resources have I seen near position X?"
- "Where was that berry I saw earlier?"
- "Is there a known hazard between me and the goal?"

**Example:**
```python
from agent_runtime.memory import SpatialMemory

world_map = SpatialMemory()

# Update each tick with what we see
world_map.update_from_observation(observation)

# Query by position
nearby = world_map.query_near_position(
    position=(10, 0, 5),
    radius=30,
    object_type="resource"
)

# Query by type
all_hazards = world_map.get_hazards()

# Mark collected resources
world_map.mark_collected("Berry1")
```

**Key properties:**
- Deterministic queries
- O(1) grid-based lookups
- Tracks object status (active, collected, destroyed)
- Remembers objects even when out of line-of-sight

### 3. Episodic Memory (Experience History)

**What it is:** A log of past observations, searchable by semantic similarity.

**Implementation:** `RAGMemoryV2` with vector embeddings.

**Use cases:**
- "Have I been in a situation like this before?"
- "What happened last time I was low on health?"
- "Find relevant past experiences for decision-making"

**Example:**
```python
from agent_runtime.memory import RAGMemoryV2

memory = RAGMemoryV2(
    embedding_model="all-MiniLM-L6-v2",
    similarity_threshold=0.3
)

# Store observations
memory.store(observation)

# Semantic retrieval
relevant = memory.retrieve(
    query="dangerous situation near fire",
    limit=3
)

# Get summary for LLM context
context = memory.summarize()
```

**Key properties:**
- Append-only (experiences accumulate)
- Similarity-based retrieval
- Good for learning from past experiences
- Helps with "have I seen this before?" queries

### 4. Sliding Window Memory (Simple Alternative)

**What it is:** Just the last N observations in a FIFO buffer.

**Implementation:** `SlidingWindowMemory`

**Use cases:**
- Simple scenarios that don't need long-term memory
- Debugging and prototyping
- When you just need recent context

**Example:**
```python
from agent_runtime.memory import SlidingWindowMemory

memory = SlidingWindowMemory(max_size=10)
memory.store(observation)
recent = memory.retrieve(limit=5)
```

---

## Current Implementation

### Architecture Diagram

```
                    ┌─────────────────────────────────────┐
                    │         Agent Behavior              │
                    │  (Your decision-making code)        │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────┴──────────────────────┐
                    │                                      │
           ┌────────▼────────┐                 ┌──────────▼──────────┐
           │  SpatialMemory  │                 │    RAGMemoryV2      │
           │  (World Map)    │                 │  (Experience Log)   │
           └────────┬────────┘                 └──────────┬──────────┘
                    │                                      │
           ┌────────▼────────┐                 ┌──────────▼──────────┐
           │   Grid Index    │                 │   SemanticMemory    │
           │  (Spatial Hash) │                 │  (Layer 2 - Generic)│
           └─────────────────┘                 └──────────┬──────────┘
                                                          │
                                               ┌──────────▼──────────┐
                                               │   LongTermMemory    │
                                               │  (FAISS + Embeddings)│
                                               └──────────────────────┘
```

### Data Flow: Observation Processing

```
Godot sends observation
        │
        ▼
┌───────────────────────────────────────────────────┐
│ Agent receives Observation                         │
│ - position, health, energy                        │
│ - nearby_resources (what's visible now)           │
│ - nearby_hazards (what's visible now)             │
└───────────────────────────────────────────────────┘
        │
        ├─────────────────────────────┐
        ▼                             ▼
┌───────────────────┐       ┌─────────────────────┐
│ SpatialMemory     │       │ RAGMemory           │
│ .update_from_     │       │ .store(observation) │
│  observation()    │       │                     │
│                   │       │ Embeds full obs     │
│ Extracts objects, │       │ for similarity      │
│ updates positions │       │ search later        │
└───────────────────┘       └─────────────────────┘
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

## Common Pitfalls

### 1. Putting Everything in Vectors

**The mistake:**
```python
# Storing position as text for vector search
memory.store(f"Berry at position 10, 5")

# Later trying to query by position
results = memory.search("what's at position 10, 5")  # Unreliable!
```

**The problem:** Vector search finds *similar* text, not exact matches. "position 10, 5" might match "position 10, 6" or "position 11, 5" with high similarity.

**The fix:** Use structured storage for positional data:
```python
world_map.store_object(name="Berry", position=(10, 5))
obj = world_map.get_object_at(10, 5)  # Exact match
```

### 2. Forgetting to Update Memory

**The mistake:**
```python
def decide(self, observation, tools):
    # Forgot to update memory!
    nearby = self.world_map.query_near_position(observation.position)
    # Returns stale data...
```

**The fix:** Always update memory at the start of each decision:
```python
def decide(self, observation, tools):
    self.world_map.update_from_observation(observation)  # First!
    nearby = self.world_map.query_near_position(observation.position)
```

### 3. Not Tracking Object Status

**The mistake:**
```python
# Agent collected Berry1, but memory still shows it as available
nearby_resources = world_map.get_resources()
# Berry1 is in the list, agent walks back to collect it again
```

**The fix:** Mark objects when their status changes:
```python
# When resource is collected
world_map.mark_collected("Berry1")

# Now queries exclude it by default
nearby_resources = world_map.get_resources()  # Berry1 not included
```

### 4. Trusting Stale Information

**The mistake:** Treating old memories as current truth.

```python
# Saw enemy at (10, 5) 100 ticks ago
# Enemy has definitely moved, but agent still treats this as current
```

**The fix:** Track when information was last updated:
```python
obj = world_map.get_object("Enemy1")
staleness = current_tick - obj.last_seen_tick
if staleness > 50:
    # Information is stale, treat with caution
    confidence = "low"
```

### 5. Memory Bloat

**The mistake:** Storing every observation forever without cleanup.

```python
# After 10,000 ticks, memory contains 10,000 observations
# Queries become slow, context becomes huge
```

**The fix:** Use appropriate memory limits:
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

**The mistake:** Building complex memory systems before you need them.

```python
# Building 5 memory types for a simple foraging scenario
working_memory = WorkingMemory()
episodic_memory = EpisodicMemory()
semantic_memory = SemanticMemory()
procedural_memory = ProceduralMemory()
world_model = WorldModel()
# ... spent weeks on memory architecture, agent still can't find berries
```

**The fix:** Start simple, add complexity when pain demands it:
```python
# Start with this:
world_map = SpatialMemory()  # What's where
recent_obs = SlidingWindowMemory(max_size=10)  # Recent context

# Add more ONLY when you hit specific problems
```

### 7. Not Using Memory in Prompts

**The mistake:** Having memory but not including it in the LLM context.

```python
def decide(self, observation, tools):
    self.memory.store(observation)
    # Memory exists but LLM never sees it!
    prompt = f"You are at {observation.position}. What do you do?"
```

**The fix:** Include relevant memory in the prompt:
```python
def decide(self, observation, tools):
    self.memory.store(observation)

    # Include memory context
    map_summary = self.world_map.summarize()
    relevant_experiences = self.memory.retrieve(
        query="current situation", limit=3
    )

    prompt = f"""
    You are at {observation.position}.

    World Map:
    {map_summary}

    Relevant past experiences:
    {format_experiences(relevant_experiences)}

    What do you do?
    """
```

---

## Design Philosophy

### 1. Let Architecture Emerge from Pain

Don't build a complex 5-tier memory system upfront. Start with the simplest thing that works:

1. **Start:** Just use the current observation (working memory only)
2. **Problem:** Agent forgets where resources were → Add SpatialMemory
3. **Problem:** Agent repeats mistakes → Add experience memory
4. **Problem:** Context too large → Add summarization

Each addition solves a real problem you've encountered.

### 2. Right Tool for the Job

| Query Type | Use This |
|------------|----------|
| "What's at position X?" | Structured (SpatialMemory) |
| "What's near me?" | Spatial index (grid/k-d tree) |
| "Have I seen something like this?" | Vector similarity (RAGMemory) |
| "What just happened?" | Sliding window |
| "What are the key facts?" | Summarization |

### 3. Memory is for the LLM, Not Just Storage

Memory only matters if it improves the agent's decisions. Always ask:

- Will the LLM use this information?
- Does this fit in the context window?
- Is this the right format for the LLM to understand?

### 4. Determinism Where It Matters

Some queries need exact answers:
- "Is there a hazard at (10, 5)?" → Yes or No, not "probably"
- "Did I collect Berry1?" → Yes or No
- "What's the closest resource?" → Exact answer with distance

Use structured storage for these. Save vectors for fuzzy similarity queries.

---

## Future Considerations

As Agent Arena evolves, we may add:

### Semantic Memory (Learned Knowledge)

Distilled facts extracted from experience:
- "Fire causes 25 damage"
- "Berries restore health"
- "Narrow passages often have traps"

This would require a summarization/extraction pipeline.

### Skill Memory (Procedural)

Reusable strategies:
- "To collect distant resources, plan a path avoiding hazards"
- "When health is low, prioritize safety over collection"

### Cross-Episode Learning

Agents that learn across multiple runs:
- "In episode 5, I learned that the north path is faster"
- Transfer knowledge to new scenarios

### Confidence Decay

Trust in old information decreasing over time:
- Position last seen 100 ticks ago → low confidence
- Position confirmed this tick → high confidence

---

## Summary

1. **Separate concerns:** Vector memory for similarity, structured memory for state
2. **Start simple:** Add memory types only when you hit real problems
3. **Update consistently:** Memory must stay in sync with the world
4. **Use it in prompts:** Memory only helps if the LLM sees it
5. **Track staleness:** Old information may no longer be true

The goal is agents that remember what matters, forget what doesn't, and make better decisions because of it.
