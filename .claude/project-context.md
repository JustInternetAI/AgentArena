# Agent Arena - Project Context

Quick reference for Claude Code sessions.

## Project Overview
- **Name**: Agent Arena
- **Repo**: https://github.com/JustInternetAI/AgentArena
- **Local Path**: `c:\Projects\Agent Arena`
- **Founders**: Andrew Madison & Justin Madison
- **Organization**: JustInternetAI

---

## Vision & Purpose

### What is Agent Arena?

Agent Arena is an **educational framework for learning agentic AI programming** through interactive game scenarios. Rather than reading about agents in isolation, developers build and deploy AI agents into simulated environments where they can observe, debug, and iterate on agent behavior in real-time.

Think of it as a **"gym" for AI agents** - a place where developers can:
- Learn the fundamentals of agentic AI (perception, reasoning, tool use, memory)
- Experiment with different architectures and LLM backends
- Test agents against progressively challenging scenarios
- Compare approaches and share results

### Why Agent Arena?

**The Problem**: Agentic AI is becoming essential, but learning it is fragmented. Tutorials show toy examples. Real deployments are too complex. There's no middle ground where you can safely experiment and see immediate results.

**The Solution**: A game-like environment where:
1. **Scenarios are self-contained** - Clear objectives, measurable outcomes
2. **Feedback is immediate** - Watch your agent succeed or fail in real-time
3. **Debugging is possible** - Deterministic replay, step-through mode, prompt inspection
4. **Complexity is progressive** - Start simple, unlock harder challenges

### Core Educational Goals

1. **Tool Use** - Learn how agents call functions to interact with the world
2. **Observation Processing** - Understand how agents perceive and interpret their environment
3. **Memory Systems** - Implement short-term, long-term, and episodic memory
4. **Planning & Reasoning** - Build agents that decompose goals and execute multi-step plans
5. **Multi-Agent Coordination** - Design agents that communicate and cooperate

### Target Audience

- **AI/ML developers** wanting hands-on experience with agentic systems
- **Students** learning about autonomous agents and LLM applications
- **Researchers** needing reproducible benchmarks for agent evaluation
- **Hobbyists** who want to build and experiment with AI agents

---

## Scenario Progression (Learning Path)

Scenarios are designed to progressively introduce agentic concepts:

### Tier 1: Foundations
| Scenario | Concepts Taught |
|----------|-----------------|
| **Simple Navigation** | Basic tool use, movement, observation handling |
| **Foraging** | Resource detection, goal-directed behavior, basic planning |
| **Obstacle Course** | Spatial reasoning, sequential decision-making |

### Tier 2: Memory & Planning
| Scenario | Concepts Taught |
|----------|-----------------|
| **Crafting Chain** | Multi-step planning, dependency resolution, inventory management |
| **Scavenger Hunt** | Long-term memory, revisiting locations, deferred goals |
| **Maze Exploration** | Map building, memory-augmented navigation |

### Tier 3: Adversarial & Dynamic
| Scenario | Concepts Taught |
|----------|-----------------|
| **Predator Evasion** | Reactive planning, risk assessment, dynamic re-planning |
| **Resource Competition** | Opponent modeling, strategic behavior |
| **Tower Defense** | Real-time decision-making under pressure |

### Tier 4: Multi-Agent Cooperation
| Scenario | Concepts Taught |
|----------|-----------------|
| **Team Capture** | Communication, role assignment, coordinated actions |
| **Collaborative Building** | Shared goals, task distribution, conflict resolution |
| **Relay Race** | Handoffs, timing, trust between agents |

---

## Design Principles

1. **Observability First** - Every agent decision should be inspectable (what it saw, what it thought, what it did)
2. **Deterministic Replay** - Any run can be replayed exactly for debugging and comparison
3. **Backend Agnostic** - Swap LLM backends without changing agent code (llama.cpp, vLLM, OpenAI, etc.)
4. **Scenario as Curriculum** - Scenarios teach specific skills, ordered by complexity
5. **Metrics Matter** - Every scenario has clear success metrics for objective comparison
6. **Layered Complexity** - Simple interface for beginners, full control for advanced users

---

## Three-Tier Agent Interface

