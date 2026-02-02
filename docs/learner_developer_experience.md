# Learner Developer Experience (LDX)

This document defines how external developers ("learners") will use Agent Arena to learn agentic AI programming. It covers distribution, SDK design, project structure, and development workflow.

**Last Updated**: Based on architectural discussions emphasizing general-purpose agents, minimal SDK, and starter-based learning.

## Goals

1. **Low Friction Entry**: Learners should start building agents in under 15 minutes
2. **No Game Dev Knowledge Required**: No Godot, C++, or game development experience needed
3. **Standard Python Development**: Familiar Python workflow with pip, venv, and any IDE
4. **Focus on Agent Logic**: Learners write only agent code - everything else is handled
5. **General-Purpose Agents**: Build agents that work across multiple scenarios, not task-specific scripts
6. **Full Visibility**: Learners can see and modify ALL agent code - no hidden "framework magic"

## Target Audience

- **AI/ML Developers** wanting hands-on agent experience
- **Students** learning autonomous agents and LLM applications
- **Researchers** needing reproducible agent benchmarks
- **Hobbyists** experimenting with AI agents

---

## Core Philosophy: General-Purpose Agents

### The Shift

| Old Thinking | New Thinking |
|--------------|--------------|
| "Forager Agent" hard-coded for foraging | "Agent" that receives objectives and achieves them |
| Scenario-specific behavior | Adapts to scenario-provided goals |
| Framework hides complexity | Learners see all the code |
| Tiers = different base classes | Tiers = different starter templates |

### How It Works

1. **Scenarios define objectives** - "Collect 10 resources while staying healthy"
2. **Agents receive objectives** - Via observation data each tick
3. **Agents decide how to achieve them** - Using universal tools
4. **Same agent, multiple scenarios** - Evaluate generalization ability

This teaches real agent development: building systems that can handle novel situations, not task-specific scripts.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                      LEARNER'S MACHINE                              │
│                                                                     │
│  ┌───────────────────────┐        ┌───────────────────────────┐    │
│  │   Agent Arena Game    │        │   Learner's Python        │    │
│  │   (Standalone EXE)    │        │   Environment             │    │
│  │                       │        │                           │    │
│  │  • Godot simulation   │  HTTP  │  • agent-arena-sdk        │    │
│  │  • 3D visualization   │◄──────►│    (minimal IPC layer)    │    │
│  │  • Scenarios          │  JSON  │  • Learner's agent code   │    │
│  │  • Objectives         │        │  • Memory (learner owns)  │    │
│  │  • Debug tools        │        │  • LLM client (if used)   │    │
│  │                       │        │                           │    │
│  └───────────────────────┘        └───────────────────────────┘    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Key insight**: The SDK is a thin IPC layer. All agent logic (memory, reasoning, LLM integration) lives in the learner's code, visible and modifiable.

---

## Distribution Model

### Game Distribution

Agent Arena is distributed as a **standalone executable** - no Godot IDE required.

| Platform | Distribution | File |
|----------|--------------|------|
| Windows | GitHub Releases, itch.io | `AgentArena-Windows.zip` |
| macOS | GitHub Releases, itch.io | `AgentArena-macOS.dmg` |
| Linux | GitHub Releases, itch.io | `AgentArena-Linux.tar.gz` |

**What's Included**:
- All benchmark scenarios (foraging, crafting_chain, team_capture)
- Objective system that passes goals to agents
- Connection UI for agent server
- Debug tools (observation viewer, step mode, decision trace)
- Replay system

**What's NOT Included**:
- Python runtime (learner provides)
- Agent code (learner writes)
- Godot editor (not needed)

### SDK Distribution (Minimal)

```bash
pip install agent-arena-sdk
```

**The SDK is intentionally minimal**. It provides only:

| Component | Purpose |
|-----------|---------|
| `AgentArena` | Connection manager, IPC server |
| `Observation` | Pydantic model for game → agent data |
| `Decision` | Pydantic model for agent → game response |
| `Objective` | Pydantic model for scenario goals |
| `ToolSchema` | Tool definitions |

**What's NOT in the SDK** (lives in starters instead):
- Memory systems
- LLM clients
- Behavior base classes
- Prompt templates
- Planning utilities

