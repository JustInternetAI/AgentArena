# Testing Agents with GPU-Accelerated Backend

This guide shows how to run the full Godot + Python IPC setup with your GPU-accelerated llama.cpp backend.

## Quick Start (Tool Execution Only)

This tests that the IPC communication works without LLM agents:

### Step 1: Start IPC Server
```bash
# From project root
START_IPC_SERVER.bat
```

The server will start at `http://127.0.0.1:5000` and automatically register all tools (movement, inventory, world_query).

### Step 2: Open Test Scene in Godot
1. Open Godot editor
2. Navigate to: `scenes/tests/test_tool_execution_simple.tscn`
3. Press **F6** (Run Current Scene)

### Step 3: Verify Results
Check both consoles:
- **Godot Console**: Shows test execution and results
- **Python Console**: Shows tool execution logs

**Expected Output (Python):**
```
2025-11-18 - ipc.server - INFO - Registered 15 tools
2025-11-18 - ipc.server - INFO - Executing tool 'move_to' for agent...
2025-11-18 - ipc.server - INFO - Tool 'move_to' executed: success=True
```

---

## Full Agent Test (with GPU Backend)

This tests agents making decisions with your GPU-accelerated LLM backend.

### Prerequisites

1. **GPU-accelerated backend working** ✅ (You already have this!)
2. **IPC server modified to use LLM backend**
3. **Test scene that triggers agent decisions**

### Step 1: Create GPU-Enabled IPC Server Script

Create `python/run_ipc_server_with_gpu.py`:

```python
"""
IPC Server with GPU-accelerated agent backend.
"""

import argparse
import logging
import sys

from agent_runtime.runtime import AgentRuntime
from agent_runtime.agent import Agent
from agent_runtime.tool_dispatcher import ToolDispatcher
from backends import LlamaCppBackend, BackendConfig
from ipc.server import create_server
from tools import register_movement_tools, register_inventory_tools, register_world_query_tools

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Agent Arena IPC Server with GPU Backend")
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument(
        "--model",
        type=str,
        default="../models/llama-2-7b-chat.Q4_K_M.gguf",
        help="Path to GGUF model file"
    )
    parser.add_argument(
        "--gpu-layers",
        type=int,
        default=-1,
        help="Number of layers to offload to GPU (-1 = all, 0 = CPU only)"
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("=" * 60)
    logger.info("Agent Arena IPC Server (GPU-Accelerated)")
    logger.info("=" * 60)
    logger.info(f"Host: {args.host}")
    logger.info(f"Port: {args.port}")
    logger.info(f"Max Workers: {args.workers}")
    logger.info(f"Model: {args.model}")
    logger.info(f"GPU Layers: {args.gpu_layers}")
    logger.info("=" * 60)

    try:
        # Create GPU-accelerated backend
        backend_config = BackendConfig(
            model_path=args.model,
            temperature=0.7,
            max_tokens=256,
            n_gpu_layers=args.gpu_layers
        )

        logger.info("Loading GPU-accelerated LLM backend...")
        backend = LlamaCppBackend(backend_config)
        logger.info("✓ Backend loaded successfully")

        # Create runtime
        runtime = AgentRuntime(max_workers=args.workers)

        # Create a test agent with GPU backend
        tool_dispatcher = ToolDispatcher()
        register_movement_tools(tool_dispatcher)
        register_inventory_tools(tool_dispatcher)
        register_world_query_tools(tool_dispatcher)

        test_agent = Agent(
            agent_id="gpu_agent_001",
            backend=backend,
            tools=list(tool_dispatcher.tools.keys()),
            goals=["explore the world", "collect resources"]
        )

        runtime.register_agent(test_agent)
        logger.info(f"✓ Registered agent '{test_agent.state.agent_id}' with GPU backend")

        # Create and start server
        server = create_server(runtime=runtime, host=args.host, port=args.port)
        logger.info("Starting IPC server...")
        server.run()

    except KeyboardInterrupt:
        logger.info("\nShutting down gracefully...")
        if 'backend' in locals():
            backend.unload()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

### Step 2: Create Batch File to Start GPU Server

Create `START_GPU_IPC_SERVER.bat` in project root:

```batch
@echo off
REM Agent Arena - GPU-Accelerated IPC Server Startup

echo ========================================
echo Agent Arena - GPU IPC Server
echo ========================================
echo.

