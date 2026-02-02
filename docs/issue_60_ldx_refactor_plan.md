# Issue #60: Refactor Codebase to Match LDX Architecture

## Executive Summary

This document defines the requirements and proposed changes for refactoring Agent Arena from a **framework-based approach** to a **"learner owns the code"** architecture as specified in the Learner Developer Experience (LDX) documentation.

**Key Transformation:**
- FROM: Framework with hidden base classes (`SimpleAgentBehavior`, `AgentBehavior`, `LLMAgentBehavior`)
- TO: Minimal SDK (IPC only) + starter templates (learner-visible code)

---

## Current vs Target Architecture

### Current State

```
python/agent_runtime/
├── behavior.py              # Base classes: SimpleAgentBehavior, AgentBehavior, LLMAgentBehavior
├── local_llm_behavior.py    # LocalLLMBehavior with LLM integration
├── memory/                  # Memory systems hidden in framework
│   ├── sliding_window.py
│   ├── spatial.py
│   ├── rag.py
│   └── summarizing.py
├── schemas.py               # Observation, AgentDecision, ToolSchema, etc.
└── __init__.py              # Exports all framework components

starters/
├── README.md                # Documentation only - templates are empty
├── beginner/                # Empty
├── intermediate/            # Empty
└── llm/                     # Empty
```

**Current Pattern (Framework-based):**
```python
from agent_runtime import SimpleAgentBehavior  # Hidden magic

class MyAgent(SimpleAgentBehavior):  # Inherit from base class
    def decide(self, context):       # Framework controls everything
        return "move_to"             # Returns just tool name
```

### Target State

```
python/sdk/agent_arena_sdk/
├── __init__.py              # Exports: AgentArena, Observation, Decision, Objective, ToolSchema
├── arena.py                 # Connection manager (thin wrapper)
├── schemas/
│   ├── observation.py       # Observation with objective + current_progress
│   ├── decision.py          # Simple Decision class
│   ├── objective.py         # NEW: Objective model
│   └── tools.py             # ToolSchema
└── server/
    └── ipc_server.py        # Minimal FastAPI IPC server

starters/
├── beginner/
│   ├── agent.py             # Complete working agent (learner owns)
│   └── run.py               # Entry point
├── intermediate/
│   ├── agent.py             # Agent with memory
│   ├── memory.py            # SlidingWindowMemory (learner owns!)
│   └── planner.py           # Goal decomposition
└── llm/
    ├── agent.py             # LLM-powered agent
    ├── llm_client.py        # LLM API wrapper (learner owns!)
    └── prompts/             # Prompt templates
```

**Target Pattern (Learner-owned):**
```python
from agent_arena_sdk import Observation, Decision  # Just schemas

class Agent:  # NO base class - plain Python class
    def decide(self, obs: Observation) -> Decision:
        return Decision(tool="move_to", params={"target_position": [1, 0, 2]})
```

---

## Phase 1: Create Minimal SDK

### 1.1 New Directory Structure

Create `python/sdk/agent_arena_sdk/`:

```
python/sdk/
├── agent_arena_sdk/
│   ├── __init__.py
│   ├── arena.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── observation.py
│   │   ├── decision.py
│   │   ├── objective.py      # NEW
│   │   └── tools.py
│   └── server/
│       ├── __init__.py
│       └── ipc_server.py
├── pyproject.toml
└── README.md
```

### 1.2 SDK Schema Definitions

#### `schemas/objective.py` (NEW)

```python
from dataclasses import dataclass, field

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
    success_metrics: dict[str, MetricDefinition] = field(default_factory=dict)
    time_limit: int = 0  # 0 = unlimited
```

#### `schemas/observation.py`

Extract from `agent_runtime/schemas.py` (lines 303-490) and ADD:

```python
# NEW fields to add to Observation class:
scenario_name: str = ""
objective: Objective | None = None
current_progress: dict[str, float] = field(default_factory=dict)
```

#### `schemas/decision.py`

Simplified from `AgentDecision` (schemas.py lines 493-727):