This keeps the SDK simple and puts educational code where learners can see it.

### Starter Templates

Starters are complete, self-contained agent implementations that learners copy and modify:

```
starters/
├── beginner/           # Simple if/else logic
├── intermediate/       # Memory, explicit planning
└── llm/                # LLM-powered reasoning
```

Each starter contains ALL the code needed - no hidden framework behavior.

---

## Objective System

Scenarios pass objectives to agents via observations. This enables general-purpose agents.

### Simple Objective Format (v1)

```python
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
    }
}
```

**For beginners**: Check `success_metrics`, pursue obvious goals
**For LLM agents**: Read `description`, understand intent
**For scoring**: Weighted combination of metrics

See `docs/objective_schema.md` for full specification.

---

## Universal Tool Set

The same tools are available in ALL scenarios. Scenarios differ by world content, not APIs.

| Tool | Description | Parameters |
|------|-------------|------------|
| `move_to` | Navigate to position | `target_x`, `target_y`, `target_z` |
| `collect` | Pick up nearby resource | `target_name` |
| `craft` | Combine items at station | `item_name`, `station_name` |
| `query_world` | Get info about surroundings | `radius` |
| `query_inventory` | Check carried items | - |
| `send_message` | Communicate with agents | `message`, `target_agent` |
| `idle` | Do nothing this tick | - |

See `docs/universal_tools.md` for full specification.

---

## Starter Templates

### Beginner Starter

Simple goal-directed behavior with if/else logic. No memory, no LLM.

```
starters/beginner/
├── agent.py              # Decision logic (learner modifies this)
├── run.py                # Entry point
├── requirements.txt      # Just: agent-arena-sdk
└── README.md             # Instructions
```

**agent.py** (simplified):
```python
from agent_arena_sdk import Observation, Decision

class Agent:
    def decide(self, obs: Observation) -> Decision:
        # Check objectives
        objective = obs.objective

        # Escape danger first
        for hazard in obs.nearby_hazards:
            if hazard.distance < 3.0:
                return self.move_away_from(hazard)

        # Work toward goals
        if "resources_collected" in objective.success_metrics:
            return self.pursue_resources(obs)

        return Decision.idle()

    def pursue_resources(self, obs):
        if obs.nearby_resources:
            closest = min(obs.nearby_resources, key=lambda r: r.distance)
            if closest.distance < 2.0:
                return Decision(tool="collect", params={"target_name": closest.name})
            return Decision(tool="move_to", params={"target": closest.position})
        return Decision.idle()
```

### Intermediate Starter

Adds memory and explicit planning. Learner can see and modify memory implementation.

```
starters/intermediate/
├── agent.py              # Decision logic with memory
├── memory.py             # Sliding window memory (visible!)
├── planner.py            # Goal decomposition
├── run.py
├── requirements.txt
└── README.md
```

**memory.py** (learner can see/modify):
```python
class SlidingWindowMemory:
    def __init__(self, capacity=50):
        self.capacity = capacity
        self.observations = []

    def store(self, observation):
        self.observations.append(observation)
        if len(self.observations) > self.capacity:
            self.observations.pop(0)

    def get_recent(self, n=10):
        return self.observations[-n:]

    def search(self, predicate):
        return [obs for obs in self.observations if predicate(obs)]
```

### LLM Starter

Full LLM integration with prompt engineering. Learner controls everything.

```
starters/llm/
├── agent.py              # LLM-powered decisions
├── memory.py             # Semantic memory with embeddings
├── llm_client.py         # API wrapper (visible!)
├── prompts/
│   ├── system.txt        # System prompt
│   └── decision.txt      # Decision prompt template
├── run.py
├── requirements.txt      # + anthropic/openai
└── README.md
```

**llm_client.py** (learner can see/modify):
```python
import anthropic

class LLMClient:
    def __init__(self, model="claude-3-haiku-20240307"):
        self.client = anthropic.Anthropic()
        self.model = model

    def complete(self, system_prompt, user_prompt, tools=None):
        messages = [{"role": "user", "content": user_prompt}]

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system_prompt,
            messages=messages,
            tools=tools
        )

        return response
```

