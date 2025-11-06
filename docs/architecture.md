# Agent Arena Architecture

## Overview

Agent Arena is designed as a hybrid system combining a high-performance Godot C++ module for deterministic simulation with a flexible Python runtime for LLM-driven agent reasoning.

## System Components

### 1. Godot C++ Module (GDExtension)

The core simulation engine built as a Godot 4 GDExtension module.

**Key Classes:**

- `SimulationManager`: Manages deterministic tick loop and simulation state
- `EventBus`: Handles event recording and replay for reproducibility
- `Agent`: Godot-side agent representation with perception and action execution
- `ToolRegistry`: Manages available tools and their execution

**Responsibilities:**

- Deterministic physics and world simulation
- Event ordering and replay recording
- Sensor data collection (raycasts, vision, etc.)
- Action execution in the game world
- Navigation and pathfinding

**Data Flow:**

```
Simulation Tick -> Perception -> Event Bus -> IPC/gRPC -> Python Runtime
                                                            |
Python Runtime -> Action Decision -> Event Bus -> Action Execution
```

### 2. Python Agent Runtime

The LLM-based reasoning and decision-making system.

**Key Modules:**

#### agent_runtime/
- `Agent`: Core agent with perception-reasoning-action loop
- `AgentRuntime`: Manages multiple agents and async execution
- `ToolDispatcher`: Registers and executes tools

#### backends/
- `BaseBackend`: Abstract LLM backend interface
- `LlamaCppBackend`: llama.cpp integration
- `VLLMBackend`: vLLM integration (future)
- `TensorRTBackend`: TensorRT-LLM integration (future)

#### memory/
- `ShortTermMemory`: Recent observations (FIFO/priority queue)
- `LongTermMemory`: Vector store for RAG (FAISS/Milvus)
- `EpisodeMemory`: Episode summaries and learning

#### tools/
- `world_query.py`: Vision rays, entity detection, distance
- `movement.py`: Navigation, pathfinding, rotation
- `inventory.py`: Item pickup, crafting, usage

#### evals/
- Evaluation harness for benchmark scenes
- Metrics collection and analysis
- Replay system for deterministic testing

### 3. Configuration System (Hydra)

Hierarchical configuration management using Hydra/OmegaConf.

**Config Structure:**
```
configs/
├── config.yaml           # Main config
├── backend/
│   ├── llama_cpp.yaml
│   ├── vllm.yaml
│   └── tensorrt.yaml
├── memory/
│   ├── basic.yaml
│   └── rag.yaml
└── scenes/
    ├── foraging.yaml
    ├── crafting_chain.yaml
    └── team_capture.yaml
```

## Communication Protocol

### Godot <-> Python IPC

**Options:**

1. **gRPC** (Recommended for production)
   - Bidirectional streaming
   - Type-safe protocol buffers
   - Low latency

2. **HTTP/REST** (Simple for prototyping)
   - Request/response per tick
   - JSON serialization
   - Easy debugging

3. **Shared Memory** (Highest performance)
   - Zero-copy communication
   - MessagePack serialization
   - Complex to implement

### Message Format

**Perception Message (Godot -> Python):**
```json
{
  "tick": 1234,
  "agent_id": "agent_001",
  "observations": {
    "position": [10.0, 0.0, 5.0],
    "rotation": [0.0, 90.0, 0.0],
    "visible_entities": [...],
    "inventory": [...],
    "health": 100.0
  }
}
```

**Action Message (Python -> Godot):**
```json
{
  "tick": 1234,
  "agent_id": "agent_001",
  "action": {
    "tool": "move_to",
    "params": {
      "target_position": [15.0, 0.0, 8.0],
      "speed": 1.5
    }
  }
}
```

## Deterministic Simulation

### Requirements

1. **Fixed Tick Rate**: Simulation advances in discrete ticks
2. **Seedable RNG**: All randomness uses seeded generators
3. **Event Ordering**: Events processed in deterministic order
4. **Replay Logs**: All events recorded with timestamps

### Replay System

**Log Format (MessagePack):**
```python
{
  "metadata": {
    "seed": 42,
    "tick_rate": 60,
    "version": "0.1.0"
  },
  "events": [
    {
      "tick": 1,
      "type": "agent_spawn",
      "data": {...}
    },
    ...
  ]
}
```

## Agent Decision Loop

```
1. Perceive
   ├─ Receive observations from Godot
   ├─ Update short-term memory
   └─ Trigger memory retrieval (RAG)

2. Reason
   ├─ Build context (goals + memories + observations)
   ├─ Query LLM with tool schemas
   └─ Parse tool call from response

3. Act
   ├─ Validate tool call against schema
   ├─ Execute tool through dispatcher
   └─ Send action to Godot

4. Learn (optional)
   ├─ Store episode in long-term memory
   ├─ Update value estimates
   └─ Adjust policy (RL fine-tuning)
```

## Benchmark Scenes

### 1. Foraging Scene

**Goal**: Collect resources while avoiding hazards

**Metrics**:
- Resources collected
- Damage taken
- Distance traveled
- Time to completion

### 2. Crafting Chain Scene

**Goal**: Craft complex items from base resources

**Metrics**:
- Items crafted
- Recipe efficiency
- Resource waste
- Crafting time

### 3. Team Capture Scene

**Goal**: Multi-agent coordination to capture objectives

**Metrics**:
- Objectives captured
- Team coordination score
- Individual contribution
- Win rate

## Memory System

### Short-Term Memory (Scratchpad)

- **Capacity**: 10-20 recent observations
- **Strategy**: FIFO, priority-based, or recency-weighted
- **Purpose**: Immediate context for LLM

### Long-Term Memory (Vector Store)

- **Backend**: FAISS, Milvus, or ChromaDB
- **Embeddings**: sentence-transformers (384-768D)
- **Retrieval**: Top-K similarity search
- **Purpose**: RAG for historical context

### Episode Memory

- **Storage**: Summarized episode logs
- **Format**: Natural language summaries
- **Purpose**: Learning from past experiences

## Extensibility

### Adding New Tools

1. Create tool function in `python/tools/`
2. Define JSON schema for parameters
3. Register with `ToolDispatcher`
4. Implement Godot-side execution if needed

### Adding New Backends

1. Inherit from `BaseBackend`
2. Implement required methods:
   - `generate()`
   - `generate_with_tools()`
   - `is_available()`
   - `unload()`
3. Create config in `configs/backend/`

### Adding New Scenes

1. Create Godot scene with required nodes
2. Add evaluation metrics script
3. Create config in `configs/scenes/`
4. Implement eval harness in `python/evals/`

## Performance Considerations

### Bottlenecks

1. **LLM Inference**: 100-1000ms per decision
2. **IPC Overhead**: 1-10ms per message
3. **Memory Retrieval**: 10-50ms per query

### Optimizations

1. **Batching**: Process multiple agents in parallel
2. **Caching**: Cache LLM responses for similar contexts
3. **Async I/O**: Non-blocking communication
4. **Model Quantization**: Use Q4/Q5 quantized models
5. **Speculative Actions**: Pre-compute likely actions

## Future Enhancements

### Curriculum Learning

- Start with simple scenes
- Gradually increase complexity
- Track learning progress

### RL Fine-Tuning

- Collect trajectories from agents
- Train PPO/DPO on successful episodes
- Fine-tune tool-use policies

### Multi-Modal

- Add vision encoders (CLIP)
- Process screenshot observations
- Learn visual patterns

### Distributed Simulation

- Run multiple simulations in parallel
- Aggregate experiences for training
- Scale evaluation throughput
