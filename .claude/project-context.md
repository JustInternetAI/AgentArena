# Agent Arena - Project Context

Quick reference for Claude Code sessions.

## Project Overview
- **Name**: Agent Arena
- **Repo**: https://github.com/JustInternetAI/AgentArena
- **Local Path**: `c:\Projects\Agent Arena`
- **Founders**: Andrew Madison & Justin Madison
- **Organization**: JustInternetAI

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
