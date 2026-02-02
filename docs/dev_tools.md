# Development Tools

This document describes the CLI tools available for agent development in Agent Arena. All tools are accessed via the `agent-arena` command.

## Installation

Tools are included with the SDK:

```bash
pip install agent-arena-sdk
```

After installation, the `agent-arena` command is available in your terminal.

## Command Overview

```bash
agent-arena --help
```

```
Usage: agent-arena [OPTIONS] COMMAND [ARGS]...

  Agent Arena development tools.

Commands:
  init       Create a new agent project from a starter template
  run        Start the agent server
  validate   Check agent code structure
  model      Model management (download, list, info)
  debug      Debugging tools (memory, trace, prompts)
  eval       Run evaluation benchmarks
  tools      List available agent tools
  objectives List objective types
  version    Show version information
```

---

## Project Management

### agent-arena init

Create a new agent project from a starter template.

```bash
agent-arena init <starter>
```

**Starters:**
- `beginner` - Simple if/else logic, no memory
- `intermediate` - Memory, planning, state tracking
- `llm` - LLM-powered reasoning

**Examples:**
```bash
# Create beginner project in current directory
agent-arena init beginner

# Create in specific directory
agent-arena init intermediate --output ./my-agent

# Create with custom agent name
agent-arena init llm --name MySmartAgent
```

**Options:**
| Option | Description |
|--------|-------------|
| `--output, -o` | Output directory (default: current) |
| `--name, -n` | Agent class name (default: Agent) |
| `--force, -f` | Overwrite existing files |

**Created files:**
```
my-agent/
├── agent.py          # Agent implementation
├── run.py            # Entry point
├── requirements.txt  # Dependencies
└── README.md         # Instructions
```

For intermediate/llm starters, additional files are created (memory.py, llm_client.py, prompts/).

---

### agent-arena validate

Check agent code structure and common issues.

```bash
agent-arena validate <file>
```

**Examples:**
```bash
agent-arena validate agent.py
agent-arena validate ./my-agent/agent.py
```

**Output:**
```
Validating agent.py...
✓ Found Agent class
✓ decide() method present
✓ Returns Decision type
✓ Observation parameter typed correctly
✓ No syntax errors

Agent is valid!
```

**Checks performed:**
- Agent class exists
- `decide()` method present with correct signature
- Return type is `Decision`
- Import statements correct
- No obvious runtime errors

---

## Running Agents

### agent-arena run

Start the agent IPC server.

```bash
agent-arena run [OPTIONS]
```

**Examples:**
```bash
# Basic run (localhost:5000)
agent-arena run

# Custom port
agent-arena run --port 5001

# Debug mode (verbose logging)
agent-arena run --debug

# Hot reload (auto-restart on file changes)
agent-arena run --hot-reload

# Specify agent file
agent-arena run --agent ./my-agent/agent.py
```

**Options:**
| Option | Description | Default |
|--------|-------------|---------|
| `--host` | Server host | 127.0.0.1 |
| `--port, -p` | Server port | 5000 |
| `--agent, -a` | Path to agent file | agent.py |
| `--debug, -d` | Enable debug logging | False |
| `--hot-reload` | Restart on file changes | False |
| `--workers, -w` | Number of worker processes | 1 |

**Output:**
```
============================================================
Agent Arena - Agent Server
============================================================
Agent: MyAgent (from agent.py)
Server: http://127.0.0.1:5000
Mode: Debug enabled, Hot-reload enabled

✓ Agent loaded successfully
✓ Server started
✓ Waiting for game connection...

Press Ctrl+C to stop
```

---

## Model Management

### agent-arena model list

List available LLM models in the registry.

```bash
agent-arena model list
```

**Output:**
```
Available Models:
─────────────────────────────────────────────────────────────
Name                  Size      Format    Quantization
─────────────────────────────────────────────────────────────
tinyllama-1.1b-chat   637 MB    GGUF      Q4_K_M
phi-2                 1.6 GB    GGUF      Q4_K_M
llama-2-7b-chat       3.8 GB    GGUF      Q4_K_M
mistral-7b-instruct   4.1 GB    GGUF      Q4_K_M
llama-3-8b-instruct   4.7 GB    GGUF      Q4_K_M

Downloaded: tinyllama-1.1b-chat, phi-2
```

### agent-arena model download

Download a model from HuggingFace Hub.

```bash
agent-arena model download <name> [OPTIONS]
```

