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

## Agent Interface Architecture

The framework provides a **layered interface** so users can start simple and grow into full control.

### Layer 1: Simple (Beginners)
```python
class MyAgent(SimpleAgentBehavior):
    system_prompt = "You are a foraging agent. Collect apples."

    def decide(self, context: SimpleContext) -> str:
        # Just return a tool name - framework handles the rest
        if context.nearby_resources:
            return "move_to"
        return "idle"
```

### Layer 2: Intermediate (LLM Integration)
```python
class MyAgent(AgentBehavior):
    def __init__(self, backend):
        self.backend = backend
        self.memory = SlidingWindowMemory(capacity=10)  # Use built-in memory
        self.system_prompt = "You are a foraging agent..."

    def decide(self, observation, tools) -> AgentDecision:
        self.memory.store(observation)
        prompt = self.build_prompt(observation)
        response = self.backend.generate_with_tools(prompt, tools)
        return AgentDecision.from_response(response)
```

### Layer 3: Advanced (Full Control)
```python
class MyAgent(AgentBehavior):
    def __init__(self, backend):
        self.backend = backend
        self.memory = MyCustomRAGMemory()  # Custom memory implementation
        self.planner = HierarchicalPlanner()

    def decide(self, observation, tools) -> AgentDecision:
        # Full control over memory, prompts, planning, everything
        ...
```

### What Users Control vs Framework Handles

| Aspect | Simple | Intermediate | Advanced |
|--------|--------|--------------|----------|
| System Prompt | Class attribute | User writes | User writes |
| Memory | Framework default | Choose built-in | Implement custom |
| Prompt Building | Framework | User customizes | User implements |
| Response Parsing | Framework | Framework helpers | User implements |
| Custom State | Not available | Basic dict | Full control |

### Key Interfaces

- `AgentBehavior` - Abstract base class users implement
- `AgentMemory` - Interface for memory systems (swappable)
- `AgentDecision` - What the agent returns (tool + params + reasoning)
- `Observation` - What the agent receives from Godot

See `docs/architecture.md` for full details.

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
- ⏳ Next: Create actual benchmark scenes (foraging, crafting_chain, team_capture)
- ⏳ Next: Set up Python environment and agent runtime
- ⏳ Next: Integrate LLM backends with agent decision-making

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

### Run IPC Server (Godot ↔ Python Communication)
```bash
# Start Python IPC server
cd python
venv\Scripts\activate
python run_ipc_server.py

# With custom options
python run_ipc_server.py --host 127.0.0.1 --port 5000 --workers 4 --debug

# Test IPC in Godot
# Open scenes/ipc_test.gd in Godot editor and run it
```

### Run IPC Server (Godot ↔ Python Communication)
```bash
# Start Python IPC server
cd python
venv\Scripts\activate
python run_ipc_server.py

# With custom options
python run_ipc_server.py --host 127.0.0.1 --port 5000 --workers 4 --debug

# Test IPC in Godot
# Open scenes/ipc_test.gd in Godot editor and run it
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
- Benchmark scenes are empty placeholders (need to create actual game worlds)
- Python environment needs initial setup (venv + pip install)
- LLM backends not yet connected to agent decision-making
- Tool execution in Godot currently returns stub responses

## References
- Godot docs: https://docs.godotengine.org/
- godot-cpp: https://github.com/godotengine/godot-cpp
- llama.cpp: https://github.com/ggerganov/llama.cpp
