# Agent Arena - Project Context

Quick reference for Claude Code sessions.

## Project Overview
- **Name**: Agent Arena
- **Repo**: https://github.com/JustInternetAI/AgentArena
- **Local Path**: `c:\Projects\Agent Arena`
- **Founders**: Andrew Madison & Justin Madison
- **Organization**: JustInternetAI

## Tech Stack
- **Godot 4**: C++ GDExtension module for simulation
- **Python 3.11+**: Agent runtime, LLM backends, tools
- **License**: Apache 2.0

## Project Structure
```
c:\Projects\Agent Arena\
├── godot/              # C++ GDExtension module
│   ├── src/           # Core simulation classes
│   └── include/       # Headers
├── python/            # Python agent runtime
│   ├── agent_runtime/ # Agent logic
│   ├── backends/      # LLM adapters (llama.cpp, vLLM, etc)
│   ├── tools/         # Agent tools (movement, inventory, etc)
│   ├── memory/        # Memory systems (RAG, episodes)
│   └── evals/         # Evaluation harness
├── configs/           # Hydra configs
├── scenes/            # Godot benchmark scenes
├── tests/             # Python unit tests
└── docs/              # Documentation
```

## Key Files
- Architecture: `docs/architecture.md`
- Setup guide: `docs/quickstart.md`
- GitHub setup: `GITHUB_SETUP.md`
- Main config: `configs/config.yaml`

## Current Status
- ✅ Initial framework complete
- ✅ Pushed to GitHub
- ⏳ Next: Build godot-cpp and compile C++ module
- ⏳ Next: Implement IPC between Godot and Python
- ⏳ Next: Create first benchmark scene

## Development Commands
```bash
# Build C++ module
cd godot/build
cmake ..
cmake --build .

# Run Python tests
cd tests
pytest -v

# Setup Python env
cd python
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
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
3. Rebuild with CMake

## Known Issues
- Need to clone godot-cpp before building
- IPC layer not yet implemented
- No Godot scenes created yet

## References
- Godot docs: https://docs.godotengine.org/
- godot-cpp: https://github.com/godotengine/godot-cpp
- llama.cpp: https://github.com/ggerganov/llama.cpp
