# IPC System - Godot ↔ Python Communication

## Overview

The IPC (Inter-Process Communication) system enables real-time communication between the Godot simulation engine (C++) and the Python agent runtime (LLM-based decision making).

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Godot Simulation (C++)                    │
│  ┌──────────────┐       ┌──────────────┐                   │
│  │ Simulation   │──────▶│  IPCClient   │──┐                │
│  │  Manager     │       │   (Node)     │  │                │
│  └──────────────┘       └──────────────┘  │                │
│         │                                   │                │
│         │                                   │ HTTP/JSON     │
│  ┌──────▼──────┐                          │                │
│  │   Agents    │                          │                │
│  │  (Nodes)    │                          │                │
│  └─────────────┘                          │                │
└───────────────────────────────────────────┼─────────────────┘
                                             │
                                             │ POST /tick
                                             │
┌───────────────────────────────────────────┼─────────────────┐
│                 Python Runtime              │                 │
│  ┌─────────────────────────────────────────▼──────────────┐ │
│  │          FastAPI IPC Server (IPCServer)                 │ │
│  └─────────────────────────────────────────┬──────────────┘ │
│                                             │                 │
│  ┌──────────────────────────────────────────▼─────────────┐ │
│  │              AgentRuntime                               │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐            │ │
│  │  │ Agent 1  │  │ Agent 2  │  │ Agent N  │            │ │
│  │  └──────────┘  └──────────┘  └──────────┘            │ │
│  └──────────────────────────────────────────┬─────────────┘ │
│                                             │                 │
│  ┌──────────────────────────────────────────▼─────────────┐ │
│  │              LLM Backend (llama.cpp, etc)               │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Components

### Godot Side (C++)

#### IPCClient (Node)
- **Purpose**: HTTP client for sending perception data to Python and receiving action decisions
- **Key Methods**:
  - `connect_to_server(url)` - Connect to Python IPC server
  - `send_tick_request(tick, perceptions)` - Send perception data for a simulation tick
  - `get_tick_response()` - Retrieve action decisions from Python
  - `has_response()` - Check if response is available
- **Signals**:
  - `response_received(response)` - Emitted when actions are received
  - `connection_failed(error)` - Emitted on connection errors

### Python Side

#### IPCServer (FastAPI)
- **Purpose**: HTTP server that receives perception data and returns action decisions
- **Endpoints**:
  - `GET /` - Server status and metrics
  - `GET /health` - Health check
  - `POST /tick` - Process simulation tick (main endpoint)
  - `POST /agents/register` - Register new agents
  - `GET /metrics` - Performance metrics
- **Key Methods**:
  - `run()` - Start server (blocking)
  - `run_async()` - Start server (async)

#### Message Schemas

##### PerceptionMessage
Observation data sent from Godot to Python for a single agent:
```python
{
    "agent_id": "agent_001",
    "tick": 1234,
    "position": [x, y, z],
    "rotation": [x, y, z],
    "velocity": [x, y, z],
    "visible_entities": [...],
    "inventory": [...],
    "health": 100.0,
    "energy": 100.0,
    "custom_data": {}
}
```

##### ActionMessage
Action decision sent from Python to Godot for a single agent:
```python
{
    "agent_id": "agent_001",
    "tick": 1234,
    "tool": "move_to",
    "params": {
        "target_position": [x, y, z],
        "speed": 1.5
    },
    "reasoning": "Moving towards resource location"
}
```

##### TickRequest
Full request sent from Godot containing all agent perceptions:
```python
{
    "tick": 1234,
    "perceptions": [PerceptionMessage, ...],
    "simulation_state": {}
}
```

##### TickResponse
Full response sent from Python containing all agent actions:
```python
{
    "tick": 1234,
    "actions": [ActionMessage, ...],
    "metrics": {
        "tick_time_ms": 150.5,
        "agents_processed": 10,
        "actions_generated": 8
    }
}
```

## Usage

### 1. Start Python IPC Server

```bash
cd python
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# Start server
python run_ipc_server.py

# With custom options
python run_ipc_server.py --host 127.0.0.1 --port 5000 --workers 4 --debug
```

### 2. Use in Godot Scene

