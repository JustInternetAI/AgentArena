# Testing the Prompt Inspector with Godot Foraging Scene

This guide walks you through testing the Prompt Inspector with a real Godot foraging simulation to capture and review LLM decision-making data.

## Quick Start (3 Commands)

**1. Start the LLM-powered foraging agent:**
```bash
cd python
venv/Scripts/python run_local_llm_forager.py --model ../models/tinyllama-1.1b-chat/gguf/q4_k_m/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf
```

**2. Run Godot foraging scene:**
- Open Godot Editor → Load `scenes/foraging.tscn` → Press F5 → Press SPACE
- Let it run for 10-15 ticks

**3. View captured data (choose one):**
```bash
# Interactive menu (recommended)
venv/Scripts/python test_inspector_with_godot.py

# Command-line tool
venv/Scripts/python -m tools.inspect_prompts --agent foraging_agent_001 --latest 5

# HTTP API
curl "http://127.0.0.1:5000/inspector/requests?agent_id=foraging_agent_001"
```

---

## Prerequisites

1. **LLM Model**: Download a local model (recommended: tinyllama for quick testing)
2. **Godot**: Have the project ready to run
3. **Python environment**: Virtual environment activated

## Step 1: Download a Model (if not already done)

```bash
cd python
venv/Scripts/python -m tools.model_manager download tinyllama-1.1b-chat --format gguf --quant q4_k_m
```

This downloads a small, fast model (~637MB) suitable for testing.

## Step 2: Start the IPC Server with Prompt Inspector Enabled

The Prompt Inspector is **enabled by default** in LocalLLMBehavior. Start the foraging agent:

```bash
cd python
venv/Scripts/python run_local_llm_forager.py --model ../models/tinyllama-1.1b-chat/gguf/q4_k_m/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf --debug
```

Options:
- `--model`: Path to your GGUF model file
- `--debug`: Enable detailed logging (optional but helpful)
- `--agent-id`: Agent ID (default: `foraging_agent_001`)
- `--temperature`: LLM temperature (default: 0.7)
- `--max-tokens`: Max tokens per response (default: 256)

You should see:
```
INFO - ============================================================
INFO - Local LLM Forager Demo
INFO - ============================================================
INFO - Model: ../models/tinyllama-1.1b-chat/...
INFO - IPC Server ready at http://127.0.0.1:5000
INFO - Press Ctrl+C to stop
INFO - ============================================================
```

## Step 3: Run the Godot Foraging Scene

1. Open Godot Editor
2. Load `scenes/foraging.tscn`
3. Press **F5** to run the scene
4. Press **SPACE** to start the simulation

The agent will:
- Observe nearby resources (apples, wood, stones)
- Observe hazards (fire, pits)
- Make decisions each tick via the LLM
- Execute movement and collection actions

Let it run for **10-20 ticks** to collect enough data for analysis.

## Step 4: View Captured Prompts

### Option A: Using the CLI Tool

View the most recent decision:

```bash
cd python
venv/Scripts/python -m tools.inspect_prompts --agent foraging_agent_001 --latest 1
```

View all decisions:

```bash
venv/Scripts/python -m tools.inspect_prompts --agent foraging_agent_001
```

View a specific tick:

```bash
venv/Scripts/python -m tools.inspect_prompts --agent foraging_agent_001 --tick 5
```

View a range of ticks:

```bash
venv/Scripts/python -m tools.inspect_prompts --agent foraging_agent_001 --tick-range 1-10
```

Export to JSON for analysis:

```bash
venv/Scripts/python -m tools.inspect_prompts --agent foraging_agent_001 --output foraging_decisions.json
```

### Option B: Using the HTTP API

Get all captures for the agent:

```bash
curl "http://127.0.0.1:5000/inspector/requests?agent_id=foraging_agent_001"
```

Get a specific tick:

```bash
curl "http://127.0.0.1:5000/inspector/requests?agent_id=foraging_agent_001&tick=5"
```

Get tick range:

```bash
curl "http://127.0.0.1:5000/inspector/requests?tick_start=1&tick_end=10"
```

