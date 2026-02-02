# Agent Arena Architecture

## Overview

Agent Arena is a platform for building and evaluating AI agents in simulated 3D environments. It combines a high-performance Godot engine for simulation with a minimal Python SDK that gives learners full visibility and control over their agent code.

## Design Philosophy

### Core Principle: Learner Owns the Code

Unlike traditional frameworks that hide complexity behind base classes, Agent Arena follows a **"learner owns the code"** approach:

```
┌─────────────────────────────────────────────────────────────────┐
│                    LEARNER'S VISIBLE CODE                       │
│                   (You write, read, and modify)                 │
│                                                                 │
│  • Agent decision logic (your agent.py)                         │
│  • Memory systems (your memory.py)                              │
│  • LLM integration (your llm_client.py)                         │
│  • Prompt templates (your prompts/)                             │
│  • Planning strategies (your planner.py)                        │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                     MINIMAL SDK                                 │
│                 (Thin IPC layer only)                           │
│                                                                 │
│  • AgentArena (connection manager)                              │
│  • Observation, Decision, Objective (data schemas)              │
│  • IPC Server (FastAPI endpoints)                               │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                      GAME ENGINE                                │
│                   (Standalone executable)                       │
│                                                                 │
│  • Godot 3D simulation                                          │
│  • Scenarios with objectives                                    │
│  • Tool execution                                               │
│  • Debug visualization                                          │
└─────────────────────────────────────────────────────────────────┘
```

**Key Benefits:**
- No hidden "framework magic" - every line of agent logic is visible
- Learners understand what their code does
- Easy to modify, extend, and experiment
- Standard Python development workflow

### What's NOT in the SDK

The SDK intentionally excludes:
- Base classes (`AgentBehavior`, `SimpleAgentBehavior`)
- Memory implementations
- LLM client wrappers
- Prompt templates
- Planning utilities

These live in **starter templates** that learners copy and own.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   LEARNER'S MACHINE                             │
├────────────────────────────┬────────────────────────────────────┤
│   Agent Arena Game         │   Learner's Python Environment    │
│   (Standalone EXE)         │                                    │
│                            │   ┌────────────────────────────┐   │
│   ┌────────────────────┐   │   │  agent-arena-sdk (pip)     │   │
│   │  Godot Simulation  │   │   │  • AgentArena              │   │
│   │  • 3D World        │   │   │  • Observation             │   │
│   │  • Physics         │   │   │  • Decision                │   │
│   │  • Navigation      │   │   │  • Objective               │   │
│   └────────────────────┘   │   └────────────────────────────┘   │
│                            │                                    │
│   ┌────────────────────┐   │   ┌────────────────────────────┐   │
│   │  Scenarios         │   │   │  Learner's Agent Code      │   │
│   │  • Foraging        │◀──┼──▶│  • agent.py (decision)     │   │
│   │  • Crafting        │   │   │  • memory.py (optional)    │   │
│   │  • Team Capture    │   │   │  • llm_client.py (optional)│   │
│   └────────────────────┘   │   └────────────────────────────┘   │
│                            │                                    │
│   ┌────────────────────┐   │                                    │
│   │  Objective System  │   │                                    │
│   │  • Goals           │   │                                    │
│   │  • Metrics         │   │                                    │
│   │  • Progress        │   │                                    │
│   └────────────────────┘   │                                    │
│                            │                                    │
│      ◀──── HTTP/JSON ────▶                                     │
└────────────────────────────┴────────────────────────────────────┘
```

---

## Component Details

### 1. Minimal SDK (`agent-arena-sdk`)

The SDK provides only what's needed for communication with the game.

**Directory Structure:**
```
python/sdk/agent_arena_sdk/
├── __init__.py              # Exports: AgentArena, Observation, Decision, Objective
├── arena.py                 # Connection manager
├── schemas/
│   ├── observation.py       # What agent receives each tick
│   ├── decision.py          # What agent returns
│   ├── objective.py         # Scenario goals
│   └── tools.py             # Tool definitions
└── server/
    └── ipc_server.py        # FastAPI server (minimal endpoints)