See `starters/README.md` for detailed usage instructions.

---

## Learner Project Structure

### Minimal Project (from beginner starter)

```
my-agent/
├── agent.py              # Copied from starter, modified
├── run.py                # Entry point
└── requirements.txt      # agent-arena-sdk
```

### Growing Project (from intermediate starter)

```
my-agent/
├── agent.py
├── memory.py             # Copied from starter, customized
├── planner.py            # Added planning logic
├── strategies/           # Learner's own additions
│   ├── foraging.py
│   └── crafting.py
├── run.py
├── requirements.txt
└── README.md
```

### Advanced Project (from llm starter)

```
my-llm-agent/
├── agent.py
├── memory.py
├── llm_client.py
├── prompts/
│   ├── system.txt
│   ├── decision.txt
│   └── reflection.txt    # Learner added
├── evals/
│   └── benchmark.py      # Custom evaluation
├── .env                  # API keys (gitignored)
├── run.py
├── requirements.txt
└── README.md
```

---

## Development Workflow

### Getting Started (First Time)

```bash
# 1. Download game from GitHub releases
# Extract to C:\Games\AgentArena (or wherever)

# 2. Create project folder
mkdir my-agent && cd my-agent

# 3. Setup Python environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# 4. Install SDK
pip install agent-arena-sdk

# 5. Copy a starter template
agent-arena init beginner    # or: intermediate, llm

# 6. Start your agent server
python run.py

# 7. Launch game, connect, run scenario
```

### Daily Development

```bash
# Terminal 1: Run agent
cd my-agent && venv\Scripts\activate
python run.py --debug

# Terminal 2 (or IDE): Edit agent.py
# Save changes

# In game: Press R to reset, test changes
```

### Debugging

```bash
# Verbose agent logging
python run.py --debug

# Memory inspection
agent-arena debug memory

# Decision trace
agent-arena debug trace

# LLM prompt/response inspection
agent-arena debug prompts
```

In-game debug tools:
- `D` - Toggle debug overlay (observations, decisions, objective progress)
- `P` - Pause/step through ticks
- `T` - Decision trace window
- `L` - LLM inspector (prompts, responses, tokens)

---

## CLI Tools

All tools under unified `agent-arena` command:

### Project Management

```bash
agent-arena init beginner       # Create from beginner starter
agent-arena init intermediate   # Create from intermediate starter
agent-arena init llm            # Create from LLM starter
agent-arena validate agent.py   # Check agent structure
```

### Running

```bash
agent-arena run                 # Start agent server (localhost:5000)
agent-arena run --debug         # Verbose logging
agent-arena run --port 5001     # Custom port
agent-arena run --hot-reload    # Auto-reload on file changes
```

### Model Management

```bash
agent-arena model list          # List available models
agent-arena model download <n>  # Download from HuggingFace
agent-arena model info <name>   # Show model details
```

### Debugging

```bash
agent-arena debug memory        # Inspect memory state
agent-arena debug trace         # Decision history
agent-arena debug prompts       # LLM prompts/responses
agent-arena debug observe       # Live observation stream
```

### Evaluation

```bash
agent-arena eval foraging       # Run foraging benchmark
agent-arena eval crafting       # Run crafting benchmark
agent-arena eval --all          # Run all scenarios
agent-arena eval --episodes 100 # Multiple runs for statistics
```

### Utilities

```bash
agent-arena tools               # List all available tools
agent-arena objectives          # List objective types
```

See `docs/dev_tools.md` for full CLI reference.

---

## Leaderboards

Two types of leaderboards teach different lessons:

### Per-Scenario Leaderboards

```
FORAGING LEADERBOARD
────────────────────────────────────────
1. speed-demon        Score: 94.2  (Rule-based)
2. adaptive-v2        Score: 91.8  (LLM)
3. memory-master      Score: 89.1  (Intermediate)
```

**Lesson**: Specialized agents can excel at specific tasks.

### Aggregate Leaderboard

```
GENERALIST RANKING (All Scenarios)
────────────────────────────────────────
1. adaptive-v2        Avg: 83.2  (3 scenarios)
2. balanced-agent     Avg: 78.5  (3 scenarios)
3. speed-demon        Avg: 62.1  (3 scenarios)  ← Great at foraging, bad at crafting
```

