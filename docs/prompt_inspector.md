# Prompt Inspector - Debugging Tool for LLM Agent Decisions

> **Note (Issue #62):** The inspection system has been consolidated into a unified
> debug system on the SDK server. Enable it with `AgentArena(enable_debug=True)`.
> The old `/inspector/*` endpoints have been replaced by `/debug/*` endpoints,
> and a web-based trace viewer is available at `GET /debug`.
> See the architecture diagram in [prompt_inspector_implementation.md](prompt_inspector_implementation.md).

The Prompt Inspector is a powerful debugging tool that captures and displays exactly what prompts are sent to LLMs and what responses are received. This enables developers to understand and debug agent decision-making in real-time.

## Overview

When an agent makes a decision, the Prompt Inspector captures data at five critical stages:

1. **Observation** - What the agent sees in the environment
2. **Prompt Building** - How observations are converted into LLM prompts
3. **LLM Request** - The exact request sent to the LLM (model, tools, parameters)
4. **LLM Response** - The raw response from the LLM (text, tokens, timing)
5. **Decision** - The final parsed decision (tool, parameters, reasoning)

## Quick Start

### Enable Automatic Capture

By default, the Prompt Inspector is enabled globally and captures all agent decisions automatically:

```python
from agent_runtime.local_llm_behavior import LocalLLMBehavior
from backends import VLLMBackend, BackendConfig

# Create your agent behavior - inspector is enabled by default
config = BackendConfig(model_path="meta-llama/Llama-2-7b-chat-hf")
backend = VLLMBackend(config)
behavior = LocalLLMBehavior(backend=backend)

# All decisions will be automatically captured!
```

### View Captured Prompts

Use the CLI tool to view captured data:

```bash
# View a specific agent decision at tick 42
python -m tools.inspect_prompts --agent agent_001 --tick 42

# View all decisions for an agent in a tick range
python -m tools.inspect_prompts --agent agent_001 --tick-range 40-50

# View the latest 5 decisions for an agent
python -m tools.inspect_prompts --agent agent_001 --latest 5

# Export to JSON for further analysis
python -m tools.inspect_prompts --agent agent_001 --output decisions.json
```

### Retrieve via API

You can also retrieve captures via the SDK server's unified debug endpoints
(requires `AgentArena(enable_debug=True)`):

```bash
# Get a specific capture
curl "http://127.0.0.1:5000/debug/prompts?agent_id=agent_001&tick=42"

# Get all captures for an agent
curl "http://127.0.0.1:5000/debug/prompts?agent_id=agent_001"

# Get captures in a tick range
curl "http://127.0.0.1:5000/debug/prompts?tick_start=40&tick_end=50"

# Get reasoning traces
curl "http://127.0.0.1:5000/debug/traces?agent_id=agent_001&limit=50"

# Get observation tracking data
curl "http://127.0.0.1:5000/debug/observations?agent_id=agent_001"

# List agents with traces
curl "http://127.0.0.1:5000/debug/agents"

# Open the web-based trace viewer
# Navigate to http://127.0.0.1:5000/debug in your browser
```

## Configuration

### Customize Inspector Behavior

Create a custom inspector with specific settings:

```python
from agent_runtime.prompt_inspector import PromptInspector, set_global_inspector
from pathlib import Path

# Create custom inspector with file logging
inspector = PromptInspector(
    enabled=True,              # Enable capture
    max_entries=1000,          # Keep last 1000 captures in memory
    log_to_file=True,          # Write captures to disk
    log_dir=Path("logs/inspector")  # Custom log directory
)

# Set as global inspector
set_global_inspector(inspector)
```

### Disable Inspector

For production or performance-critical scenarios:

```python
from agent_runtime.prompt_inspector import PromptInspector, set_global_inspector

# Disable globally
inspector = PromptInspector(enabled=False)
set_global_inspector(inspector)
```

Or pass a custom inspector to a specific behavior:

```python
# Disable for a specific behavior
inspector = PromptInspector(enabled=False)
behavior = LocalLLMBehavior(backend=backend, inspector=inspector)
```

## Captured Data Structure

Each capture contains entries for all five stages:

### 1. Observation Stage

```json
{
  "timestamp": "2026-01-30T19:38:00Z",
  "agent_id": "agent_001",
  "tick": 42,
  "stage": "observation",
  "data": {
    "agent_id": "agent_001",
    "tick": 42,
    "position": [10.5, 0.0, 5.2],
    "health": 100.0,
    "energy": 95.0,
    "nearby_resources": [
      {
        "name": "Apple",
        "type": "food",
        "distance": 2.5,
        "position": [12.0, 0.0, 6.0]
      }
    ],
    "nearby_hazards": [],
    "inventory": []
  }
}
```

### 2. Prompt Building Stage

```json
{
  "timestamp": "2026-01-30T19:38:00.001Z",
  "agent_id": "agent_001",
  "tick": 42,
  "stage": "prompt_building",
  "data": {
    "system_prompt": "You are an autonomous foraging agent...",
    "memory_context": {
      "count": 5,
      "items": [
        {"tick": 38, "position": [8.0, 0.0, 4.0]},
        {"tick": 39, "position": [9.0, 0.0, 4.5]}
      ]
    },
    "final_prompt": "You are an autonomous foraging agent...\n\n## Current Situation\nPosition: [10.5, 0.0, 5.2]...",
    "prompt_length": 1024,
    "estimated_tokens": 256
  }
}
```

### 3. LLM Request Stage

```json
{
  "timestamp": "2026-01-30T19:38:00.002Z",
  "agent_id": "agent_001",
  "tick": 42,
  "stage": "llm_request",
  "data": {
    "model": "meta-llama/Llama-2-7b-chat-hf",
    "prompt": "Full prompt text...",
    "tools": [
      {
        "name": "move_to",
        "description": "Move to a target position",
        "parameters": {...}
      }
    ],
    "temperature": 0.7,
    "max_tokens": 256
  }
}
```

### 4. LLM Response Stage

```json
{
  "timestamp": "2026-01-30T19:38:00.500Z",
  "agent_id": "agent_001",
  "tick": 42,
  "stage": "llm_response",
  "data": {
    "raw_text": "I see an apple nearby at distance 2.5. I should move to collect it for food.",
    "tokens_used": 45,
    "finish_reason": "stop",
    "metadata": {
      "tool_call": {
        "name": "move_to",
        "arguments": {"target_position": [12.0, 0.0, 6.0]}
      }
    },
    "latency_ms": 498
  }
}
```

### 5. Decision Stage

```json
{
  "timestamp": "2026-01-30T19:38:00.510Z",
  "agent_id": "agent_001",
  "tick": 42,
  "stage": "decision",
  "data": {
    "tool": "move_to",
    "params": {
      "target_position": [12.0, 0.0, 6.0]
    },
    "reasoning": "Moving to collect nearby apple",
    "total_latency_ms": 510
  }
}
```

## Use Cases

### Debugging Agent Behavior

**Problem**: "Why did my agent choose to move away from the resource?"

**Solution**: Use the inspector to see the exact prompt and LLM response:

```bash
python -m tools.inspect_prompts --agent agent_001 --tick 42
```

Examine the observation data, the prompt that was built, and the LLM's reasoning to understand the decision.

### Optimizing Prompts

**Problem**: "Is my system prompt too long? Are observations being truncated?"

**Solution**: Check the prompt building stage to see:
- Final prompt length and estimated tokens
- What context is included from memory
- How observations are formatted

```python
from agent_runtime.prompt_inspector import get_global_inspector

inspector = get_global_inspector()
capture = inspector.get_capture("agent_001", 42)

# Examine prompt building entry
for entry in capture.entries:
    if entry.stage == "prompt_building":
        print(f"Prompt length: {entry.data['prompt_length']} chars")
        print(f"Estimated tokens: {entry.data['estimated_tokens']}")
```

### Monitoring Performance

**Problem**: "Which decisions are taking too long?"

**Solution**: Check the LLM response latency:

```bash
python -m tools.inspect_prompts --agent agent_001 --tick-range 0-100 --output metrics.json
```

Then analyze the `latency_ms` field in each LLM response stage.

### Learning Effective Patterns

**Problem**: "How do successful agents make decisions?"

**Solution**: Study prompts from working agents:

```bash
# Export all decisions from a successful run
python -m tools.inspect_prompts --agent best_agent --output successful_run.json
```

Analyze the successful patterns in prompt construction and reasoning.

## Advanced Usage

### Programmatic Access

```python
from agent_runtime.prompt_inspector import get_global_inspector

inspector = get_global_inspector()

# Get a specific capture
capture = inspector.get_capture("agent_001", 42)

# Get all captures for an agent
captures = inspector.get_captures_for_agent("agent_001", tick_start=40, tick_end=50)

# Iterate through stages
for entry in capture.entries:
    print(f"Stage: {entry.stage}")
    print(f"Timestamp: {entry.timestamp}")
    print(f"Data: {entry.data}")

# Export to JSON
json_str = inspector.to_json(agent_id="agent_001", tick=42)
```

### File-Based Logging

Enable file logging to persist captures across sessions:

```python
from agent_runtime.prompt_inspector import PromptInspector, set_global_inspector
from pathlib import Path

inspector = PromptInspector(
    enabled=True,
    log_to_file=True,
    log_dir=Path("logs/inspector")
)
set_global_inspector(inspector)

# Each decision will be written to:
# logs/inspector/agent_001_tick_000042.json
```

### Custom Analysis

```python
from agent_runtime.prompt_inspector import get_global_inspector

inspector = get_global_inspector()

# Find all decisions that resulted in errors
error_decisions = []
for capture in inspector.get_all_captures():
    for entry in capture.entries:
        if entry.stage == "decision" and "error" in entry.data:
            error_decisions.append(capture)

print(f"Found {len(error_decisions)} error decisions")
```

## API Reference

### PromptInspector Class

#### Constructor

```python
PromptInspector(
    enabled: bool = True,
    max_entries: int = 1000,
    log_to_file: bool = False,
    log_dir: Optional[Path] = None
)
```

#### Methods

- `start_capture(agent_id: str, tick: int) -> Optional[DecisionCapture]`
  - Start capturing a new decision cycle

- `finish_capture(agent_id: str, tick: int) -> None`
  - Finish capturing and optionally write to file

- `get_capture(agent_id: str, tick: int) -> Optional[DecisionCapture]`
  - Get a specific decision capture

- `get_captures_for_agent(agent_id: str, tick_start: Optional[int] = None, tick_end: Optional[int] = None) -> list[DecisionCapture]`
  - Get all captures for a specific agent

- `get_all_captures(tick_start: Optional[int] = None, tick_end: Optional[int] = None) -> list[DecisionCapture]`
  - Get all captures across all agents

- `clear() -> None`
  - Clear all in-memory captures

- `to_json(agent_id: Optional[str] = None, tick: Optional[int] = None) -> str`
  - Export captures as JSON string

### InspectorStage Enum

```python
class InspectorStage(str, Enum):
    OBSERVATION = "observation"
    PROMPT_BUILDING = "prompt_building"
    LLM_REQUEST = "llm_request"
    LLM_RESPONSE = "llm_response"
    DECISION = "decision"
```

## Performance Impact

The Prompt Inspector is designed to have minimal performance impact:

- **When enabled**: ~1-2ms overhead per decision (mostly for data copying)
- **When disabled**: ~0ms overhead (early return in `start_capture()`)
- **Memory usage**: Configurable via `max_entries` (default: 1000 captures)
- **File I/O**: Only when `log_to_file=True`, written asynchronously

For production environments where every millisecond counts, disable the inspector:

```python
inspector = PromptInspector(enabled=False)
set_global_inspector(inspector)
```

## Troubleshooting

### No captures appearing

1. Ensure debug mode is enabled:
   ```python
   arena = AgentArena(enable_debug=True)
   ```

2. Check that the server is running and debug endpoints are active:
   ```bash
   curl "http://127.0.0.1:5000/debug/agents"
   ```

3. Verify the agent is using `LocalLLMBehavior` (inspector only works with LocalLLMBehavior)

4. Check if max_entries limit is too low and old captures are being evicted

### CLI tool not working

1. Ensure the IPC server is running:
   ```bash
   curl "http://127.0.0.1:5000/health"
   ```

2. Install required dependencies:
   ```bash
   pip install requests
   ```

3. Check the correct URL (default: `http://127.0.0.1:5000`)

### File logging not working

1. Check log directory permissions
2. Verify `log_to_file=True` in inspector configuration
3. Check disk space

## Related Documentation

- [LocalLLMBehavior](three_layer_architecture.md#locallllmbehavior) - The behavior class that integrates with the inspector
- [IPC Protocol](ipc_protocol.md) - HTTP endpoints for retrieving inspector data
- [Memory Systems](memory_system.md) - How memory context is included in prompts
- [Prompt Engineering](learners/advanced/02_prompt_engineering.md) - Best practices for crafting effective prompts
- [Implementation Summary](prompt_inspector_implementation.md) - Architecture and consolidated debug system details

## Contributing

Found a bug or have a feature request for the Prompt Inspector? Please open an issue on GitHub with the label `enhancement` or `bug`.