```

**SDK Schemas:**

```python
# observation.py
@dataclass
class Observation:
    """What the agent receives from the game each tick."""
    agent_id: str
    tick: int
    position: tuple[float, float, float]
    rotation: tuple[float, float, float] | None
    velocity: tuple[float, float, float] | None
    health: float
    energy: float
    nearby_resources: list[ResourceInfo]
    nearby_hazards: list[HazardInfo]
    visible_entities: list[EntityInfo]
    inventory: list[ItemInfo]

    # Objective system
    scenario_name: str
    objective: Objective | None
    current_progress: dict[str, float]
```

```python
# decision.py
@dataclass
class Decision:
    """What the agent returns to the game."""
    tool: str
    params: dict = field(default_factory=dict)
    reasoning: str | None = None

    @classmethod
    def idle(cls, reasoning: str | None = None) -> "Decision":
        return cls(tool="idle", params={}, reasoning=reasoning)
```

```python
# objective.py
@dataclass
class MetricDefinition:
    """Definition of a success metric."""
    target: float
    weight: float = 1.0
    lower_is_better: bool = False
    required: bool = False

@dataclass
class Objective:
    """Scenario-defined goals for the agent."""
    description: str
    success_metrics: dict[str, MetricDefinition]
    time_limit: int = 0  # 0 = unlimited
```

**SDK Usage:**

```python
from agent_arena_sdk import AgentArena, Observation, Decision

class Agent:
    def decide(self, obs: Observation) -> Decision:
        # Your logic here
        return Decision(tool="move_to", params={"target_position": [1, 0, 2]})

arena = AgentArena(host="127.0.0.1", port=5000)
agent = Agent()
arena.run(agent.decide)
```

### 2. Starter Templates

Starters are complete, working implementations that learners copy and modify. They demonstrate progressively more sophisticated agent architectures.

**Directory Structure:**
```
starters/
├── beginner/                # Simple if/else logic
│   ├── agent.py             # Priority-based decisions
│   ├── run.py               # Entry point
│   └── requirements.txt
│
├── intermediate/            # Memory + planning
│   ├── agent.py             # Uses memory and planner
│   ├── memory.py            # SlidingWindowMemory (YOUR code!)
│   ├── planner.py           # Goal decomposition (YOUR code!)
│   ├── run.py
│   └── requirements.txt
│
└── llm/                     # LLM-powered reasoning
    ├── agent.py             # LLM integration
    ├── memory.py            # Same as intermediate
    ├── llm_client.py        # LLM API wrapper (YOUR code!)
    ├── prompts/
    │   ├── system.txt       # System prompt (YOUR code!)
    │   └── decision.txt     # Decision prompt (YOUR code!)
    ├── run.py
    └── requirements.txt
```

**Beginner Pattern:**
```python
# starters/beginner/agent.py
from agent_arena_sdk import Observation, Decision

class Agent:
    def decide(self, obs: Observation) -> Decision:
        # Priority 1: Escape danger
        for hazard in obs.nearby_hazards:
            if hazard.distance < 3.0:
                return self.escape_from(obs.position, hazard.position)

        # Priority 2: Pursue objective
        if obs.objective and "resources_collected" in obs.objective.success_metrics:
            return self.pursue_resources(obs)

        return Decision.idle()
```

**Intermediate Pattern:**
```python
# starters/intermediate/agent.py
from agent_arena_sdk import Observation, Decision
from memory import SlidingWindowMemory
from planner import Planner

class Agent:
    def __init__(self):
        self.memory = SlidingWindowMemory(capacity=50)
        self.planner = Planner()

    def decide(self, obs: Observation) -> Decision:
        self.memory.store(obs)

        # Decompose objective into sub-goals
        sub_goals = self.planner.decompose(obs.objective, obs.current_progress)
        current_goal = self.planner.select_goal(sub_goals)

        return self.execute_goal(current_goal, obs)
```

**LLM Pattern:**
```python
# starters/llm/agent.py
from agent_arena_sdk import Observation, Decision
from memory import SlidingWindowMemory
from llm_client import LLMClient