```python
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

**Remove:** Complex LLM response parsing logic (that goes in LLM starter)

### 1.3 SDK Arena/IPC

#### `arena.py`

Extract simplified version from `agent_runtime/arena.py`:

```python
class AgentArena:
    """Connection manager for Agent Arena game."""

    def __init__(self, host: str = "127.0.0.1", port: int = 5000):
        self.host = host
        self.port = port

    def run(self, decide_callback: Callable[[Observation], Decision]):
        """Run the agent server with given decision callback."""
        # Create FastAPI app with /tick endpoint
        # Call decide_callback for each observation
        # Return decision to game
```

#### `server/ipc_server.py`

Strip down from `python/ipc/server.py`:

**KEEP:**
- `/tick` POST endpoint (core game loop)
- `/health` GET endpoint
- Observation parsing (with new objective fields)
- Decision serialization

**REMOVE:**
- Behavior dictionary management
- Tool dispatcher (tools execute in Godot)
- Mock decision making
- `/agents/register`, `/tools/execute`, `/memory/{agent_id}` endpoints

---

## Phase 2: Populate Starter Templates

### 2.1 Beginner Starter

**Files to create in `starters/beginner/`:**

| File | Source | Notes |
|------|--------|-------|
| `agent.py` | New implementation | Priority-based if/else logic |
| `run.py` | New implementation | Entry point using SDK |
| `requirements.txt` | New | Just `agent-arena-sdk` |
| `README.md` | Update existing | Instructions |

**`agent.py` key methods:**
- `decide(obs: Observation) -> Decision` - Main decision logic
- `escape_hazard(hazard, obs)` - Move away from danger
- `pursue_resources(obs)` - Find and collect resources
- `check_objective(obs)` - Read objective and adapt

### 2.2 Intermediate Starter

**Files to create in `starters/intermediate/`:**

| File | Source | Notes |
|------|--------|-------|
| `agent.py` | New implementation | Uses memory + planner |
| `memory.py` | Extract from `agent_runtime/memory/sliding_window.py` | Simplified, learner-owned |
| `planner.py` | New implementation | Goal decomposition |
| `run.py` | New | Entry point |
| `requirements.txt` | New | Just `agent-arena-sdk` |

**`memory.py` methods to include:**
- `store(observation)` - Add observation
- `get_recent(n)` - Get last N observations
- `find_resources_seen()` - Query remembered resources
- `clear()` - Reset memory

**`planner.py` methods:**
- `decompose(objective, progress)` - Break into sub-goals
- `select_goal(sub_goals)` - Pick highest priority
- `calculate_priority(metric, current, target)` - Priority scoring

### 2.3 LLM Starter

**Files to create in `starters/llm/`:**

| File | Source | Notes |
|------|--------|-------|
| `agent.py` | New implementation | Uses LLM client |
| `memory.py` | Copy from intermediate | Same base memory |
| `llm_client.py` | Extract from `behavior.py` LLMAgentBehavior | LLM API wrapper |
| `prompts/system.txt` | New | System prompt template |
| `prompts/decision.txt` | New | Decision prompt template |
| `run.py` | New | Entry point |
| `requirements.txt` | New | `agent-arena-sdk`, `anthropic` |

**`llm_client.py` methods:**
- `__init__(backend, model)` - Initialize client
- `complete(system_prompt, user_prompt, temperature)` - Get completion
- Support backends: anthropic, openai, ollama

**`agent.py` methods:**
- `decide(obs)` - Build context, call LLM, parse response
- `build_context(obs)` - Format observation for LLM
- `parse_response(response, tools)` - Extract tool call from LLM output

---

## Phase 3: Update IPC Protocol

### 3.1 Schema Changes

**Files to modify:**

| File | Change |
|------|--------|
| `python/agent_runtime/schemas.py` | Add objective fields to Observation |
| `python/ipc/converters.py` | Parse new fields |
| `python/ipc/messages.py` | Update PerceptionMessage |

**Add to Observation class (around line 318):**
```python
# Objective system fields (NEW)
scenario_name: str = ""
objective: "Objective | None" = None
current_progress: dict[str, float] = field(default_factory=dict)
```

**Add Objective dataclass (NEW):**
```python
@dataclass
class MetricDefinition:
    target: float
    weight: float = 1.0
    lower_is_better: bool = False
    required: bool = False

@dataclass
class Objective:
    description: str
    success_metrics: dict[str, MetricDefinition] = field(default_factory=dict)
    time_limit: int = 0
