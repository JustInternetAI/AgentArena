# Foraging Demo Guide

This guide explains how to run the foraging benchmark scene with the SimpleForager agent, demonstrating the complete observation-decision loop integration.

## Overview

The foraging demo showcases the full integration between Godot and Python agents:

1. **Godot Scene** sends observations (nearby resources, hazards, agent state)
2. **Python Agent** (SimpleForager) makes decisions based on observations
3. **Godot** executes the agent's decisions (movement, collection)
4. **Metrics** are tracked (resources collected, damage taken, distance traveled)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Godot (foraging.tscn)                    │
│                                                             │
│  ┌──────────────┐         ┌─────────────────┐             │
│  │ SceneController│────────│  SimpleAgent    │             │
│  │  (foraging.gd) │        │ (simple_agent.gd)│             │
│  └────────┬───────┘        └────────┬────────┘             │
│           │                         │                       │
│           │ Observations            │ Tool Execution        │
│           │                         │                       │
└───────────┼─────────────────────────┼───────────────────────┘
            │                         │
            │ HTTP POST /observe      │ HTTP POST /tool
            │                         │
┌───────────▼─────────────────────────▼───────────────────────┐
│                    IPC Server (Python)                      │
│                                                             │
│  ┌──────────────┐         ┌─────────────────┐             │
│  │  IPCServer   │────────│   AgentArena     │             │
│  │              │        │                  │             │
│  └──────┬───────┘        └────────┬────────┘             │
│         │                         │                       │
│         │                         │                       │
│  ┌──────▼──────────────────────┐ │                       │
│  │  Registered Behaviors Dict  │ │                       │
│  │  {"foraging_agent_001":     │ │                       │
│  │   SimpleForager instance}   │◄┘                       │
│  └─────────────────────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

There are two ways to run the foraging demo:
1. **Rule-based agent** (SimpleForager) - No model download required
2. **LLM-powered agent** - Requires downloading a GGUF model

---

### Option A: Rule-Based Agent (Quick Test)

This uses the SimpleForager agent which makes decisions using simple rules (no LLM).

```bash
cd python
.\venv\Scripts\activate   # Windows
# source venv/bin/activate  # Linux/Mac
python run_foraging_demo.py
```

---

### Option B: LLM-Powered Agent (GPU Required)

This uses a local LLM via llama.cpp for decision-making.

#### Step 1: Download a Model

First, download a GGUF model using the built-in model manager:

```bash
cd python
.\venv\Scripts\activate

# Small model for testing (~700MB) - recommended for first test
python -m tools.model_manager download tinyllama-1.1b-chat --format gguf --quant q4_k_m

# Or a more capable model (~4GB)
python -m tools.model_manager download phi-2 --format gguf --quant q4_k_m

# Or a production-quality model (~4GB)
python -m tools.model_manager download llama-2-7b-chat --format gguf --quant q4_k_m
```

To see all available models:
```bash
python -m tools.model_manager info
```

To list downloaded models:
```bash
python -m tools.model_manager list
```

#### Step 2: Run with LocalLLMBehavior

Use `run_local_llm_forager.py` which integrates the LLM with the agent behavior system:

```bash
# Using TinyLlama (fastest, basic quality)
python run_local_llm_forager.py --model ../models/tinyllama-1.1b-chat/gguf/q4_k_m/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf --gpu-layers -1

# Using Phi-2 (good balance)
python run_local_llm_forager.py --model ../models/phi-2/gguf/q4_k_m/phi-2.Q4_K_M.gguf --gpu-layers -1

# Using Llama-2-7B (production quality)
python run_local_llm_forager.py --model ../models/llama-2-7b-chat/gguf/q4_k_m/llama-2-7b-chat.Q4_K_M.gguf --gpu-layers -1
```

**Options:**
- `--gpu-layers -1`: Offload all layers to GPU (fastest)
- `--gpu-layers 0`: CPU only (no GPU required)
- `--gpu-layers 20`: Offload 20 layers to GPU (partial)
- `--temperature`: LLM temperature (default: 0.7)
- `--max-tokens`: Maximum tokens per response (default: 256)
- `--debug`: Enable debug logging

The LocalLLMBehavior class bridges the LlamaCppBackend with the AgentBehavior interface, providing real LLM-powered decision making.

---

### Expected Output (Rule-Based Demo)

You should see:
```
============================================================
Foraging Demo - SimpleForager Agent
============================================================

1. This script will start the IPC server
2. Open Godot and load scenes/foraging.tscn
3. Press SPACE in Godot to start the simulation
4. Watch the agent collect resources!

============================================================
Registering SimpleForager agent...
  ✓ Registered SimpleForager for agent_id: foraging_agent_001
Total registered agents: 1

✓ IPC Server ready at http://127.0.0.1:5000
✓ Waiting for observations from Godot...
```