class Agent:
    def __init__(self):
        self.memory = SlidingWindowMemory(capacity=50)
        self.llm = LLMClient(backend="anthropic", model="claude-3-haiku-20240307")

    def decide(self, obs: Observation) -> Decision:
        self.memory.store(obs)
        context = self.build_context(obs)
        response = self.llm.complete(self.system_prompt, context)
        return self.parse_response(response)
```

### 3. Godot Game Engine

The game is distributed as a standalone executable (no Godot IDE required).

**Key Components:**

- `SimulationManager`: Deterministic tick loop and simulation state
- `EventBus`: Event recording for replay and reproducibility
- `SimpleAgent`: Agent entity with perception and tool execution
- `ToolRegistry`: Available tools and their execution
- `IPCClient`: HTTP communication with Python backend

**Autoload Services:**

- `IPCService`: Global connection manager to Python backend
- `ToolRegistryService`: Global tool registration and execution

**Scene Controllers:**

Each scenario has a controller that:
- Builds perception data for agents
- Sends observations to Python via IPC
- Receives decisions and executes tools
- Tracks objective progress

### 4. Objective System

Scenarios communicate goals to agents through the objective system.

**Flow:**
```
Scenario defines objective → Sent in observation → Agent reads and adapts
```

**Example Objective (Foraging):**
```json
{
    "scenario_name": "foraging",
    "objective": {
        "description": "Collect resources while avoiding hazards and staying healthy.",
        "success_metrics": {
            "resources_collected": {"target": 10, "weight": 1.0},
            "health_remaining": {"target": 50, "weight": 0.5},
            "time_taken": {"target": 300, "weight": 0.2, "lower_is_better": true}
        },
        "time_limit": 600
    },
    "current_progress": {
        "resources_collected": 3,
        "health_remaining": 85,
        "time_elapsed": 142
    }
}
```

**Using Objectives in Agent Code:**
```python
def decide(self, obs: Observation) -> Decision:
    objective = obs.objective
    progress = obs.current_progress

    # Check which metrics need work
    for metric, definition in objective.success_metrics.items():
        current = progress.get(metric, 0)
        target = definition.target

        if metric == "resources_collected" and current < target:
            return self.pursue_resources(obs)

        if metric == "health_remaining" and current < target:
            return self.seek_safety(obs)

    return Decision.idle()
```

---

## Communication Protocol

### IPC Overview

```
Godot (Game)  ◀──── HTTP/JSON ────▶  Python (Agent)
     │                                      │
     │ POST /tick                           │
     │ {observation}  ────────────────────▶ │
     │                                      │ agent.decide(obs)
     │ ◀──────────────────────────────────  │
     │ {decision}                           │
     │                                      │
     │ Execute tool                         │
     ▼                                      │
```

### Message Formats

**Perception (Godot → Python):**
```json
{
    "tick": 1234,
    "agents": [{
        "agent_id": "agent_001",
        "observations": {
            "position": [10.5, 0.0, 5.2],
            "rotation": [0.0, 90.0, 0.0],
            "health": 100.0,
            "energy": 100.0,
            "nearby_resources": [
                {"name": "berry_001", "type": "berry", "position": [12.0, 0.5, 6.0], "distance": 2.1}
            ],
            "nearby_hazards": [
                {"name": "fire_001", "type": "fire", "position": [7.0, 0.5, 3.0], "distance": 4.2, "damage": 10.0}
            ],
            "inventory": [],
            "scenario_name": "foraging",
            "objective": {...},
            "current_progress": {...}
        }
    }]
}
```

**Decision (Python → Godot):**
```json
{
    "tick": 1234,
    "actions": [{
        "agent_id": "agent_001",
        "action": {
            "tool": "move_to",
            "params": {"target_position": [12.0, 0.0, 6.0], "speed": 1.5},
            "reasoning": "Moving to nearest berry"
        }
    }]
}
```

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/tick` | POST | Process simulation tick (core loop) |
| `/health` | GET | Health check |

---

## Universal Tools

Agents use the same tools across all scenarios. What varies is the world content, not the API.