Check inspector configuration:

```bash
curl "http://127.0.0.1:5000/inspector/config"
```

### Option C: Programmatic Access

```python
import requests

# Get all captures
response = requests.get("http://127.0.0.1:5000/inspector/requests", params={
    "agent_id": "foraging_agent_001"
})
captures = response.json()

# Analyze prompts
for capture in captures:
    tick = capture["tick"]

    # Find the prompt building stage
    for entry in capture["entries"]:
        if entry["stage"] == "prompt_building":
            print(f"Tick {tick} prompt length: {entry['data']['prompt_length']} chars")
            print(f"Estimated tokens: {entry['data']['estimated_tokens']}")

        # Find the LLM response stage
        if entry["stage"] == "llm_response":
            print(f"Tick {tick} tokens used: {entry['data']['tokens_used']}")
            print(f"Latency: {entry['data']['latency_ms']:.0f}ms")

        # Find the decision stage
        if entry["stage"] == "decision":
            print(f"Tick {tick} decision: {entry['data']['tool']}")
            print(f"Reasoning: {entry['data']['reasoning']}")

    print()
```

## Step 5: Analyze the Captured Data

### What to Look For

#### 1. **Observation Stage** - What the agent saw
```json
{
  "stage": "observation",
  "data": {
    "position": [0.0, 1.0, 0.0],
    "health": 100.0,
    "energy": 100.0,
    "nearby_resources": [
      {
        "name": "Apple",
        "type": "berry",
        "distance": 5.2,
        "position": [5.0, 0.0, 0.0]
      }
    ],
    "nearby_hazards": []
  }
}
```

**Check**: Does the agent have accurate perception data?

#### 2. **Prompt Building Stage** - How the prompt was constructed
```json
{
  "stage": "prompt_building",
  "data": {
    "system_prompt": "You are a foraging agent...",
    "memory_context": {
      "count": 5,
      "items": [...]
    },
    "final_prompt": "Full prompt text...",
    "prompt_length": 1250,
    "estimated_tokens": 312
  }
}
```

**Check**:
- Is the prompt too long? (>2000 tokens might be slow)
- Is memory context useful?
- Is the system prompt clear?

#### 3. **LLM Request Stage** - What was sent to the LLM
```json
{
  "stage": "llm_request",
  "data": {
    "model": "tinyllama-1.1b-chat-v1.0.Q4_K_M",
    "prompt": "...",
    "tools": [
      {"name": "move_to", ...},
      {"name": "pickup", ...},
      {"name": "idle", ...}
    ],
    "temperature": 0.7,
    "max_tokens": 256
  }
}
```

**Check**: Are the right tools available?

#### 4. **LLM Response Stage** - What the LLM returned
```json
{
  "stage": "llm_response",
  "data": {
    "raw_text": "I see an apple at distance 5.2. I should move towards it to collect food.",
    "tokens_used": 45,
    "finish_reason": "stop",
    "metadata": {
      "tool_call": {
        "name": "move_to",
        "arguments": {"target_position": [5.0, 0.0, 0.0], "speed": 1.5}
      }
    },
    "latency_ms": 342
  }
}
```

**Check**:
- Did the LLM respond with valid JSON?
- Is the reasoning sound?
- Is latency acceptable? (<500ms is good)
- Did it use the right number of tokens?

#### 5. **Decision Stage** - The final parsed decision
```json
{
  "stage": "decision",
  "data": {
    "tool": "move_to",
    "params": {
      "target_position": [5.0, 0.0, 0.0],
      "speed": 1.5
    },
    "reasoning": "Moving to collect nearby apple",
    "total_latency_ms": 345
  }
}
```

**Check**: Was the decision executed correctly in Godot?

## Common Issues and Debugging

### Issue 1: No Captures Appearing

**Check if inspector is enabled:**
```bash
curl "http://127.0.0.1:5000/inspector/config"
```

Should return:
```json
{
  "enabled": true,
  "max_entries": 1000,
  "log_to_file": false
}
```

