# Autoload Service Architecture

## Overview

The Agent Arena now uses Godot's **autoload singleton pattern** for persistent backend services. This architecture ensures that IPC connections and tool registries survive scene changes and are shared across all agents.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  Autoload Singletons (Global - Persist Across Scenes)      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  IPCService (/root/IPCService)                             │
│  ├── Manages single IPCClient instance                     │
│  ├── Persistent HTTP connection to Python backend          │
│  ├── Signals: connected_to_server, tool_response, etc.     │
│  └── Auto-connects on startup                              │
│                                                             │
│  ToolRegistryService (/root/ToolRegistryService)           │
│  ├── Manages global ToolRegistry instance                  │
│  ├── Knows all available tools                             │
│  ├── Routes tool calls through IPCService                  │
│  └── Pre-registers default tools on startup                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ Uses global services
                            │
┌─────────────────────────────────────────────────────────────┐
│  Scene-Specific Nodes (Created per scene/NPC)              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  SimpleAgent (extends Node3D)                              │
│  ├── Lightweight wrapper around C++ Agent                  │
│  ├── Has agent_id (e.g., "npc_guard_001")                 │
│  ├── Auto-connects to global services                      │
│  ├── Signals: tool_completed, tick_completed               │
│  └── Dies when scene changes (but state persists in Python)│
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. IPCService (Autoload Singleton)

**File**: `scripts/autoload/ipc_service.gd`

**Purpose**: Manages the persistent connection to the Python IPC server.

**Features**:
- Creates and manages a single `IPCClient` C++ node
- Auto-connects to `http://127.0.0.1:5000` on startup
- Provides signal-based API for tool execution and tick updates
- Survives scene changes

**Signals**:
- `connected_to_server` - Emitted when Python backend connection succeeds
- `connection_failed(error: String)` - Emitted on connection failure
- `tool_response(agent_id: String, tool_name: String, response: Dictionary)`
- `tick_response(agent_id: String, response: Dictionary)`

**Usage**:
```gdscript
# Execute a tool (from anywhere in your game)
IPCService.execute_tool("agent_001", "move_to", {"target_position": [10, 0, 5]})

# Connect to responses
IPCService.tool_response.connect(_on_tool_response)

# Check connection status
if IPCService.is_backend_connected():
    print("Backend is ready!")
```

### 2. ToolRegistryService (Autoload Singleton)

**File**: `scripts/autoload/tool_registry_service.gd`

**Purpose**: Manages the global catalog of tools available to all agents.

**Features**:
- Creates and manages a single `ToolRegistry` C++ node
- Pre-registers default tools (move_to, pickup_item, etc.)
- Routes tool execution through IPCService
- Survives scene changes

**Signals**:
- `tool_registered(tool_name: String)`
- `tool_executed(agent_id: String, tool_name: String)`

**Pre-registered Tools**:
- `move_to` - Move to a target position
- `navigate_to` - Navigate using pathfinding
- `stop_movement` - Stop all movement
- `pickup_item` - Pick up an item
- `drop_item` - Drop an item
- `use_item` - Use an item
- `get_inventory` - Get inventory contents
- `look_at` - Examine an object

**Usage**:
```gdscript
# Get all available tools
var tools = ToolRegistryService.get_available_tools()
print("Available tools: ", tools)

# Register a custom tool
ToolRegistryService.register_tool("custom_action", {
    "name": "custom_action",
    "description": "Does something custom",
    "parameters": {...}
})

# Execute a tool
ToolRegistryService.execute_tool("agent_001", "move_to", params)
```

### 3. SimpleAgent (Scene Node)

**File**: `scripts/simple_agent.gd`

**Purpose**: Lightweight agent wrapper that automatically uses global services.

**Features**:
- Extends `Node3D` (can be placed in 3D scenes)
- Wraps C++ `Agent` class for memory and perception
- Auto-connects to IPCService and ToolRegistryService
- Auto-generates agent_id if not provided
- Signal-based tool completion notifications

**Properties**:
- `agent_id: String` - Unique identifier (required)
- `auto_connect: bool` - Auto-connect to services (default: true)

**Signals**:
- `tool_completed(tool_name: String, response: Dictionary)`
- `tick_completed(response: Dictionary)`

**Usage**:
```gdscript
# Create an agent (in any scene)
var agent = SimpleAgent.new()
agent.agent_id = "npc_guard_001"
agent.tool_completed.connect(_on_tool_done)
add_child(agent)

# Call a tool
agent.call_tool("move_to", {"target_position": [10, 0, 5]})

# Handle response
func _on_tool_done(tool_name: String, response: Dictionary):
    print("Tool ", tool_name, " completed: ", response)
```

## Benefits of This Architecture

### ✅ Persistent Backend Connection
- IPCService maintains a single HTTP connection to Python
- No reconnection overhead when changing scenes
- Services start automatically when Godot launches

### ✅ Shared Resources
- All agents use the same IPCClient and ToolRegistry
- Lower memory footprint
- Consistent state across the game

