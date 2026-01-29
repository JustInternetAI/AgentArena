# Agent Arena Architecture

## Overview

Agent Arena is designed as a hybrid system combining a high-performance Godot C++ module for deterministic simulation with a flexible Python runtime for LLM-driven agent reasoning.

## Design Philosophy

Agent Arena follows a clear principle: **learner clarity over performance optimization**.

### Separation of Concerns

```
┌─────────────────────────────────────────────────────────────────┐
│                        LEARNER SPACE                            │
│                   (What you write and control)                  │
│                                                                 │
│  • Agent behaviors (decide logic)                               │
│  • Prompts and prompt templates                                 │
│  • Memory management and inspection                             │
│  • Reflection, planning, and reasoning traces                   │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                       INFRASTRUCTURE                            │
│                     (Hidden, just works)                        │
│                                                                 │
│  • IPC Server (FastAPI, HTTP handling)                          │
│  • LLM Backends (llama.cpp, vLLM)                               │
│  • GPU memory management                                        │
│  • Model loading and inference                                  │
│  • Godot communication protocol                                 │
└─────────────────────────────────────────────────────────────────┘
```

**The Learner Interface**: Learners interact with a simple, well-defined contract:

- **Input**: `Observation` (position, nearby resources, hazards, inventory)
- **Output**: `AgentDecision` (tool name, parameters, reasoning)

Everything else - how observations arrive, how decisions execute, what LLM powers inference - is infrastructure that learners don't need to understand.

See [learner_tiers.md](learner_tiers.md) for the complete progression guide.

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

#### Three-Tier Learning Progression

The framework provides three tiers of abstraction, designed as a learning progression.
See [learner_tiers.md](learner_tiers.md) for detailed documentation and examples.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  TIER 1: BEGINNER                                                        │
│  SimpleAgentBehavior                                                     │
│  ─────────────────────                                                   │
│  • User returns: tool name (string)                                      │
│  • Framework handles: parameters, memory, context building               │
│  • Focus: Understanding perception → decision → action loop              │
│  • No LLM required                                                       │
├─────────────────────────────────────────────────────────────────────────┤
│  TIER 2: INTERMEDIATE                                                    │
│  AgentBehavior + LLMAgentBehavior                                        │
│  ────────────────────────────────                                        │
│  • User returns: AgentDecision with tool, params, reasoning              │
│  • User customizes: prompt templates, response parsing                   │
│  • User implements: lifecycle hooks (on_episode_start, on_tool_result)   │
│  • Focus: Prompt engineering, LLM integration, state tracking            │
├─────────────────────────────────────────────────────────────────────────┤
│  TIER 3: ADVANCED                                                        │
│  LLMAgentBehavior + Memory/Reflection Extensions                         │
│  ───────────────────────────────────────────────                         │
│  • User controls: memory storage and retrieval (self.memory)             │
│  • User implements: reflection hooks, planning strategies                │
│  • User inspects: reasoning traces, decision logs                        │
│  • Tooling: Memory viewer, decision inspector, trace debugger            │
│  • Focus: Learning from experience, multi-step planning, self-improvement│
└─────────────────────────────────────────────────────────────────────────┘
```

**Tier 3 Capabilities** (for advanced learners):

| Capability | What You Control | Inspection Tool |
|------------|------------------|-----------------|
| **Prompting** | `build_prompt()`, templates | Log full prompt before send |
| **Memory** | `self.memory.add()`, `memory.query()` | `memory.dump()`, memory viewer |
| **Reasoning** | `self.reasoning_trace` | Step-by-step decision log |
| **Reflection** | `reflect(outcome)` → stored insights | View past reflections |
| **Planning** | `plan()` → multi-step strategies | Visualize plan tree |

**Key Design Principles:**

1. **Learners don't need C++ knowledge** - The C++ GDExtension module handles all low-level simulation details (raycasting, pathfinding, collision detection). Learners work exclusively in Python.

2. **Learners don't need game development knowledge** - GDScript wrappers handle Godot integration, animation, and world interaction. Learners focus on agent logic.

3. **Progressive complexity** - Each tier builds on the previous, allowing learners to gradually take more control as they understand more concepts.

4. **Python is the "brain"** - All decision-making logic lives in Python. Godot and C++ provide the "body" (perception and execution).

See [Learner Documentation](learners/getting_started.md) for tutorials at each tier.

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

**Current Implementation: HTTP/REST (FastAPI)**

The foraging demo uses a working HTTP-based IPC system that demonstrates the full observation-decision-execution loop.

**Architecture:**

```
┌─────────────────────────────────────────────────────────────┐
│                Godot Scene (foraging.tscn)                  │
│                                                             │
│  ┌────────────────┐              ┌──────────────────┐      │
│  │SceneController │──observe────▶│  HTTPRequest     │──┐   │
│  │  (foraging.gd) │              │                  │  │   │
│  │                │◀────result───│                  │◀─┘   │
│  └────────┬───────┘              └──────────────────┘      │
│           │                                                 │
│           │ call_tool(decision)                             │
│           │                                                 │
│  ┌────────▼───────┐              ┌──────────────────┐      │
│  │  SimpleAgent   │──execute────▶│ToolRegistryService│     │
│  │(simple_agent.gd)│              │                  │      │
│  └────────────────┘              └──────────────────┘      │
└─────────────────────────────────────────────────────────────┘
                       │                   ▲
                       │ POST /observe     │ response
                       ▼                   │