```

### 3.2 Godot-Side Changes

**Files to modify:**

| File | Change |
|------|--------|
| `scripts/foraging.gd` | Add objective data to perception |
| `scripts/base_scene_controller.gd` | Define objective interface |

**Add to `_build_perception()` in scene controllers:**
```gdscript
perception["scenario_name"] = "foraging"
perception["objective"] = {
    "description": "Collect resources while avoiding hazards.",
    "success_metrics": {
        "resources_collected": {"target": 10, "weight": 1.0},
        "health_remaining": {"target": 50, "weight": 0.5}
    },
    "time_limit": 600
}
perception["current_progress"] = {
    "resources_collected": _resources_collected,
    "health_remaining": agent.health,
    "time_elapsed": _current_tick
}
```

### 3.3 Documentation Updates

**Files to modify:**

| File | Change |
|------|--------|
| `docs/ipc_protocol.md` | Add objective fields to perception format |
| `docs/objective_schema.md` | Already exists - verify matches implementation |

---

## Phase 4: Remove Old Code

### 4.1 Files to Delete

| File | Reason |
|------|--------|
| `python/agent_runtime/behavior.py` | Base classes replaced by starters |
| `python/agent_runtime/local_llm_behavior.py` | LLM code extracted to starters/llm/ |
| `python/agent_runtime/memory/` (folder) | Memory code extracted to starters |
| `python/user_agents/examples/` | Replaced by starters |

### 4.2 Update `agent_runtime/__init__.py`

**Remove old exports entirely:**
```python
# REMOVE these lines (9-11):
# from .behavior import AgentBehavior, LLMAgentBehavior, SimpleAgentBehavior
# from .local_llm_behavior import LocalLLMBehavior, create_local_llm_behavior
# from .memory import AgentMemory, RAGMemory, SlidingWindowMemory, SummarizingMemory

# Keep only core components needed by SDK
from .agent import Agent
from .arena import AgentArena
from .runtime import AgentRuntime
from .schemas import Observation, AgentDecision, ToolSchema
```

**Update `__all__` to remove behavior and memory exports.**

### 4.3 Demo Script Updates

**Files to update:**

| File | Change |
|------|--------|
| `python/run_foraging_demo.py` | Update to use SDK pattern |
| `python/run_agent.py` | Update to use SDK pattern |
| `python/run_local_llm_forager.py` | Archive or update |

**New demo pattern:**
```python
from agent_arena_sdk import AgentArena
from agent import Agent  # From copied starter