**Solution**: Inspector is enabled by default. If disabled, restart the server.

### Issue 2: Agent Not Making Decisions

**Check agent registration:**
```bash
curl "http://127.0.0.1:5000/agents"
```

Should include `foraging_agent_001`.

**Solution**: Ensure `--agent-id` matches the agent ID in the Godot scene.

### Issue 3: LLM Responses Are Invalid JSON

View the raw LLM response:
```bash
venv/Scripts/python -m tools.inspect_prompts --agent foraging_agent_001 --tick 5
```

Look at the `llm_response` stage → `raw_text` field.

**Solution**: Adjust the system prompt to be more explicit about JSON format.

### Issue 4: Latency Too High (>1000ms)

Check if GPU layers are enabled:
```bash
# Use GPU acceleration
python run_local_llm_forager.py --model ... --gpu-layers -1
```

Check token counts:
```bash
venv/Scripts/python -m tools.inspect_prompts --agent foraging_agent_001 --latest 5
```

**Solution**:
- Reduce `--max-tokens` (try 128)
- Use more GPU layers
- Simplify system prompt
- Use a smaller/faster model

## Performance Analysis Example

Extract performance metrics:

```python
import requests
import statistics

response = requests.get("http://127.0.0.1:5000/inspector/requests", params={
    "agent_id": "foraging_agent_001"
})
captures = response.json()

latencies = []
token_counts = []

for capture in captures:
    for entry in capture["entries"]:
        if entry["stage"] == "llm_response":
            latencies.append(entry["data"]["latency_ms"])
            token_counts.append(entry["data"]["tokens_used"])

print(f"Decisions analyzed: {len(latencies)}")
print(f"Average latency: {statistics.mean(latencies):.1f}ms")
print(f"Min latency: {min(latencies):.1f}ms")
print(f"Max latency: {max(latencies):.1f}ms")
print(f"Average tokens: {statistics.mean(token_counts):.1f}")
```

## Comparing Different Models or Prompts

1. Run simulation with Model A, save data:
   ```bash
   venv/Scripts/python -m tools.inspect_prompts --agent foraging_agent_001 --output model_a.json
   curl -X DELETE "http://127.0.0.1:5000/inspector/requests"  # Clear
   ```

2. Restart with Model B, run simulation:
   ```bash
   python run_local_llm_forager.py --model ../models/model_b.gguf
   ```

3. Save Model B data:
   ```bash
   venv/Scripts/python -m tools.inspect_prompts --agent foraging_agent_001 --output model_b.json
   ```

4. Compare performance:
   ```python
   import json

   with open("model_a.json") as f:
       model_a = json.load(f)

   with open("model_b.json") as f:
       model_b = json.load(f)

   # Compare latencies, token usage, decision quality...
   ```

## File-Based Logging (Optional)

To persist captures across sessions, enable file logging:

```python
# Modify run_local_llm_forager.py to add:
from agent_runtime.prompt_inspector import PromptInspector, set_global_inspector
from pathlib import Path

inspector = PromptInspector(
    enabled=True,
    log_to_file=True,
    log_dir=Path("logs/foraging_inspector")
)
set_global_inspector(inspector)

# Then create behavior as usual
behavior = LocalLLMBehavior(
    backend=backend,
    system_prompt=system_prompt,
    inspector=inspector  # Use custom inspector
)
```

Each decision will be saved to:
```
logs/foraging_inspector/foraging_agent_001_tick_000001.json
logs/foraging_inspector/foraging_agent_001_tick_000002.json
...
```

## Next Steps

- Use captured data to optimize your system prompts
- Compare different models' decision quality
- Analyze latency patterns to improve performance
- Build custom analysis tools using the HTTP API
- Create visualizations of agent decision-making over time

## Related Documentation

- [Prompt Inspector Overview](prompt_inspector.md) - Full API reference
- [LocalLLMBehavior](three_layer_architecture.md#locallllmbehavior) - Agent behavior implementation
- [Foraging Scene](../scenes/foraging.tscn) - Godot scene file