**Examples:**
```bash
# Download default quantization
agent-arena model download tinyllama-1.1b-chat

# Specific quantization
agent-arena model download llama-2-7b-chat --quant Q5_K_M

# Specific format
agent-arena model download phi-2 --format gguf
```

**Options:**
| Option | Description | Default |
|--------|-------------|---------|
| `--quant, -q` | Quantization level | Q4_K_M |
| `--format, -f` | Model format | gguf |
| `--output, -o` | Download location | ~/.agent-arena/models |

### agent-arena model info

Show details about a model.

```bash
agent-arena model info <name>
```

**Output:**
```
Model: tinyllama-1.1b-chat
─────────────────────────────────────────
Parameters: 1.1B
Architecture: LLaMA
Format: GGUF
Quantization: Q4_K_M
Size: 637 MB
Downloaded: Yes
Path: ~/.agent-arena/models/tinyllama-1.1b-chat-q4_k_m.gguf

Recommended for: Fast inference, testing, development
```

---

## Debugging

### agent-arena debug memory

Inspect agent memory state (requires running agent server).

```bash
agent-arena debug memory [OPTIONS]
```

**Examples:**
```bash
# Show current memory state
agent-arena debug memory

# Show specific agent
agent-arena debug memory --agent agent_001

# Live updates
agent-arena debug memory --follow
```

**Output:**
```
Memory State: agent_001
─────────────────────────────────────────
Type: SlidingWindowMemory
Capacity: 50
Used: 23

Recent observations (last 5):
  Tick 142: pos=(10.5, 0, 5.2) resources=2 hazards=1
  Tick 141: pos=(10.3, 0, 5.1) resources=2 hazards=1
  Tick 140: pos=(10.0, 0, 5.0) resources=3 hazards=1
  Tick 139: pos=(9.8, 0, 4.9) resources=3 hazards=1
  Tick 138: pos=(9.5, 0, 4.8) resources=3 hazards=0

Resources seen: berry_001, berry_002, wood_001
Hazards tracked: fire_001
```

### agent-arena debug trace

Show decision history.

```bash
agent-arena debug trace [OPTIONS]
```

**Examples:**
```bash
# Last 20 decisions
agent-arena debug trace

# Last 50 decisions
agent-arena debug trace --count 50

# Export to file
agent-arena debug trace --output trace.json

# Filter by tool
agent-arena debug trace --tool move_to
```

**Output:**
```
Decision Trace: agent_001
─────────────────────────────────────────
Tick  Tool        Target              Reasoning
─────────────────────────────────────────
142   move_to     (12.0, 0.0, 6.0)   "Moving to nearest berry"
141   move_to     (11.5, 0.0, 5.8)   "Moving to nearest berry"
140   idle        -                   "No resources visible"
139   move_to     (8.0, 0.0, 4.0)    "Escaping fire hazard"
138   move_to     (8.0, 0.0, 4.0)    "Escaping fire hazard"
137   collect     berry_003           "Resource in range"
...
```

### agent-arena debug prompts

Show LLM prompts and responses (LLM agents only).

```bash
agent-arena debug prompts [OPTIONS]
```

**Examples:**
```bash
# Show last prompt/response
agent-arena debug prompts

# Live updates
agent-arena debug prompts --follow

# Show specific tick
agent-arena debug prompts --tick 142
```

**Output:**
```
LLM Interaction: Tick 142
─────────────────────────────────────────
SYSTEM PROMPT:
You are an AI agent in a simulation...

USER PROMPT:
Current observation:
- Position: (10.5, 0.0, 5.2)
- Nearby resources: berry at (12.0, 0.0, 6.0), distance 2.1m
- Nearby hazards: fire at (7.0, 0.0, -3.0), distance 9.8m
- Objective: Collect 10 resources
- Progress: 3/10 collected

What should I do?

RESPONSE:
I can see a berry nearby at distance 2.1m. Since I need to collect
resources and this one is close, I should move toward it.

<tool_use name="move_to">{"target": [12.0, 0.0, 6.0]}</tool_use>

TOKENS: 245 input, 89 output
LATENCY: 340ms
```

### agent-arena debug observe

Stream live observations.

```bash
agent-arena debug observe [OPTIONS]
```

**Examples:**
```bash
# Stream all observations
agent-arena debug observe

# Specific fields only
agent-arena debug observe --fields position,nearby_resources

# JSON output
agent-arena debug observe --format json
```