cd /d "%~dp0\python"

REM Activate venv
echo Activating Python virtual environment...
call venv\Scripts\activate.bat

echo.
echo Starting GPU-Accelerated IPC Server...
echo Model: Llama-2-7B (Q4_K_M)
echo GPU Acceleration: ENABLED (all layers)
echo Server: http://127.0.0.1:5000
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

python run_ipc_server_with_gpu.py --gpu-layers -1

if errorlevel 1 (
    echo.
    echo Server exited with error!
    pause
)
```

### Step 3: Test with Godot Scene

**Option A: Use existing test scene**
1. Start GPU server: `START_GPU_IPC_SERVER.bat`
2. Open `scenes/tests/test_tool_execution_simple.tscn`
3. Press F6
4. Tools will execute (no LLM needed)

**Option B: Create agent decision scene**

You'll need to modify one of the benchmark scenes to:
1. Register an agent via `/agents/register` endpoint
2. Send observations via `/tick` endpoint
3. Receive agent's LLM-driven action decision

Example GDScript:
```gdscript
extends Node

var http_client := HTTPRequest.new()
var agent_id = "gpu_agent_001"

func _ready():
    add_child(http_client)
    http_client.request_completed.connect(_on_request_completed)

    # Send observation to agent
    var observation = {
        "tick": 0,
        "perceptions": [{
            "agent_id": agent_id,
            "position": [0, 0, 0],
            "visible_entities": [
                {"type": "wood", "distance": 5.0}
            ],
            "inventory": []
        }]
    }

    var json = JSON.stringify(observation)
    http_client.request(
        "http://127.0.0.1:5000/tick",
        ["Content-Type: application/json"],
        HTTPClient.METHOD_POST,
        json
    )

func _on_request_completed(result, response_code, headers, body):
    var json = JSON.parse_string(body.get_string_from_utf8())
    print("Agent decision: ", json)
```

---

## Testing Workflow

### 1. Test IPC Server (No LLM)
```bash
START_IPC_SERVER.bat
# Run: scenes/tests/test_tool_execution_simple.tscn
```
**Verifies:** Tool execution works ✓

### 2. Test GPU Backend (Python Only)
```bash
cd python
venv\Scripts\activate
python test_agent_gpu.py
```
**Verifies:** GPU backend + agent decisions work ✓

### 3. Test Full Integration (Godot + Python + GPU)
```bash
START_GPU_IPC_SERVER.bat
# Run modified scene that sends /tick requests
```
**Verifies:** End-to-end agent pipeline works ✓

---

## Performance Expectations

With GPU acceleration enabled:
- **LLM Speed**: ~113 tokens/sec
- **Decision Time**: ~1-2 seconds per action
- **Recommended Tick Rate**: 0.5-1 Hz (one decision every 1-2 seconds)

Without GPU (CPU only):
- **LLM Speed**: ~9 tokens/sec
- **Decision Time**: ~15-20 seconds per action
- **Not recommended** for real-time simulation

---

## Troubleshooting

### Server won't start
- Check Python venv is activated
- Verify model exists: `models/llama-2-7b-chat.Q4_K_M.gguf`
- Check CUDA PATH (should be fixed now)

### Agent not responding
- Verify agent registered: Check server logs for "Registered agent"
- Send observation to `/tick` endpoint
- Check both consoles for errors

### GPU not being used
- Check server startup logs for "Offloading all layers to GPU"
- Verify CUDA toolkit installed
- Monitor GPU usage: `nvidia-smi`

### Slow responses
- Check GPU utilization in `nvidia-smi`
- Verify `n_gpu_layers=-1` (all layers on GPU)
- Reduce `max_tokens` parameter (currently 256)

---

## Next Steps

1. **Modify existing benchmark scenes** to send `/tick` requests
2. **Create custom test scene** for agent decision-making
3. **Add agent registration** in scene `_ready()` function
4. **Implement perception loop** (Godot → Python observations)
5. **Handle action responses** (Python → Godot actions)

## Current Status

✅ GPU backend working (113 tok/s)
✅ IPC server working (tool execution)
✅ Python agent test working (all 3 scenarios)
⏳ **TODO**: Connect agents to IPC `/tick` endpoint
⏳ **TODO**: Modify Godot scenes to use agent decisions
