# Prompt Inspector Demo

This demo script showcases the Prompt Inspector functionality implemented for issue #31.

## Running the Demo

```bash
cd python
venv/Scripts/python test_prompt_inspector_demo.py
```

## What It Does

The demo script:
1. Creates a mock LLM backend that simulates agent decisions
2. Configures the Prompt Inspector with file logging enabled
3. Runs 4 simulated decision cycles with different scenarios:
   - Tick 1: Agent sees an apple nearby
   - Tick 2: Agent picks up the apple
   - Tick 3: Agent encounters a fire hazard
   - Tick 4: Agent waits in a safe area
4. Captures all 5 stages of each decision:
   - **Observation**: What the agent sees
   - **Prompt Building**: How the prompt is constructed
   - **LLM Request**: What is sent to the LLM
   - **LLM Response**: What the LLM returns
   - **Decision**: The final parsed action
5. Displays captured data in various formats
6. Writes JSON log files to `logs/inspector_demo/`

## Output

The script generates:
- Console output showing the decision pipeline
- 4 JSON files (one per tick) in `logs/inspector_demo/`
- Examples of filtering and accessing specific stages

## Viewing the Data

After running the demo, you can:

1. **View the JSON files directly:**
   ```bash
   cat logs/inspector_demo/demo_agent_tick_000001.json
   ```

2. **Use the CLI tool** (requires IPC server running):
   ```bash
   python -m tools.inspect_prompts --agent demo_agent
   ```

3. **Programmatically access the data:**
   ```python
   from agent_runtime.prompt_inspector import get_global_inspector

   inspector = get_global_inspector()
   capture = inspector.get_capture("demo_agent", 1)

   for entry in capture.entries:
       print(f"{entry.stage}: {entry.data}")
   ```

## Understanding the Output

Each captured decision includes:

### Observation Stage
```json
{
  "agent_id": "demo_agent",
  "tick": 1,
  "position": [0.0, 0.0, 0.0],
  "health": 100.0,
  "nearby_resources": [...]
}
```

### Prompt Building Stage
```json
{
  "system_prompt": "You are a foraging agent...",
  "memory_context": {...},
  "final_prompt": "Full prompt text...",
  "prompt_length": 408,
  "estimated_tokens": 102
}
```

### LLM Request Stage
```json
{
  "model": "demo-llm-v1",
  "prompt": "...",
  "tools": [...],
  "temperature": 0.7
}
```

### LLM Response Stage
```json
{
  "raw_text": "I see an apple nearby...",
  "tokens_used": 50,
  "finish_reason": "stop",
  "latency_ms": 0.0
}
```

### Decision Stage
```json
{
  "tool": "move_to",
  "params": {"target_position": [5.0, 0.0, 0.0]},
  "reasoning": "I see an apple nearby...",
  "total_latency_ms": 0.0
}
```

## Next Steps

- Read the full documentation: [docs/prompt_inspector.md](../docs/prompt_inspector.md)
- Integrate with your own simulation
- Use the inspector to debug agent behavior
- Analyze prompts to optimize agent performance