| Tool | Purpose | Parameters |
|------|---------|------------|
| `move_to` | Navigate to position | `target_position: [x, y, z]`, `speed: float` |
| `collect` | Pick up nearby resource | `target_name: str` |
| `craft` | Craft item at station | `item_name: str`, `station_name: str` |
| `query_world` | Get detailed surroundings | `radius: float`, `filter_type: str` |
| `query_inventory` | Check inventory | - |
| `send_message` | Team communication | `message: str`, `target_agent: str` |
| `idle` | Do nothing this tick | - |

---

## Benchmark Scenarios

### 1. Foraging

**Goal:** Collect resources while avoiding hazards

**Metrics:**
- Resources collected
- Health remaining
- Time taken

**Teaches:** Basic perception-decision-action loop, hazard avoidance

### 2. Crafting Chain

**Goal:** Gather materials and craft complex items

**Metrics:**
- Target item crafted
- Materials wasted
- Time taken

**Teaches:** Multi-step planning, resource management, station usage

### 3. Team Capture

**Goal:** Coordinate with teammates to capture objectives

**Metrics:**
- Team score
- Points captured
- Team deaths

**Teaches:** Multi-agent coordination, communication, team strategy

---

## Deterministic Simulation

### Requirements

1. **Fixed Tick Rate:** Simulation advances in discrete ticks (60/sec)
2. **Seedable RNG:** All randomness uses seeded generators
3. **Event Ordering:** Events processed in deterministic order
4. **Replay Logs:** All events recorded with timestamps

### Replay System

Enables:
- Reproducible evaluation
- Debugging agent behavior
- Sharing interesting runs

---

## Development Workflow

### Getting Started

```bash
# 1. Download game from releases
# 2. Create project
mkdir my-agent && cd my-agent
python -m venv venv && venv\Scripts\activate

# 3. Install SDK
pip install agent-arena-sdk

# 4. Copy a starter
agent-arena init beginner

# 5. Run agent
python run.py

# 6. Launch game, connect, run scenario
```

### Daily Development

```bash
# Terminal 1: Run agent
python run.py --debug

# Terminal 2: Edit agent.py
# Save changes

# In game: Press R to reset, test changes
```

### Debugging

| Tool | Command |
|------|---------|
| Debug logging | `python run.py --debug` |
| Memory inspection | `agent-arena debug memory` |
| Decision trace | `agent-arena debug trace` |
| LLM prompts | `agent-arena debug prompts` |

**In-Game:**
- `D` - Debug overlay
- `P` - Pause/step mode
- `T` - Decision trace
- `L` - LLM inspector

---

## Extensibility

### Adding New Scenarios

1. Create Godot scene with required nodes
2. Implement scene controller with objective system
3. Define success metrics
4. Add to scenario selector

### Adding New Tools

1. Implement tool in `ToolRegistryService` (Godot)
2. Register with tool schema
3. Document parameters and behavior

### Custom Agent Architectures

Since learners own all their code, they can:
- Implement custom memory systems
- Use different LLM providers
- Add reflection and planning
- Integrate external APIs
- Build multi-agent communication

---

## Performance Considerations

### Bottlenecks

| Component | Typical Latency |
|-----------|-----------------|
| LLM Inference | 100-1000ms |
| IPC Overhead | 1-10ms |
| Memory Retrieval | 10-50ms |

### Optimizations

- **Async LLM:** Queue decisions while LLM processes
- **Caching:** Cache similar decisions
- **Batching:** Process multiple agents together
- **Model Quantization:** Use smaller/quantized models

---

## File Reference

### SDK
- `python/sdk/agent_arena_sdk/` - Minimal SDK package

### Starters
- `starters/beginner/` - Simple if/else agent
- `starters/intermediate/` - Memory + planning
- `starters/llm/` - LLM-powered agent

### Godot
- `scripts/autoload/ipc_service.gd` - IPC connection
- `scripts/autoload/tool_registry_service.gd` - Tool execution
- `scripts/simple_agent.gd` - Agent entity
- `scripts/base_scene_controller.gd` - Scenario base
- `scripts/foraging.gd` - Foraging scenario

### Documentation
- `docs/learner_developer_experience.md` - LDX philosophy
- `docs/objective_schema.md` - Objective system
- `docs/ipc_protocol.md` - Communication details
- `docs/universal_tools.md` - Tool reference