### 2. Run the Godot Scene

1. Open Godot Engine
2. Load the project at `c:\Projects\Agent Arena`
3. Open [scenes/foraging.tscn](scenes/foraging.tscn)
4. Press **F5** to run the scene (or click the play button)

### 3. Start the Simulation

In the Godot window:
- Press **SPACE** to start/stop the simulation
- Press **R** to reset the scene
- Press **S** to step one tick at a time

### 4. Watch the Agent Work

The agent will:
- Scan for nearby resources (apples, wood, stone)
- Avoid hazards (fire pits)
- Move toward the nearest safe resource
- Collect resources when within range
- Complete when 7/7 resources are collected

## What Was Implemented

### Issue #30: Observation-Decision Loop Integration

**Files Modified:**

1. **[python/ipc/server.py](python/ipc/server.py:397-495)** - Updated `/observe` endpoint
   - Checks for registered behaviors instead of always using mock logic
   - Converts Godot observations to Python `Observation` schema
   - Calls `behavior.decide()` for registered agents
   - Falls back to mock logic for unregistered agents

2. **[python/run_foraging_demo.py](python/run_foraging_demo.py)** - New demo script
   - Creates AgentArena instance
   - Registers SimpleForager for `foraging_agent_001`
   - Starts IPC server and waits for Godot connections

3. **[scripts/simple_agent.gd](scripts/simple_agent.gd:130-151)** - Added movement implementation
   - Added `_process(delta)` for frame-based movement
   - Intercepts `move_to` tool calls to update position
   - Uses linear interpolation toward target position
   - Configurable movement speed via `@export var move_speed: float = 5.0`

### Key Bugs Fixed

#### Bug #1: Registered Behaviors Not Being Used

**Problem:** Even after registering agents, IPC server used mock logic instead of registered behaviors.