The framework provides a **three-tier learning progression** so users can start simple and grow into full control. Learners do NOT need C++ or game development knowledge - all agent logic is written in Python.

### Tier 1: Beginner (SimpleAgentBehavior)
```python
from agent_runtime import SimpleAgentBehavior, SimpleContext

class MyAgent(SimpleAgentBehavior):
    system_prompt = "You are a foraging agent. Collect apples."

    def decide(self, context: SimpleContext) -> str:
        # Just return a tool name - framework infers parameters
        if context.nearby_resources:
            return "move_to"
        return "idle"
```
**Focus**: Understanding the perception → decision → action loop

### Tier 2: Intermediate (AgentBehavior)
```python
from agent_runtime import AgentBehavior, Observation, AgentDecision, ToolSchema
from agent_runtime.memory import SlidingWindowMemory

class MyAgent(AgentBehavior):
    def __init__(self):
        self.memory = SlidingWindowMemory(capacity=50)

    def on_episode_start(self):
        self.memory.clear()

    def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
        self.memory.store(observation)
        if observation.nearby_resources:
            target = observation.nearby_resources[0]
            return AgentDecision(
                tool="move_to",
                params={"target_position": list(target.position)},
                reasoning=f"Moving to {target.name}"
            )
        return AgentDecision.idle()
```
**Focus**: State tracking, explicit parameters, memory patterns

### Tier 3: Advanced (LLMAgentBehavior)
```python
from agent_runtime import LLMAgentBehavior, Observation, AgentDecision, ToolSchema

class MyAgent(LLMAgentBehavior):
    def __init__(self):
        super().__init__(backend="anthropic", model="claude-3-haiku-20240307")
        self.system_prompt = "You are an intelligent foraging agent."

    def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
        context = self._format_observation(observation)
        response = self.complete(context)
        return self._parse_response(response, tools)
```
**Focus**: LLM reasoning, planning, multi-agent coordination

### What Users Control vs Framework Handles

| Aspect | Beginner | Intermediate | Advanced |
|--------|----------|--------------|----------|
| Return Type | Tool name (str) | AgentDecision | AgentDecision |
| Parameters | Framework infers | User specifies | User specifies |
| Memory | Automatic | User manages built-in | User implements custom |
| LLM Integration | Not needed | Optional | Core feature |
| Lifecycle Hooks | Not needed | Optional | Optional |

### Key Classes

- `SimpleAgentBehavior` - Beginner tier (just return tool name)
- `AgentBehavior` - Intermediate tier (full decision control)
- `LLMAgentBehavior` - Advanced tier (LLM integration)
- `SlidingWindowMemory` - Built-in memory for intermediate/advanced

### Example Agents

Located in `python/user_agents/examples/`:
- `SimpleForagerSimple` - Beginner tier example
- `SimpleForager` - Intermediate tier example
- `LLMForager` - Advanced tier example

### Learner Documentation

Complete tutorials at each tier: `docs/learners/`
- `getting_started.md` - Quick start guide
- `beginner/` - 5 tutorials + foraging challenge
- `intermediate/` - 5 tutorials + crafting challenge
- `advanced/` - 6 tutorials + team challenge
- `api_reference/` - Complete API documentation

See `docs/architecture.md` for technical details.

---

## Future Directions

### Near-Term
- Complete initial benchmark scenarios (foraging, crafting_chain, team_capture)
- Build debugging/inspection tools (prompt viewer, step-through mode)
- Create quickstart tutorials for building your first agent

### Medium-Term
- Public leaderboards for scenario benchmarks
- Community scenario sharing
- A/B comparison tools for agent implementations
- Support for visual/multimodal observations (screenshots, rendered views)

### Long-Term
- Curriculum learning system (automatic difficulty progression)
- RL fine-tuning pipeline for agents
- Distributed evaluation for large-scale benchmarking
- Integration with popular agent frameworks (LangChain, AutoGPT patterns)

---