arena = AgentArena(host="127.0.0.1", port=5000)
agent = Agent()
arena.run(agent.decide)
```

---

## Implementation Order

### Phase 1: Foundation (SDK + Schemas)
1. Create `python/sdk/` directory structure
2. Create `schemas/objective.py` (NEW)
3. Extract `schemas/observation.py` (add objective fields)
4. Extract `schemas/decision.py` (simplified)
5. Extract `schemas/tools.py`
6. Create minimal `arena.py`
7. Create minimal `server/ipc_server.py`

### Phase 2: IPC Protocol Updates
1. Add objective fields to `agent_runtime/schemas.py`
2. Update `ipc/converters.py` for new fields
3. Update Godot scene controllers to send objectives
4. Update `docs/ipc_protocol.md`

### Phase 3: Starter Templates
1. Beginner starter (validates SDK works)
2. Intermediate starter (validates memory extraction)
3. LLM starter (validates LLM extraction)

### Phase 4: Clean Up Old Code
1. Remove old exports from `__init__.py`
2. Update demo scripts to new pattern
3. Delete old behavior classes
4. Delete memory folder (code now lives in starters)

### Phase 5: Testing & Documentation
1. Test SDK with each starter
2. Test end-to-end flow (Godot → SDK → Starter)
3. Update README.md quickstart

### Phase 6: Documentation Audit (Issue #61)
1. Audit all docs in `docs/` for old patterns
2. Update learner tutorials (`docs/learners/`)
3. Remove/archive obsolete documentation
4. Verify all code examples work with new SDK

---

## Files Summary

### New Files to Create

| Path | Purpose |
|------|---------|
| `python/sdk/agent_arena_sdk/__init__.py` | SDK exports |
| `python/sdk/agent_arena_sdk/arena.py` | Connection manager |
| `python/sdk/agent_arena_sdk/schemas/__init__.py` | Schema exports |
| `python/sdk/agent_arena_sdk/schemas/observation.py` | Observation model |
| `python/sdk/agent_arena_sdk/schemas/decision.py` | Decision model |
| `python/sdk/agent_arena_sdk/schemas/objective.py` | Objective model (NEW) |
| `python/sdk/agent_arena_sdk/schemas/tools.py` | ToolSchema model |
| `python/sdk/agent_arena_sdk/server/__init__.py` | Server exports |
| `python/sdk/agent_arena_sdk/server/ipc_server.py` | Minimal IPC server |
| `python/sdk/pyproject.toml` | Package config |
| `starters/beginner/agent.py` | Beginner agent implementation |
| `starters/beginner/run.py` | Entry point |
| `starters/beginner/requirements.txt` | Dependencies |
| `starters/intermediate/agent.py` | Intermediate agent |
| `starters/intermediate/memory.py` | Memory system |
| `starters/intermediate/planner.py` | Goal decomposition |
| `starters/intermediate/run.py` | Entry point |
| `starters/intermediate/requirements.txt` | Dependencies |
| `starters/llm/agent.py` | LLM agent |
| `starters/llm/memory.py` | Memory system |
| `starters/llm/llm_client.py` | LLM API wrapper |
| `starters/llm/prompts/system.txt` | System prompt |
| `starters/llm/prompts/decision.txt` | Decision prompt |
| `starters/llm/run.py` | Entry point |
| `starters/llm/requirements.txt` | Dependencies |

### Existing Files to Modify

| Path | Change |
|------|--------|
| `python/agent_runtime/schemas.py` | Add Objective, MetricDefinition; add fields to Observation |
| `python/agent_runtime/__init__.py` | Remove old exports |
| `python/ipc/converters.py` | Parse objective fields |
| `scripts/foraging.gd` | Send objective data in perception |
| `scripts/base_scene_controller.gd` | Define objective interface |
| `docs/ipc_protocol.md` | Document objective fields |
| `python/run_foraging_demo.py` | Update to SDK pattern |

### Files to Delete

| Path | Reason |
|------|--------|
| `python/agent_runtime/behavior.py` | Base classes replaced by starters |
| `python/agent_runtime/local_llm_behavior.py` | LLM code now in starters/llm/ |
| `python/agent_runtime/memory/` | Memory code now in starters |
| `python/user_agents/examples/` | Replaced by starters |

---

## Verification

### Test SDK Installation
```bash
cd python/sdk
pip install -e .
python -c "from agent_arena_sdk import Observation, Decision, Objective"
```

### Test Each Starter
```bash
# Beginner
cd starters/beginner
pip install -r requirements.txt
python run.py  # Then connect from Godot

# Intermediate
cd starters/intermediate
pip install -r requirements.txt
python run.py

# LLM
cd starters/llm
export ANTHROPIC_API_KEY=...
pip install -r requirements.txt
python run.py
```

### Test Objective Flow
1. Start agent with beginner starter
2. Load foraging scene in Godot
3. Connect agent
4. Verify observation includes `scenario_name`, `objective`, `current_progress`
5. Verify agent can read and respond to objectives

---

## Dependencies

**This issue depends on:**
- Issue #57: Create starter templates (provides directory structure) - can be done in parallel
- Issue #58: Implement objective system (defines observation fields) - can be done in parallel

**This issue blocks:**
- Issue #50: SDK package (can't publish until refactored)
- Issue #61: Documentation update (docs can't be updated until refactor is complete)

---

## Acceptance Criteria

1. `python/sdk/` contains minimal SDK with only IPC and schemas
2. `starters/beginner/`, `starters/intermediate/`, `starters/llm/` contain complete working implementations
3. Old base classes (`SimpleAgentBehavior`, `AgentBehavior`, `LLMAgentBehavior`) are deleted
4. Memory systems live in starters, not framework
5. Observation includes `objective` and `current_progress` fields
6. Godot sends objective data in perception
7. Demo scripts updated to new SDK pattern
8. `agent_runtime/__init__.py` exports only core components (no behaviors/memory)