**Root Cause:** In [python/ipc/server.py:56](python/ipc/server.py#L56):
```python
# BROKEN (empty dict is falsy):
self.behaviors = behaviors or {}

# FIXED (None check):
self.behaviors = behaviors if behaviors is not None else {}
```

When `AgentArena.behaviors` was an empty dict `{}`, Python's `or` operator treated it as falsy and created a NEW dict, breaking the reference.

**Symptoms:**
- Python logs: `Using mock logic for agent foraging_agent_001`
- Agent registered but behavior dict reference was broken

#### Bug #2: Agent Not Moving Physically

**Problem:** Agent received `move_to` commands but didn't update position.

**Root Cause:** SimpleAgent had no movement implementation in `_process()`.

**Fix:** Added frame-based movement logic:
```gdscript
func _process(delta):
    if _is_moving:
        var distance = global_position.distance_to(_target_position)
        if distance < 0.1:
            _is_moving = false
            global_position = _target_position
            return

        var direction = (_target_position - global_position).normalized()
        var move_distance = _movement_speed * move_speed * delta

        if move_distance > distance:
            global_position = _target_position
            _is_moving = false
        else:
            global_position += direction * move_distance
```

**Symptoms:**
- Godot logs: `Distance Traveled: 0.00 meters`
- Tool execution returned success but position unchanged

## How It Works

### Observation Flow

1. **Godot Scene** ([foraging.gd](scripts/foraging.gd#L114-133)) sends observations each tick:
   ```gdscript
   func _on_scene_tick(tick: int):
       # Build observations for agent
       var obs = _build_observations_for_agent(agent_data)

       # Send to Python backend
       _request_backend_decision(agent_data, obs, tick)
   ```

2. **SceneController** ([base_scene_controller.gd](scripts/base_scene_controller.gd)) sends HTTP request:
   ```gdscript
   func _request_backend_decision(agent_data, observations, tick):
       var headers = ["Content-Type: application/json"]
       var body = JSON.stringify({
           "agent_id": agent_data.id,
           "tick": tick,
           "position": observations.position,
           "nearby_resources": observations.nearby_resources,
           "nearby_hazards": observations.nearby_hazards
       })

       http_request.request(backend_url + "/observe", headers, HTTPClient.METHOD_POST, body)
   ```

3. **IPC Server** ([python/ipc/server.py](python/ipc/server.py#L397-495)) processes observation:
   ```python
   @app.post("/observe")
   async def process_observation(observation: dict[str, Any]) -> dict[str, Any]:
       agent_id = observation.get("agent_id")
       behavior = self.behaviors.get(agent_id)  # Get registered behavior

       if behavior:
           # Convert to Observation schema
           obs = perception_to_observation(perception)

           # Get tool schemas
           tool_schemas = [...]

           # Agent decides action
           decision = behavior.decide(obs, tool_schemas)

           return {
               "tool": decision.tool,
               "params": decision.params,
               "reasoning": decision.reasoning
           }
   ```

4. **SimpleForager** ([python/user_agents/examples/simple_forager.py](python/user_agents/examples/simple_forager.py)) decides:
   ```python
   def decide(self, observation: Observation, available_tools: list[ToolSchema]) -> AgentDecision:
       # Find nearest resource
       nearest_resource = min(observation.nearby_resources, key=lambda r: r['distance'])

       # Check for nearby hazards
       nearby_hazards = [h for h in observation.nearby_hazards if h['distance'] < 3.0]

       if nearby_hazards:
           # Avoid hazard
           safe_position = calculate_safe_position(...)
           return AgentDecision(
               tool="move_to",
               params={"target_position": safe_position, "speed": 1.0},
               reasoning=f"Avoiding {hazard['type']} at distance {hazard['distance']:.1f}"
           )
       else:
           # Move toward resource
           return AgentDecision(
               tool="move_to",
               params={"target_position": nearest_resource['position'], "speed": 1.5},
               reasoning=f"Moving toward {nearest_resource['type']}"
           )
   ```

### Execution Flow

1. **Godot receives decision** and calls agent's tool:
   ```gdscript
   func _execute_backend_decision(agent_data, decision):
       print("[Backend Decision] Tick %d: %s - %s" % [tick, decision.tool, decision.reasoning])

       # Call the agent's tool
       agent_data.agent.call_tool(decision.tool, decision.params)
   ```

2. **SimpleAgent** executes movement:
   ```gdscript
   func call_tool(tool_name: String, parameters: Dictionary = {}) -> Dictionary:
       if tool_name == "move_to":
           var target = parameters.target_position
           if target is Array and target.size() >= 3:
               _target_position = Vector3(target[0], target[1], target[2])

           _movement_speed = parameters.get("speed", 1.0)
           _is_moving = true
           print("Starting movement to ", _target_position, " at speed ", _movement_speed)

       return ToolRegistryService.execute_tool(agent_id, tool_name, parameters)
   ```

3. **Each frame** updates position:
   ```gdscript
   func _process(delta):
       if _is_moving:
           var direction = (_target_position - global_position).normalized()
           var move_distance = _movement_speed * move_speed * delta
           global_position += direction * move_distance
   ```

## Metrics Tracked

The foraging scene tracks:

- **Resources Collected**: 0/7 → 7/7 when complete
- **Damage Taken**: From fire pits (10 damage) or pits (25 damage)
- **Distance Traveled**: Total meters moved
- **Time Elapsed**: Seconds since start
- **Efficiency Score**: `(resources/max_resources * 100) - min(damage, 100)`

## Next Steps

Now that Issue #30 is complete, you can:

1. **Create more agents** - Implement different foraging strategies
2. **Add more scenes** - See [docs/backlog_items.md](docs/backlog_items.md) for scene ideas
3. **Improve agents** - Add long-term memory, better planning
4. **Run benchmarks** - Compare different agent implementations

## Troubleshooting

### Model not found error

```
ValueError: Model path does not exist: path/to/model.gguf
```

**Fix:** Download a model first using the model manager:
```bash
cd python
.\venv\Scripts\activate
python -m tools.model_manager download tinyllama-1.1b-chat --format gguf --quant q4_k_m
```

Then use the correct path:
```bash
python run_ipc_server_with_gpu.py --model ../models/tinyllama-1.1b-chat/gguf/q4_k_m/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf --gpu-layers -1
```

### CUDA/GPU not detected

**Check:**
- NVIDIA GPU with CUDA support
- CUDA Toolkit installed
- `llama-cpp-python` installed with CUDA support:
  ```bash
  pip uninstall llama-cpp-python
  CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python --no-cache-dir
  ```

**Fallback:** Use CPU-only mode:
```bash
python run_ipc_server_with_gpu.py --model <path> --gpu-layers 0
```

### Agent uses mock logic instead of registered behavior

**Check:**
- IPC server logs show "Registered SimpleForager for agent_id: foraging_agent_001"
- Agent ID in Godot scene matches registered ID exactly
- `behaviors` dict reference is preserved (not using `or {}`)

**Fix:** Ensure [python/ipc/server.py:56](python/ipc/server.py#L56) uses:
```python
self.behaviors = behaviors if behaviors is not None else {}
```

### Agent doesn't move

**Check:**
- `_process(delta)` function exists in SimpleAgent
- `_is_moving` is set to `true` when move_to is called
- `move_speed` export variable is > 0

**Fix:** Ensure movement logic is implemented in [scripts/simple_agent.gd](scripts/simple_agent.gd#L130-151)

### Resources not being collected

**Check:**
- `COLLECTION_RADIUS = 2.0` in [scripts/foraging.gd](scripts/foraging.gd#L11)
- Agent is moving close enough to resources
- Resources haven't already been collected

**Fix:** Increase collection radius or improve agent pathfinding