┌─────────────────────────────────────────────────────────────┐
│              Python IPC Server (FastAPI)                    │
│                                                             │
│  ┌────────────────┐              ┌──────────────────┐      │
│  │   IPCServer    │──lookup─────▶│  AgentArena      │      │
│  │                │              │  .behaviors{}    │      │
│  │  /observe      │◀────behavior─│                  │      │
│  │  /tool         │              │                  │      │
│  └────────┬───────┘              └──────────────────┘      │
│           │                                                 │
│           │ behavior.decide(obs, tools)                     │
│           │                                                 │
│  ┌────────▼───────────────────────────────────────┐        │
│  │  SimpleForager (user_agents/examples/)         │        │
│  │  - Finds nearest resource                      │        │
│  │  - Avoids hazards                              │        │
│  │  - Returns AgentDecision(tool, params)         │        │
│  └────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

**Implementation Details:**

1. **Behavior Registration** ([run_foraging_demo.py](../python/run_foraging_demo.py)):
   ```python
   arena = AgentArena.connect(host="127.0.0.1", port=5000)
   arena.register("foraging_agent_001", SimpleForager(memory_capacity=10))
   arena.run()  # Starts FastAPI server
   ```

2. **Observation Endpoint** ([ipc/server.py:397-495](../python/ipc/server.py#L397-L495)):
   ```python
   @app.post("/observe")
   async def process_observation(observation: dict) -> dict:
       agent_id = observation.get("agent_id")
       behavior = self.behaviors.get(agent_id)  # Lookup registered behavior

       if behavior:
           # Convert Godot dict -> Observation schema
           obs = perception_to_observation(perception)

           # Get tool schemas
           tool_schemas = [...]

           # Agent decides action
           decision = behavior.decide(obs, tool_schemas)

           return {
               "tool": decision.tool,
               "params": decision.params,
               "reasoning": decision.reasoning
           }
       else:
           # Fallback to mock logic
           return self._make_mock_decision(observation)
   ```

3. **Scene Observation Sending** ([base_scene_controller.gd](../scripts/base_scene_controller.gd)):
   ```gdscript
   func _request_backend_decision(agent_data, observations, tick):
       var body = JSON.stringify({
           "agent_id": agent_data.id,
           "tick": tick,
           "position": observations.position,
           "nearby_resources": observations.nearby_resources,
           "nearby_hazards": observations.nearby_hazards
       })

       http_request.request(backend_url + "/observe", headers, HTTPClient.METHOD_POST, body)
   ```

4. **Decision Execution** ([foraging.gd:173-175](../scripts/foraging.gd#L173-L175)):
   ```gdscript
   func _execute_backend_decision(agent_data, decision):
       # Call agent's tool with params from Python decision
       agent_data.agent.call_tool(decision.tool, decision.params)
   ```

5. **Movement Implementation** ([simple_agent.gd:130-151](../scripts/simple_agent.gd#L130-L151)):
   ```gdscript
   func call_tool(tool_name: String, parameters: Dictionary = {}):
       if tool_name == "move_to":
           _target_position = Vector3(parameters.target_position[0],
                                      parameters.target_position[1],
                                      parameters.target_position[2])
           _movement_speed = parameters.get("speed", 1.0)
           _is_moving = true

       return ToolRegistryService.execute_tool(agent_id, tool_name, parameters)

   func _process(delta):
       if _is_moving:
           var direction = (_target_position - global_position).normalized()
           var move_distance = _movement_speed * move_speed * delta
           global_position += direction * move_distance
   ```

**Critical Implementation Notes:**

- **Behavior Reference Bug**: Must use `behaviors if behaviors is not None else {}` instead of `behaviors or {}` to preserve dict reference when empty
- **Movement Implementation**: SimpleAgent must implement `_process(delta)` for frame-based movement, not just return success from tool calls
- **Agent ID Matching**: Godot agent_id must exactly match registered Python agent_id

**Other IPC Options (Not Currently Implemented):**

1. **gRPC** (Recommended for production)
   - Bidirectional streaming
   - Type-safe protocol buffers
   - Low latency

2. **Shared Memory** (Highest performance)
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