## GitHub Configuration
- **Project Board**: Agent Arena Development Board (Project #3)
- **Project Board ID**: `PVT_kwDODG39W84BHw8k`
- **Issue Labels**:
  - `enhancement`: New feature or request
  - `backend`: LLM backends and inference
  - `tools`: Agent tools
  - `memory`: Memory systems
  - `evals`: Evaluation and benchmarks
  - `critical`: Critical priority
  - `high-priority`: High priority

### GitHub CLI Commands
```bash
# List projects
gh project list --owner JustInternetAI

# View project board
gh project view 3 --owner JustInternetAI

# Create issue (may auto-add to project if automation enabled)
gh issue create --title "Title" --body "Description" --label "enhancement"

# Create issue and add to project
gh issue create --title "Title" --body "Description" --label "enhancement"
gh project item-add 3 --owner JustInternetAI --url https://github.com/JustInternetAI/AgentArena/issues/ISSUE_NUMBER

# Refresh auth with project scopes (if needed)
gh auth refresh -h github.com -s read:project -s project
```

## Tech Stack
- **Godot 4.5**: C++ GDExtension module for simulation
- **Python 3.11**: Agent runtime, LLM backends, tools (3.11 required - many ML packages don't support 3.14 yet)
- **Visual Studio 2022**: C++ compilation (MSVC)
- **CMake 3.20+**: Build system
- **License**: Apache 2.0

## Project Structure
```
c:\Projects\Agent Arena\
├── agent_arena.gdextension  # GDExtension configuration
├── project.godot            # Godot project file
├── godot/                   # C++ GDExtension module
│   ├── src/                 # Core simulation classes
│   ├── include/             # Headers
│   └── build/               # CMake build directory
├── bin/                     # Compiled libraries
│   └── windows/             # Windows DLLs
├── external/                # Third-party dependencies
│   └── godot-cpp/           # Godot C++ bindings (4.5-stable)
├── python/                  # Python agent runtime
│   ├── agent_runtime/       # Core framework (see Agent Interface below)
│   │   ├── behaviors/       # Built-in behavior implementations
│   │   ├── memory/          # Memory system implementations
│   │   └── schemas/         # Shared data contracts
│   ├── user_agents/         # WHERE USERS PUT THEIR CODE
│   ├── backends/            # LLM adapters (llama.cpp, vLLM, etc)
│   ├── tools/               # Agent tools (movement, inventory, etc)
│   └── evals/               # Evaluation harness
├── configs/                 # Hydra configs
├── scenes/                  # Godot benchmark scenes (.tscn files)
├── scripts/                 # GDScript files
│   ├── autoload/            # Global services (IPCService, ToolRegistryService)
│   └── tests/               # Test scripts
├── tests/                   # Python unit tests
└── docs/                    # Documentation
```

## Key Files
- Architecture: `docs/architecture.md`
- Setup guide: `docs/quickstart.md`
- **Learner docs**: `docs/learners/getting_started.md` (start here for tutorials)
- **API reference**: `docs/learners/api_reference/`
- Testing guide: `TESTING.md`
- GitHub setup: `GITHUB_SETUP.md`
- Main config: `configs/config.yaml`
- Project context: `.claude/project-context.md` (this file)

## Current Status
- ✅ Initial framework complete
- ✅ Pushed to GitHub
- ✅ godot-cpp cloned and built (4.5-stable branch)
- ✅ C++ GDExtension module compiled successfully
- ✅ Extension tested and working in Godot 4.5.1
- ✅ Test scene created with working controls
- ✅ Core classes verified: SimulationManager, Agent, EventBus, ToolRegistry
- ✅ IPC system implemented (Godot ↔ Python via HTTP/FastAPI)
- ✅ Python agent runtime framework complete (AgentArena, AgentBehavior, memory systems)
- ✅ **Observation-decision loop integrated** (Issue #30) - Foraging scene fully working with Python agents
- ✅ SimpleForager agent demonstrates complete flow: observations → decisions → execution
- ✅ **Three-tier learning system documented** - Beginner, Intermediate, Advanced tiers with full tutorials
- ✅ **LLMAgentBehavior implemented** - Supports Anthropic, OpenAI, and Ollama backends
- ✅ **Comprehensive learner documentation** - `docs/learners/` with 16+ tutorial files
- ✅ **Example agents for each tier** - SimpleForagerSimple, SimpleForager, LLMForager
- ⏳ Next: Create additional benchmark scenes (crafting_chain, team_capture)
- ⏳ Next: Test LLM integration end-to-end with real API calls

## Development Commands

### Build C++ Module (Windows)
```bash
# Clean build (if needed)
rm -rf godot/build
mkdir godot/build

# Configure with CMake
cd godot/build
"C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe" ..

# Build
"C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe" --build . --config Debug

# Copy DLLs to bin folder (CMake does this automatically)
```

### Run Godot
```bash
# Open project in Godot 4.5+
godot --path "c:\Projects\Agent Arena"

# Or drag project.godot onto Godot executable
```

### Python Setup
```bash
# Setup Python env
cd python
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Run Python tests
cd tests
pytest -v
```

### Run Foraging Demo (Complete Observation-Decision Loop)
```bash
# Start Python IPC server with SimpleForager agent
cd python
venv\Scripts\activate
python run_foraging_demo.py

# You should see:
# ============================================================
# Foraging Demo - SimpleForager Agent
# ============================================================
# Registering SimpleForager agent...
#   ✓ Registered SimpleForager for agent_id: foraging_agent_001
# ✓ IPC Server ready at http://127.0.0.1:5000
# ✓ Waiting for observations from Godot...

# Then in Godot:
# 1. Open scenes/foraging.tscn
# 2. Press F5 to run the scene
# 3. Press SPACE to start the simulation
# 4. Watch the agent collect resources while avoiding hazards!
#
# Controls:
# - SPACE: Start/Stop simulation
# - R: Reset scene
# - S: Step one tick
```

### Run Generic IPC Server (For Custom Agents)
```bash
# Start Python IPC server without pre-registered agents
cd python
venv\Scripts\activate
python run_ipc_server.py

# With custom options
python run_ipc_server.py --host 127.0.0.1 --port 5000 --workers 4 --debug
```

## Common Tasks

### Adding a New Tool
1. Create in `python/tools/your_tool.py`
2. Define function with JSON schema
3. Register in `tools/__init__.py`
4. Add tests in `tests/test_your_tool.py`

### Adding a New Backend
1. Create in `python/backends/your_backend.py`
2. Inherit from `BaseBackend`
3. Implement required methods
4. Add config in `configs/backend/your_backend.yaml`

### Adding to C++ Module
1. Update `godot/include/agent_arena.h`
2. Implement in `godot/src/agent_arena.cpp`
3. If adding new classes, register in `godot/src/register_types.cpp`
4. Rebuild with CMake (see Development Commands)
5. Restart Godot to load new version

## Built C++ Classes

### SimulationManager (Node)
- Deterministic tick-based simulation controller
- Methods: `start_simulation()`, `stop_simulation()`, `step_simulation()`, `reset_simulation()`
- Properties: `current_tick`, `tick_rate`, `is_running`
- Signals: `simulation_started`, `simulation_stopped`, `tick_advanced(tick)`

### Agent (Node)
- Base agent class with perception, memory, and actions
- Methods: `perceive()`, `decide_action()`, `execute_action()`, `call_tool()`
- Memory: `store_memory()`, `retrieve_memory()`, `clear_short_term_memory()`
- Properties: `agent_id`
- Signals: `action_decided`, `perception_received`

### EventBus (RefCounted)
- Event recording and replay system
- Methods: `emit_event()`, `get_events_for_tick()`, `clear_events()`
- Recording: `start_recording()`, `stop_recording()`, `export_recording()`, `load_recording()`

### ToolRegistry (RefCounted)
- Tool management system for agent actions
- Methods: `register_tool()`, `unregister_tool()`, `get_tool_schema()`, `execute_tool()`

### IPCClient (Node)
- HTTP client for Godot ↔ Python communication
- Methods: `connect_to_server()`, `send_tick_request()`, `get_tick_response()`, `has_response()`
- Properties: `server_url`
- Signals: `response_received`, `connection_failed`

## Known Issues
- Only foraging scene is fully implemented (crafting_chain and team_capture need content)
- LLM backends not yet connected to agent decision-making (currently using rule-based SimpleForager)
- Some tools in ToolRegistryService return stub responses (only move_to is fully implemented)

## References
- Godot docs: https://docs.godotengine.org/
- godot-cpp: https://github.com/godotengine/godot-cpp
- llama.cpp: https://github.com/ggerganov/llama.cpp
