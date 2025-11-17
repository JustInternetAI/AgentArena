# Agent Arena - Project Context

Quick reference for Claude Code sessions.

## Project Overview
- **Name**: Agent Arena
- **Repo**: https://github.com/JustInternetAI/AgentArena
- **Local Path**: `c:\Projects\Agent Arena`
- **Founders**: Andrew Madison & Justin Madison
- **Organization**: JustInternetAI

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
│   ├── src/                 # Core simulation classes (agent_arena.cpp, register_types.cpp)
│   ├── include/             # Headers (agent_arena.h, register_types.h)
│   └── build/               # CMake build directory
├── bin/                     # Compiled libraries
│   └── windows/             # Windows DLLs
├── external/                # Third-party dependencies
│   └── godot-cpp/           # Godot C++ bindings (4.5-stable)
├── python/                  # Python agent runtime
│   ├── agent_runtime/       # Agent logic
│   ├── backends/            # LLM adapters (llama.cpp, vLLM, etc)
│   ├── tools/               # Agent tools (movement, inventory, etc)
│   ├── memory/              # Memory systems (RAG, episodes)
│   └── evals/               # Evaluation harness
├── configs/                 # Hydra configs
├── scenes/                  # Godot benchmark scenes (.tscn files)
├── scripts/                 # GDScript files
│   ├── tests/               # Test scripts (test_extension.gd, ipc_test.gd)
│   └── test_arena.gd        # Main test arena script
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
- ✅ Benchmark scenes created (foraging, crafting_chain, team_capture)
- ✅ Tool execution system connected (Agent → ToolRegistry → IPC → Python)
- ✅ Benchmark scenes integrated with tool execution system

### Active Work Items
- 🔄 **Andrew**: LLM backend integration with agent decision-making
- ✅ **Justin** (Issue #15): Build out benchmark scenes with game content - **COMPLETE**
- ✅ **Justin** (Issue #16): Connect tool execution system in Godot - **COMPLETE**

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
- Methods: `connect_to_server()`, `send_tick_request()`, `get_tick_response()`, `has_response()`, `execute_tool_sync()`
- Properties: `server_url`
- Signals: `response_received`, `connection_failed`

## Tool Execution System

The tool execution system enables agents to perform actions in the simulation by calling Python tool functions.

### Architecture
```
Agent.call_tool() → ToolRegistry.execute_tool() → IPCClient.execute_tool_sync() →
Python IPC Server (/tools/execute) → ToolDispatcher.execute_tool() → Tool Function
```

### Available Tools
- **Movement**: `move_to`, `navigate_to`, `stop_movement`, `rotate_to_face`
- **Inventory**: `pickup_item`, `drop_item`, `use_item`, `get_inventory`, `craft_item`
- **World Query**: (defined in `python/tools/world_query.py`)

### Usage Example (GDScript)
```gdscript
# Setup
var agent = Agent.new()
var tool_registry = ToolRegistry.new()
var ipc_client = IPCClient.new()

tool_registry.set_ipc_client(ipc_client)
agent.set_tool_registry(tool_registry)

# Execute tool
var result = agent.call_tool("move_to", {
    "target_position": [10.0, 0.0, 5.0],
    "speed": 1.5
})

if result["success"]:
    print("Tool executed successfully: ", result["result"])
else:
    print("Tool failed: ", result["error"])
```

### Testing
- Test scenes: `scenes/tests/test_tool_execution_simple.tscn` (recommended), `scenes/tests/test_tool_execution.tscn`
- Test scripts: `scripts/tests/test_tool_execution_simple.gd`, `scripts/tests/test_tool_execution.gd`
- Test README: `scenes/tests/README.md`
- Documentation: `TESTING_TOOL_EXECUTION.md`, `TOOL_TESTING_FIXED.md`

## Known Issues
- Python environment needs initial setup (venv + pip install)

## Recent Issues
- Issue #15: Build out benchmark scenes with game content (assigned to Justin) - ✅ **COMPLETE**
  - Connected all three benchmark scenes to tool execution system
  - Foraging scene: Resource collection with hazard avoidance
  - Crafting chain scene: Multi-step crafting recipes
  - Team capture scene: Multi-agent team competition
  - All scenes ready for LLM-driven agents
- Issue #16: Connect tool execution system in Godot (assigned to Justin) - ✅ **COMPLETE**
  - See: `TESTING_TOOL_EXECUTION.md`, `TOOL_TESTING_FIXED.md` for details
  - Test scenes: `scenes/tests/` (use `test_tool_execution_simple.tscn` for quick verification)
- LLM backend integration (assigned to Andrew) - In Progress

## References
- Godot docs: https://docs.godotengine.org/
- godot-cpp: https://github.com/godotengine/godot-cpp
- llama.cpp: https://github.com/ggerganov/llama.cpp