**Lesson**: Generalization is hard. What tradeoffs exist between adaptability and specificity?

### Submitting Scores

```bash
agent-arena eval --all --submit    # Run benchmarks and submit
```

Requires GitHub authentication. Scores linked to your GitHub profile.

---

## Repo Structure

```
JustInternetAI/AgentArena (main repo)
├── godot/                  # C++ GDExtension
├── scenes/                 # Godot scenarios
├── scripts/                # GDScript
├── python/
│   ├── framework/          # IPC server, core protocol
│   ├── tools/              # CLI dev tools
│   └── evals/              # Evaluation harness
├── starters/               # Reference implementations
│   ├── beginner/           # Simple if/else
│   ├── intermediate/       # Memory + planning
│   └── llm/                # LLM-powered
├── examples/               # Scenario-specific tips
│   ├── foraging/
│   ├── crafting/
│   └── team/
└── docs/
    ├── learner_developer_experience.md  (this file)
    ├── objective_schema.md
    ├── universal_tools.md
    ├── dev_tools.md
    └── learners/           # Tutorials
```

**agent-arena-sdk** (published to PyPI):
- Minimal package: Observation, Decision, Objective, AgentArena, ToolSchema
- Does NOT include: memory, LLM clients, behavior classes

**Learner's repo** (their own):
- Copies from starters/
- Installs SDK via pip
- Full ownership of all agent code

---

## Version Compatibility

| SDK Version | Game Version | Notes |
|-------------|--------------|-------|
| 0.1.x | 0.1.x | Initial release |
| 0.2.x | 0.2.x | Breaking: New observation format |

The SDK and game version together. Game displays required SDK version on startup.

---

## Security Considerations

- **Local only by default**: IPC server binds to localhost
- **No remote execution**: Game cannot run arbitrary code
- **API keys**: Learners manage via `.env` (gitignored)
- **No telemetry**: No data collection without consent
- **Leaderboard**: Only scores submitted, not agent code

---

## Migration Path

### From Old Three-Tier System

If you have agents using the old `SimpleAgentBehavior` / `AgentBehavior` / `LLMAgentBehavior` base classes:

1. Choose appropriate starter (beginner/intermediate/llm)
2. Copy your decision logic into the new structure
3. Replace framework memory with starter's memory.py
4. Replace framework LLM calls with starter's llm_client.py

The logic is the same - it's just now in YOUR code, not hidden in the framework.

---

## Roadmap

### Phase 1: MVP
- [ ] Minimal SDK package (#50)
- [ ] Windows game build (#51)
- [ ] Beginner starter
- [ ] Basic debug overlay
- [ ] Foraging scenario with objectives

### Phase 2: Full Release
- [ ] All platform builds
- [ ] All three starters
- [ ] All three scenarios
- [ ] CLI tools (#52)
- [ ] Hot-reload (#54)
- [ ] Advanced debug tools (#55)

### Phase 3: Community
- [ ] Per-scenario leaderboards
- [ ] Aggregate leaderboard
- [ ] itch.io distribution
- [ ] Community scenario sharing

---

## Related Documents

- [Objective Schema](objective_schema.md) - How scenarios define goals
- [Universal Tools](universal_tools.md) - Complete tool reference
- [Starters Guide](../starters/README.md) - Using starter templates
- [Dev Tools](dev_tools.md) - CLI tool reference
- [IPC Protocol](ipc_protocol.md) - Technical protocol specification

---

## Appendix: Why Minimal SDK?

**Question**: Why not include memory systems and LLM clients in the SDK?

**Answer**: Education.

When memory is in the SDK:
```python
from agent_arena_sdk import SlidingWindowMemory  # Magic box
self.memory = SlidingWindowMemory(50)            # How does it work? 🤷
```

When memory is in your code:
```python
from memory import SlidingWindowMemory           # YOUR file
# You can open memory.py and see exactly how it works
# You can modify it, experiment, learn
```

The starters give you working implementations. But they're YOUR code now. No magic, no hidden behavior, full understanding.

This is the difference between "using a framework" and "learning how agents work."
