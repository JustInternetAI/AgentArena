# Claude Starter — Learn Anthropic Tool Use by Building a Game Agent

This starter teaches you **Anthropic's Claude tool_use API** by building an AI agent that plays Agent Arena scenarios.

## What You'll Learn

- **Tool definitions** — how to describe actions as JSON Schema tools
- **Tool use responses** — how Claude calls tools with typed parameters
- **System prompts** — giving Claude personality, strategy, and constraints
- **Context injection** — formatting game state into effective prompts
- **Error handling** — graceful fallbacks when the LLM doesn't cooperate

## Prerequisites

1. An **Anthropic API key** — get one at [console.anthropic.com](https://console.anthropic.com)
2. Python 3.11+
3. Agent Arena game (Godot) running

## Quick Start

```bash
# 1. Set your API key
export ANTHROPIC_API_KEY=sk-ant-...

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the agent
python run.py

# 4. In Godot: open scenes/foraging.tscn → F5 → SPACE
```

Your agent will start making decisions using Claude!

## Files

| File | What it does |
|------|-------------|
| `agent.py` | `ClaudeAdapter` — formats observations, calls Claude, extracts tool calls |
| `run.py` | Entry point — parses args, creates adapter, starts server |
| `requirements.txt` | Dependencies (agent-arena-sdk, anthropic) |

## How It Works

Each game tick:

```
Godot sends Observation (what the agent sees)
    ↓
ClaudeAdapter.format_observation() → text context
    ↓
Claude reads context + tool definitions
    ↓
Claude calls a tool (e.g., move_to with target_position)
    ↓
ClaudeAdapter extracts tool call → Decision
    ↓
Decision sent back to Godot
```

### The Key Concept: Tool Use

Instead of asking Claude to output JSON (fragile, needs parsing), we define **tools**:

```python
# This is what gets sent to Claude as a tool definition:
{
    "name": "move_to",
    "description": "Navigate to a target position. This ends your turn.",
    "input_schema": {
        "type": "object",
        "properties": {
            "target_position": {
                "type": "array",
                "items": {"type": "number"},
                "description": "Target position as [x, y, z]"
            }
        },
        "required": ["target_position"]
    }
}
```

Claude responds with a structured tool call — no string parsing needed:

```python
# Claude's response contains a tool_use block:
block.type == "tool_use"
block.name == "move_to"
block.input == {"target_position": [10.0, 0.0, 5.0]}
```

## Customization

### Change the System Prompt

Edit `SYSTEM_PROMPT` at the top of `agent.py`. Try:
- Adding personality ("You are a cautious agent that avoids all risk")
- Changing strategy ("Always explore before collecting")
- Adding domain knowledge ("Fire hazards deal 10 damage per tick")

### Change the Model

```bash
python run.py --model claude-haiku-4-5-20251001  # Fastest, cheapest
python run.py --model claude-sonnet-4-20250514   # Balanced (default)
python run.py --model claude-opus-4-20250514     # Most capable
```

### Add Memory

The base adapter is stateless (each tick is independent). Add memory:

```python
class ClaudeAdapterWithMemory(ClaudeAdapter):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.history = []  # Remember past observations

    def decide(self, obs):
        self.history.append(obs)
        # Include recent history in the prompt
        return super().decide(obs)
```

### Override Observation Formatting

```python
class MyAdapter(ClaudeAdapter):
    def format_observation(self, obs):
        # Your custom formatting
        text = super().format_observation(obs)
        text += "\n\nRemembered locations: ..."
        return text
```

## Cost Estimation

Each tick costs approximately:
- **Haiku**: ~0.1 cent (500 input + 100 output tokens)
- **Sonnet**: ~0.5 cent
- **Opus**: ~2.5 cents

A typical foraging run (100 ticks) costs ~$0.10 with Sonnet.

## Debugging

### Enable Debug Viewer

```bash
python run.py --debug
# Open http://127.0.0.1:5000/debug in your browser
```

### View Traces

The adapter records each decision in `self.last_trace` with:
- System prompt sent
- Observation context sent
- Tokens used
- Parse method (tool_use, fallback, error)
- Final decision

### Common Issues

**"Claude did not call a tool"** — Claude sometimes returns text without calling a tool. The adapter falls back to observation-based logic. Try making the system prompt more directive.

**High latency** — Each tick requires an API round-trip. Use Haiku for faster responses, or add caching for repeated observations.

**"ANTHROPIC_API_KEY not set"** — Export your API key: `export ANTHROPIC_API_KEY=sk-ant-...`

## Comparison with LLM Starter

| Feature | LLM Starter | Claude Starter |
|---------|------------|---------------|
| LLM location | Local (llama.cpp) | Cloud (Anthropic API) |
| Output format | JSON text parsing | Native tool_use |
| GPU required | Yes | No |
| Cost | Free (after model download) | Per-token API cost |
| Latency | Low (local) | Medium (network) |
| Model quality | Varies (local models) | High (Claude) |
| Setup | Download model (~4GB) | Set API key |

## Next Steps

- Modify `SYSTEM_PROMPT` to improve decision quality
- Add memory to remember past observations
- Try different models and compare scores
- Read the [Anthropic docs](https://docs.anthropic.com/en/docs/build-with-claude/tool-use) to learn more about tool use