### ✅ Scene Independence
- Agents are lightweight scene nodes
- Backend maintains agent state (Python side)
- Can recreate Agent nodes without losing state

### ✅ Simple API
- No manual setup required in scenes
- Just create SimpleAgent nodes and go
- Signal-based async communication

### ✅ Testability
- Easy to test individual components
- Services can be mocked for unit tests
- Clear separation of concerns

## Migration from Old Architecture

### Old Way (Manual Setup):
```gdscript
# Every scene had to do this:
var ipc_client = IPCClient.new()
var tool_registry = ToolRegistry.new()
var agent = Agent.new()

add_child(ipc_client)
add_child(tool_registry)
add_child(agent)

tool_registry.set_ipc_client(ipc_client)
agent.set_tool_registry(tool_registry)

ipc_client.connect_to_server("http://127.0.0.1:5000")

# Register all tools manually...
tool_registry.register_tool("move_to", {...})
# ... etc
```

### New Way (Automatic):
```gdscript
# Just create agents - services are already running!
var agent = SimpleAgent.new()
agent.agent_id = "my_agent"
add_child(agent)

# That's it! Agent is ready to use tools.
agent.call_tool("move_to", {"target_position": [10, 0, 5]})
```

## Testing

### Test Scene
**File**: `scenes/tests/test_autoload_services.tscn`
**Script**: `scripts/tests/test_autoload_services.gd`

This test demonstrates:
- Creating multiple agents that share services
- Executing different tools
- Handling async responses via signals
- Services persisting across operations

### Running the Test

1. Start Python IPC server:
   ```bash
   cd python
   venv\Scripts\activate
   python run_ipc_server.py
   ```

2. Run the test scene:
   ```bash
   "C:\Program Files\Godot\Godot_v4.5.1-stable_win64.exe" --path . res://scenes/tests/test_autoload_services.tscn
   ```

3. Observe:
   - Services auto-connect on startup
   - Multiple agents created with minimal code
   - Tool execution and responses
   - Press Q to quit, T to re-run tests

## Configuration

### project.godot
```ini
[autoload]

IPCService="*res://scripts/autoload/ipc_service.gd"
ToolRegistryService="*res://scripts/autoload/tool_registry_service.gd"
```

The `*` prefix means the autoload is a singleton (loaded at startup).

### Changing IPC Server URL

Edit `scripts/autoload/ipc_service.gd`:
```gdscript
var server_url := "http://127.0.0.1:5000"  # Change this
```

## Debugging

### Check if Services are Loaded
```gdscript
if IPCService:
    print("IPCService is loaded")
if ToolRegistryService:
    print("ToolRegistryService is loaded")
```

### Monitor Connection Status
```gdscript
IPCService.connected_to_server.connect(func():
    print("Connected!")
)

IPCService.connection_failed.connect(func(error):
    print("Connection failed: ", error)
)
```

### List Available Tools
```gdscript
print("Available tools: ", ToolRegistryService.get_available_tools())
print("Tool count: ", ToolRegistryService.get_tool_count())
```

## Advanced Usage

### Custom Tools at Runtime
```gdscript
# Register a scene-specific tool
ToolRegistryService.register_tool("open_door", {
    "name": "open_door",
    "description": "Open a specific door",
    "parameters": {
        "door_id": {"type": "string"}
    }
})
```

### Multiple Agents Coordination
```gdscript
# All agents share the same services automatically
var guard1 = SimpleAgent.new()
guard1.agent_id = "guard_001"

var guard2 = SimpleAgent.new()
guard2.agent_id = "guard_002"

# Both use the same IPCService and ToolRegistryService
# No additional setup needed!
```

### Scene Changes
```gdscript
# Agents die when scene changes, but services persist
get_tree().change_scene_to_file("res://scenes/other_scene.tscn")

# In the new scene, services are already connected!
# Just create new agents with the same IDs to continue
var agent = SimpleAgent.new()
agent.agent_id = "guard_001"  # Same ID = same state in Python
```

## Troubleshooting

### "IPCService not found!"
- Check `project.godot` has the `[autoload]` section
- Make sure the file path is correct: `res://scripts/autoload/ipc_service.gd`
- Restart Godot editor

### "Connection failed"
- Make sure Python IPC server is running
- Check server URL in `ipc_service.gd` matches Python server
- Check firewall settings for localhost:5000

### "No response from tools"
- Make sure agent's signals are connected
- Check Python server logs for errors
- Verify tool name exists: `ToolRegistryService.has_tool("tool_name")`

### HTTPRequest crashes (old issue)
- This should no longer happen with autoload architecture
- Services are created once at startup, not per-scene
- If it still happens, check C++ `set_owner()` calls in IPCClient

## Future Enhancements

- [ ] Add connection retry logic with exponential backoff
- [ ] Add connection status UI indicator
- [ ] Cache tool results for performance
- [ ] Add tool execution queue management
- [ ] Support multiple IPC server URLs (load balancing)
- [ ] Add metrics/telemetry for tool usage