```gdscript
extends Node

var simulation_manager: SimulationManager
var ipc_client: IPCClient

func _ready():
    # Create simulation manager
    simulation_manager = SimulationManager.new()
    add_child(simulation_manager)

    # Create IPC client
    ipc_client = IPCClient.new()
    ipc_client.server_url = "http://127.0.0.1:5000"
    add_child(ipc_client)

    # Connect signals
    ipc_client.response_received.connect(_on_response_received)
    simulation_manager.tick_advanced.connect(_on_tick_advanced)

    # Wait for initialization
    await get_tree().process_frame

    # Connect to server
    ipc_client.connect_to_server("http://127.0.0.1:5000")

func _on_tick_advanced(tick: int):
    # Gather perception data from agents
    var perceptions = []
    for agent in get_tree().get_nodes_in_group("agents"):
        var perception = {
            "agent_id": agent.agent_id,
            "tick": tick,
            "position": [agent.position.x, agent.position.y, agent.position.z],
            # ... other perception data
        }
        perceptions.append(perception)

    # Send to Python
    ipc_client.send_tick_request(tick, perceptions)

func _on_response_received(response: Dictionary):
    # Execute actions from Python
    var actions = response.get("actions", [])
    for action in actions:
        var agent = get_node("Agents/" + action["agent_id"])
        agent.execute_action(action)
```

### 3. Test IPC Communication

Run the test scene:
```bash
# In Godot editor, open and run: scenes/ipc_test.gd
# Or use command line:
godot --path "c:\Projects\Agent Arena" scenes/ipc_test.gd
```

## Protocol Details

### Communication Flow

1. **Godot** advances simulation tick
2. **Godot** collects perception data from all agents
3. **Godot** sends `POST /tick` request to Python with `TickRequest`
4. **Python** receives request, distributes perceptions to agents
5. **Python** agents process observations and decide actions (LLM inference)
6. **Python** collects all actions and sends `TickResponse`
7. **Godot** receives response, executes actions in simulation
8. Repeat for next tick

### Performance Considerations

- **Latency**: Each tick request adds ~10-500ms depending on LLM inference time
- **Async Processing**: Python uses `asyncio` to process multiple agents concurrently
- **Batching**: All agents processed in a single HTTP request to minimize overhead
- **Timeout**: Consider implementing timeouts for slow LLM responses

### Error Handling

- **Connection Failures**: IPC client emits `connection_failed` signal
- **Server Errors**: Returns HTTP 500 with error details
- **Timeout**: HTTPRequest has built-in timeout (configurable)
- **Retry Logic**: Implement in Godot script as needed

## Development Tips

### Debugging

1. **Enable Debug Logging**:
   ```bash
   python run_ipc_server.py --debug
   ```

2. **Test Server Manually**:
   ```bash
   curl http://127.0.0.1:5000/health
   curl -X POST http://127.0.0.1:5000/tick -H "Content-Type: application/json" -d @test_request.json
   ```

3. **Monitor Performance**:
   ```bash
   curl http://127.0.0.1:5000/metrics
   ```

### Common Issues

1. **"Connection Failed"**
   - Make sure Python IPC server is running
   - Check firewall settings
   - Verify port is not in use

2. **Slow Response Times**
   - LLM inference is the main bottleneck
   - Use smaller/quantized models
   - Increase worker pool size
   - Enable response caching

3. **JSON Parse Errors**
   - Verify message format matches schemas
   - Check for NaN/Inf values in float fields
   - Ensure UTF-8 encoding

## Future Enhancements

### Planned Improvements

1. **gRPC Protocol**: Upgrade from HTTP to gRPC for lower latency and bidirectional streaming
2. **Shared Memory**: Zero-copy IPC for maximum performance
3. **Compression**: MessagePack or Protobuf for smaller payloads
4. **Persistent Connections**: WebSocket or gRPC streaming to avoid connection overhead
5. **Load Balancing**: Distribute agents across multiple Python instances

### Migration Path

The current HTTP/JSON implementation is designed to be easily replaceable:
- Message schemas are decoupled from transport
- Same interfaces can be reused with different protocols
- Godot and Python can upgrade independently

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Godot HTTPRequest](https://docs.godotengine.org/en/stable/classes/class_httprequest.html)
- [Agent Runtime Architecture](architecture.md)