**Output:**
```
Live Observations: agent_001
─────────────────────────────────────────
[Tick 142] pos=(10.5, 0.0, 5.2) hp=85 resources=2 hazards=1
[Tick 143] pos=(10.7, 0.0, 5.4) hp=85 resources=2 hazards=1
[Tick 144] pos=(10.9, 0.0, 5.6) hp=85 resources=2 hazards=1
[Tick 145] pos=(11.1, 0.0, 5.8) hp=85 resources=2 hazards=1
^C
```

---

## Evaluation

### agent-arena eval

Run evaluation benchmarks.

```bash
agent-arena eval <scenario> [OPTIONS]
```

**Examples:**
```bash
# Run foraging benchmark
agent-arena eval foraging

# Run all scenarios
agent-arena eval --all

# Multiple episodes
agent-arena eval foraging --episodes 100

# Save results
agent-arena eval foraging --output results.json

# Submit to leaderboard
agent-arena eval --all --submit
```

**Options:**
| Option | Description | Default |
|--------|-------------|---------|
| `--episodes, -e` | Number of runs | 10 |
| `--output, -o` | Save results to file | None |
| `--submit` | Submit to leaderboard | False |
| `--all` | Run all scenarios | False |
| `--agent, -a` | Path to agent file | agent.py |

**Output:**
```
Evaluation: foraging
─────────────────────────────────────────
Episodes: 10
Agent: MyAgent

Running... ████████████████████████████████ 10/10

Results:
─────────────────────────────────────────
Metric                  Mean      Std       Best
─────────────────────────────────────────
resources_collected     8.3       1.2       10
health_remaining        67.5      12.3      85
time_taken             287.4      45.2      198

Final Score: 78.4 (±5.2)

Pass Rate: 7/10 (70%)
```

---

## Utilities

### agent-arena tools

List all available agent tools.

```bash
agent-arena tools
```

**Output:**
```
Available Tools:
─────────────────────────────────────────
Tool            Description                     Parameters
─────────────────────────────────────────
move_to         Navigate to position            target_x, target_y, target_z
collect         Pick up nearby resource         target_name
craft           Create item at station          item_name, station_name
query_world     Get detailed surroundings       radius, filter_type
query_inventory Check inventory contents        (none)
send_message    Communicate with agents         message, target_agent
idle            Do nothing this tick            (none)

For detailed documentation, see: docs/universal_tools.md
```

### agent-arena objectives

List objective types and metrics.

```bash
agent-arena objectives
```

**Output:**
```
Objective Metrics:
─────────────────────────────────────────
Metric                Type        Direction
─────────────────────────────────────────
resources_collected   count       higher is better
health_remaining      value       higher is better
time_taken           ticks       lower is better
items_crafted        count       higher is better
team_score           points      higher is better
points_captured      count       higher is better

For detailed documentation, see: docs/objective_schema.md
```

### agent-arena version

Show version information.

```bash
agent-arena version
```

**Output:**
```
Agent Arena SDK: 0.1.0
Compatible Game Versions: 0.1.x
Python: 3.11.5
```

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AGENT_ARENA_HOST` | Default server host | 127.0.0.1 |
| `AGENT_ARENA_PORT` | Default server port | 5000 |
| `AGENT_ARENA_MODELS_DIR` | Model storage directory | ~/.agent-arena/models |
| `AGENT_ARENA_DEBUG` | Enable debug mode | false |
| `ANTHROPIC_API_KEY` | Anthropic API key | (none) |
| `OPENAI_API_KEY` | OpenAI API key | (none) |

### Config File

Create `~/.agent-arena/config.yaml` for persistent settings:

```yaml
server:
  host: 127.0.0.1
  port: 5000

models:
  directory: ~/.agent-arena/models
  default_quant: Q4_K_M

debug:
  enabled: false
  log_level: INFO

eval:
  default_episodes: 10
```

---

## Troubleshooting

### Command not found

```bash
# Ensure SDK is installed
pip install agent-arena-sdk

# Or reinstall
pip install --force-reinstall agent-arena-sdk
```

### Connection refused

```bash
# Make sure agent server is running
agent-arena run

# Check port isn't in use
netstat -an | grep 5000
```

### Model download fails

```bash
# Check internet connection
# Try with verbose logging
agent-arena model download <name> --verbose

# Check HuggingFace is accessible
curl https://huggingface.co
```

---

## References

- [Learner Developer Experience](learner_developer_experience.md) - Overall architecture
- [Objective Schema](objective_schema.md) - Objective format
- [Universal Tools](universal_tools.md) - Tool reference
- [Starters Guide](../starters/README.md) - Starter templates
