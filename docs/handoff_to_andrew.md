# Project Handoff: Agent Arena

**Date:** February 2026
**From:** Justin
**To:** Andrew

---

## TL;DR

Agent Arena is a platform for building AI agents in 3D simulated environments. The core tech works (Godot simulation + Python agent IPC), but we're in the middle of a major architectural shift to make it easier for external learners to use.

**Your primary task:** Implement the LDX refactor (Issue #60) which transforms the codebase from a framework-based approach to a "learner owns the code" architecture.

---

## Current State

### What Works
- Godot 3D simulation with foraging scenario
- Python ↔ Godot IPC communication (HTTP/JSON via FastAPI)
- Agent behaviors with LLM integration (local models via llama.cpp, vLLM)
- Memory systems (sliding window, spatial, RAG)
- Basic tool system (move_to, collect, etc.)
- Trace/debugging system for observing agent decisions

### What's In Progress
- **LDX Architecture Refactor** (Issue #60) - THE BIG ONE
- Objective system for scenarios (Issue #58)
- Starter templates (Issue #57)

### What Needs Building
- Standalone game builds (no Godot IDE required)
- SDK package for PyPI
- More scenarios (crafting, team capture)
- Leaderboard system
- In-game debug tools

---

## The LDX Vision (Most Important!)

We're shifting from this:
```python
# OLD: Hidden framework magic
from agent_runtime import SimpleAgentBehavior

class MyAgent(SimpleAgentBehavior):  # Inherit from base class
    def decide(self, context):
        return "move_to"  # Framework handles everything
```

To this:
```python
# NEW: Learner owns all the code
from agent_arena_sdk import Observation, Decision

class Agent:  # No base class - plain Python
    def decide(self, obs: Observation) -> Decision:
        return Decision(tool="move_to", params={"target_position": [1, 0, 2]})
```

**Why?** External learners (students, hobbyists) need to see and understand all their code. Hidden framework magic is confusing and hard to debug.

**Key docs:**
- [docs/learner_developer_experience.md](learner_developer_experience.md) - The full LDX philosophy
- [docs/issue_60_ldx_refactor_plan.md](issue_60_ldx_refactor_plan.md) - Detailed implementation plan
- [docs/new_architecture.md](new_architecture.md) - New architecture (replaces old one after refactor)

---

## GitHub Issues - Priority Order

### Epic: LDX Refactor
| Issue | Title | Priority | Notes |
|-------|-------|----------|-------|
| #56 | [Epic] Learner Developer Experience | - | Parent epic, tracks overall progress |
| **#60** | **Refactor codebase to match LDX architecture** | **HIGH** | **START HERE** - the main refactor task |
| #57 | Create starter templates | HIGH | Beginner/intermediate/LLM starters |
| #58 | Implement objective system in Godot | HIGH | Scenarios send goals to agents |
| #50 | Create agent-arena-sdk package | HIGH | Blocked by #60 |
| #51 | Standalone game builds | HIGH | No Godot IDE for learners |

### Supporting Work
| Issue | Title | Priority |
|-------|-------|----------|
| #61 | Update all documentation for LDX | HIGH (after #60) |
| #55 | In-game debug tools | HIGH |
| #52 | CLI tools for SDK | MEDIUM |
| #53 | In-game server connection UI | MEDIUM |
| #54 | Hot-reload support | MEDIUM |
| #59 | Leaderboard system | MEDIUM |

### Future (After LDX)
- #26, #27 - Populate crafting/team capture scenes
- #31-36 - Advanced tooling (prompt inspector, step debug, etc.)

---

## Key Files to Know

### Python
| Path | Purpose |
|------|---------|
| `python/agent_runtime/schemas.py` | Core data schemas (Observation, Decision, etc.) |
| `python/agent_runtime/behavior.py` | Current base classes (TO BE REMOVED) |
| `python/agent_runtime/memory/` | Memory implementations (TO MOVE TO STARTERS) |
| `python/ipc/server.py` | FastAPI IPC server |
| `python/run_foraging_demo.py` | Example of running an agent |

### Godot
| Path | Purpose |
|------|---------|
| `scripts/autoload/ipc_service.gd` | HTTP client for Python communication |
| `scripts/autoload/tool_registry_service.gd` | Tool execution |
| `scripts/simple_agent.gd` | Agent entity with movement/perception |
| `scripts/foraging.gd` | Foraging scenario controller |
| `scripts/base_scene_controller.gd` | Base class for scenarios |

### Starters (Currently Empty)
| Path | Purpose |
|------|---------|
| `starters/beginner/` | Simple if/else agent template |
| `starters/intermediate/` | Memory + planning template |
| `starters/llm/` | LLM-powered agent template |

### Documentation
| Path | Purpose |
|------|---------|
| `docs/learner_developer_experience.md` | LDX philosophy and design |
| `docs/issue_60_ldx_refactor_plan.md` | Detailed refactor plan |
| `docs/new_architecture.md` | New architecture doc |
| `docs/objective_schema.md` | How objectives work |
| `docs/ipc_protocol.md` | Godot ↔ Python communication |

---

## Development Setup

### Prerequisites
- Godot 4.2+
- Python 3.11+
- Git

### Quick Start
```bash
# Clone
git clone https://github.com/JustInternetAI/AgentArena.git
cd AgentArena

# Python setup
cd python
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Run demo (Terminal 1)
python run_foraging_demo.py

# Open Godot project, run foraging.tscn (connects to Python)
```

### Branch Strategy
- `main` - Stable releases
- `JustinDev` - Justin's development branch (current work)
- Create feature branches from `main` for new work

---

## Architecture Quick Reference

```
┌─────────────────────────┐          ┌─────────────────────────┐
│     GODOT PROCESS       │          │     PYTHON PROCESS      │
│                         │   HTTP   │                         │
│  Simulation             │ ──────▶  │  FastAPI Server (:5000) │
│  Scene Controller       │ POST     │                         │
│  IPCService (client)    │ /tick    │  agent.decide(obs)      │
│                         │ ◀──────  │                         │
│  Tool Execution         │ response │                         │
└─────────────────────────┘          └─────────────────────────┘
```

- Godot runs the 3D simulation, sends observations to Python
- Python runs agent logic, returns decisions to Godot
- They're separate processes communicating via HTTP

---

## Known Issues / Gotchas

1. **Behavior dict reference bug** - In `ipc/server.py`, must use `behaviors if behaviors is not None else {}` not `behaviors or {}` (empty dict is falsy)

2. **Movement is frame-based** - `simple_agent.gd` uses `_process(delta)` for movement, not instant teleport

3. **Agent ID matching** - Godot agent_id must exactly match Python registered agent_id

4. **Hot reload** - Currently must restart Python process to reload agent code (Issue #54 to fix this)

5. **Old docs** - Some docs in `docs/learners/` reference the old framework patterns. These need updating after the LDX refactor (tracked in Issue #61).

---

## Questions / Support

- **Code questions:** Check existing docs first, then GitHub Issues
- **Architecture decisions:** Reference the LDX doc and issue #60 plan
- **Stuck?** Create a GitHub Discussion or Issue

---

## Recommended First Steps

1. **Read the LDX docs** (30 min)
   - `docs/learner_developer_experience.md`
   - `docs/issue_60_ldx_refactor_plan.md`

2. **Run the current demo** (15 min)
   - Start `python run_foraging_demo.py`
   - Open Godot, run `scenes/foraging.tscn`
   - Watch an agent collect berries

3. **Review Issue #60** on GitHub
   - Read the full issue description
   - Check the acceptance criteria

4. **Start implementing Phase 1** of the refactor
   - Create `python/sdk/` directory structure
   - Extract minimal schemas

---

**Good luck! The foundation is solid - the LDX refactor will make this project accessible to a much wider audience. 🚀**
