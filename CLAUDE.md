# Agent Arena - Project Instructions

## Project Overview
- **Repo**: https://github.com/JustInternetAI/AgentArena
- **Organization**: JustInternetAI
- **License**: Apache 2.0

## Tech Stack
- **Godot 4.5**: C++ GDExtension module for simulation
- **Python 3.11**: Agent runtime, LLM backends, tools (3.11 required — many ML packages don't support 3.14 yet)
- **Visual Studio 2022**: C++ compilation (MSVC)
- **CMake 3.20+**: Build system

## Codebase Search

When exploring or modifying code, **prefer using the `mcp__claude-context__search_code` tool** for semantic search before falling back to Glob/Grep. The codebase is indexed via the Claude Context MCP server and supports natural language queries.

Use semantic search for:
- Understanding how a feature or module works
- Finding implementations related to a concept (e.g., "agent scoring logic", "IPC message handling")
- Locating code relevant to a bug report or feature request
- Discovering patterns and conventions used in the project

Use Glob/Grep when:
- You need an exact string or regex match (e.g., a specific function name, import path)
- You're looking for a file by name/extension

If semantic search returns stale or unexpected results, re-index with `mcp__claude-context__index_codebase`.

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
│   ├── agent_runtime/       # Core framework (behaviors, memory, schemas)
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

## Strategic Direction

**Own the unique, delegate the generic.** See `docs/framework_integration_strategy.md` for full details.

Agent Arena is the **gym** (scenarios, physics, observations, scoring), not the **agent** (LLM calls, prompts, memory, tool calling). Agent infrastructure is commodity code that frameworks like LangGraph, Claude SDK, and OpenAI SDK do better.

**What we own and invest in:**
- SpatialMemory, EpisodeMemory — domain-specific to navigating a 3D world
- Observation schema, game-specific tools (`move_to`, `collect`, `craft_item`)
- MockArena, mock observation factories, eval harness — offline testing without Godot
- FrameworkAdapter ABC — thin integration layer for any agent framework
- Scenario/objective system, scoring, episode lifecycle

**What we delegate to frameworks:**
- LLM API calls, prompt construction, chain-of-thought
- Generic memory (conversation history, RAG)
- Tool calling infrastructure, function schemas
- Observability/tracing (LangSmith, Anthropic Console, etc.)

**When building new features, ask:** "Does any agent framework already provide this?" If yes, don't build it — write a framework starter that teaches users how to use the framework's version instead.

## Agent Architecture (Summary)

Starter templates in `starters/` — all agent logic is Python, no C++/Godot knowledge needed:

- **Beginner** (`starters/beginner/`): No framework — raw `decide()`, priority-based if/else
- **Intermediate** (`starters/intermediate/`): No framework — manual memory + planning
- **Claude** (`starters/claude/`): FrameworkAdapter using Claude native tool_use
- **LLM** (`starters/llm/`): Local model via llama-cpp with custom prompt pipeline (legacy, pre-framework-strategy)

Framework starters (Claude, future LangGraph) are the primary path. The LLM starter exists for local/offline use but its built-in prompt construction and JSON parsing duplicate what frameworks handle natively.

## Key Files
- Architecture: `docs/architecture.md`
- Learner docs: `docs/learners/getting_started.md`
- API reference: `docs/learners/api_reference/`
- Testing guide: `TESTING.md`
- Main config: `configs/config.yaml`
- Project context (vision/design): `.claude/project-context.md`

## Development Commands

### Build C++ Module (Windows)
```bash
# Clean build
rm -rf godot/build && mkdir godot/build

# Configure + Build
cd godot/build
"C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe" ..
"C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe" --build . --config Debug
```

### Python Setup & Tests
```bash
cd python
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Run tests
cd tests
pytest -v
```

### Run Foraging Demo
```bash
cd python
venv\Scripts\activate
python run_foraging_demo.py
# Then in Godot: open scenes/foraging.tscn, F5, SPACE to start
```

### Run IPC Server (Custom Agents)
```bash
cd python
venv\Scripts\activate
python run_ipc_server.py --host 127.0.0.1 --port 5000 --workers 4 --debug
```

## Common Tasks

### Adding a New Tool
1. Create `python/tools/your_tool.py` with JSON schema
2. Register in `tools/__init__.py`
3. Add tests in `tests/test_your_tool.py`

### Adding a New Framework Starter
1. Create `starters/your_framework/` with `agent.py` and `run.py`
2. Implement `FrameworkAdapter` subclass (or standalone `decide()` function)
3. Write tutorial-quality comments explaining framework concepts
4. Add `eval_agent.py` or equivalent for offline evaluation
5. See `starters/claude/` as reference

### Adding to C++ Module
1. Update `godot/include/agent_arena.h`
2. Implement in `godot/src/agent_arena.cpp`
3. Register new classes in `godot/src/register_types.cpp`
4. Rebuild with CMake, restart Godot

## GitHub Configuration
- **Project Board**: Agent Arena Development Board (Project #3)
- **Project Board ID**: `PVT_kwDODG39W84BHw8k`
- **Labels**: `enhancement`, `backend`, `tools`, `memory`, `evals`, `critical`, `high-priority`

```bash
# Useful commands
gh project list --owner JustInternetAI
gh project view 3 --owner JustInternetAI
gh issue create --title "Title" --body "Description" --label "enhancement"
gh project item-add 3 --owner JustInternetAI --url <issue-url>
```

## Known Issues
- Only foraging scene is fully implemented (crafting_chain and team_capture need content)
- Some tools in ToolRegistryService return stub responses (only move_to is fully implemented)
- `starters/llm/` prompt pipeline duplicates what frameworks handle natively — kept for local/offline use but not the recommended path
