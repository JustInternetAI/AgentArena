# Agent Arena Architecture

## Overview

Agent Arena is designed as a hybrid system combining a high-performance Godot C++ module for deterministic simulation with a flexible Python runtime for LLM-driven agent reasoning.

## System Components

### 1. Godot C++ Module (GDExtension)

The core simulation engine built as a Godot 4 GDExtension module.

**Key Classes:**

- `SimulationManager`: Manages deterministic tick loop and simulation state
- `EventBus`: Handles event recording and replay for reproducibility
- `Agent`: Core C++ agent class with perception and memory (wrapped by SimpleAgent)
- `SimpleAgent`: GDScript wrapper providing auto-discovery and signal-based tool responses
- `ToolRegistry`: Manages available tools and their execution
- `IPCClient`: Handles HTTP communication with Python backend

**Autoload Services:**

- `IPCService`: Global singleton managing connection to Python backend
- `ToolRegistryService`: Global singleton managing tool registration and execution

**Responsibilities:**

- Deterministic physics and world simulation
- Event ordering and replay recording
- Sensor data collection (raycasts, vision, etc.)
- Action execution in the game world
- Navigation and pathfinding
- Tool execution through Python IPC backend

**Data Flow:**

```
Simulation Tick -> Perception -> Event Bus -> IPC/gRPC -> Python Runtime
                                                            |
Python Runtime -> Action Decision -> Event Bus -> Action Execution
```

### 2. Python Agent Runtime

The LLM-based reasoning and decision-making system with a **layered interface** for different skill levels.

**Directory Structure:**

```
python/
├── agent_runtime/              # Core framework (users import from here)
│   ├── __init__.py             # Public API exports
│   ├── behavior.py             # AgentBehavior ABC, SimpleAgentBehavior
│   ├── schemas.py              # Observation, AgentDecision, ToolSchema
│   ├── arena.py                # AgentArena orchestrator (hides IPC)
│   ├── behaviors/              # Built-in behavior implementations
│   │   ├── llm_behavior.py     # LLM-based decision making
│   │   ├── rule_based.py       # Simple rules for tutorials
│   │   └── random_behavior.py  # Random baseline
│   └── memory/                 # Memory system implementations
│       ├── base.py             # AgentMemory ABC
│       ├── sliding_window.py   # Simple FIFO memory
│       ├── summarizing.py      # LLM-compressed memory
│       └── rag.py              # Vector store retrieval
│
├── user_agents/                # WHERE USERS PUT THEIR CODE
│   ├── __init__.py
│   ├── examples/               # Example agents to learn from
│   │   ├── simple_forager.py
│   │   ├── llm_forager.py
│   │   └── strategic_agent.py
│   └── README.md               # "Start here" guide
│
├── backends/                   # LLM adapters
│   ├── base.py                 # BaseBackend ABC
│   ├── llama_cpp.py            # llama.cpp integration
│   ├── vllm.py                 # vLLM integration
│   └── openai_compat.py        # OpenAI-compatible APIs
│
├── tools/                      # Agent tools (framework-provided)
│   ├── movement.py             # move_to, navigate_to, rotate
│   ├── world_query.py          # raycast, get_nearby_entities
│   └── inventory.py            # pickup, drop, craft
│
├── evals/                      # Evaluation harness
│   └── ...
│
├── ipc/                        # IPC internals (users don't touch)
│   ├── server.py               # FastAPI server
│   └── protocol.py             # Message schemas
│
└── run_agent.py                # Main entry point
```

#### Layered Agent Interface

The framework provides three layers of abstraction:

**Layer 1: SimpleAgentBehavior (Beginners)**
- User implements `decide(context) -> tool_name`
- Framework handles: memory, prompts, parsing, tool parameters
- Best for: Tutorials, learning tool use basics

**Layer 2: AgentBehavior with Built-in Memory (Intermediate)**
- User implements `decide(observation, tools) -> AgentDecision`
- User chooses memory strategy from built-ins
- User writes system prompt and builds context
- Best for: Learning LLM integration, prompt engineering

**Layer 3: AgentBehavior with Custom Memory (Advanced)**
- User implements custom `AgentMemory` subclass
- Full control over state, prompts, and decision flow
- Best for: Research, complex agent architectures

#### Key Interfaces

```python
# behavior.py - What users implement

class AgentBehavior(ABC):
    """Full interface for agent decision-making."""

    @abstractmethod
    def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
        """Given current observation and available tools, decide what to do."""
        pass

    def on_tool_result(self, tool: str, result: dict) -> None:
        """Optional: Handle tool execution results."""
        pass

    def on_episode_start(self) -> None:
        """Optional: Initialize at episode start."""
        pass

    def on_episode_end(self, success: bool) -> None:
        """Optional: Cleanup at episode end."""
        pass


class SimpleAgentBehavior(AgentBehavior):
    """Simplified interface for beginners."""

    system_prompt: str = "You are an agent."
    memory_capacity: int = 10

    @abstractmethod
    def decide(self, context: SimpleContext) -> str:
        """Return the name of the tool to use."""
        pass
```

```python
# schemas.py - Data contracts

@dataclass
class Observation:
    """What the agent receives from Godot each tick."""
    agent_id: str
    tick: int
    position: tuple[float, float, float]
    rotation: tuple[float, float, float] | None
    visible_entities: list[EntityInfo]
    nearby_resources: list[ResourceInfo]
    nearby_hazards: list[HazardInfo]
    inventory: list[ItemInfo]
    health: float
    energy: float
    custom: dict  # Scenario-specific data


@dataclass
class AgentDecision:
    """What the agent returns to the framework."""
    tool: str
    params: dict
    reasoning: str | None = None

    @classmethod
    def from_llm_response(cls, response: str) -> "AgentDecision":
        """Parse LLM response into decision."""
        ...


@dataclass
class SimpleContext:
    """Simplified context for beginners."""
    position: tuple[float, float, float]
    nearby_resources: list[dict]
    nearby_hazards: list[dict]
    inventory: list[str]
    goal: str | None
```

```python
# memory/base.py - Memory interface

class AgentMemory(ABC):
    """Interface for agent memory systems."""

    @abstractmethod
    def store(self, observation: Observation) -> None:
        """Store an observation."""
        pass

    @abstractmethod
    def retrieve(self, query: str | None = None) -> list[Observation]:
        """Retrieve relevant observations."""
        pass

    @abstractmethod
    def summarize(self) -> str:
        """Return memory as string for LLM context."""
        pass

    def clear(self) -> None:
        """Clear all memory."""
        pass
```

#### User Entry Point

```python
# run_agent.py - How users run their agents

from agent_runtime import AgentArena
from user_agents.my_agent import MyAgent

# Connect to Godot (framework handles IPC)
arena = AgentArena.connect(host="127.0.0.1", port=5000)

# Register agent behavior
arena.register("agent_001", MyAgent())

# Run (blocks, handles tick loop)
arena.run()
```

#### backends/
- `BaseBackend`: Abstract LLM backend interface
- `LlamaCppBackend`: llama.cpp integration
- `VLLMBackend`: vLLM integration
- `OpenAICompatBackend`: OpenAI-compatible APIs (OpenRouter, etc.)

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
