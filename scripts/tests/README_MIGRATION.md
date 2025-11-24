# Test Scene Migration Guide

## Migrating from test_tool_execution.gd to test_autoload_services.gd

This guide shows how the test architecture has been simplified with autoload singletons.

## Old Architecture (test_tool_execution.gd)

**Problems**:
- 82 lines of setup code per test scene
- Had to manually create and wire IPCClient, ToolRegistry, Agent
- Had to register all tools manually
- Services died when scene changed
- Complex timing issues with _ready() and connection initialization
- HTTPRequest crashes due to per-scene instantiation

**Code**:
```gdscript
var ipc_client: IPCClient
var tool_registry: ToolRegistry
var agent: Agent

func _ready():
    # Create IPC Client
    ipc_client = IPCClient.new()
    ipc_client.name = "IPCClient"
    ipc_client.server_url = "http://127.0.0.1:5000"
    add_child(ipc_client)

    # Create Tool Registry
    tool_registry = ToolRegistry.new()
    tool_registry.name = "ToolRegistry"
    add_child(tool_registry)

    # Connect them
    tool_registry.set_ipc_client(ipc_client)

    # Register each tool manually (20+ lines)
    var move_schema = {}
    move_schema["name"] = "move_to"
    move_schema["description"] = "Move to a target position"
    move_schema["parameters"] = {}
    tool_registry.register_tool("move_to", move_schema)
    # ... repeat for each tool ...

    # Create Agent
    agent = Agent.new()
    agent.name = "TestAgent"
    agent.agent_id = "test_agent_001"
    add_child(agent)

    # Connect agent to registry
    agent.set_tool_registry(tool_registry)

    # Connect signals
    ipc_client.response_received.connect(_on_response_received)
    ipc_client.connection_failed.connect(_on_connection_failed)

    # Complex connection timing logic
    # (30+ lines of workarounds for race conditions)
    ...
```

## New Architecture (test_autoload_services.gd)

**Benefits**:
- ~40 lines for entire test (half the size!)
- No setup - services already running
- Tools pre-registered
- Services persist across scenes
- Clean signal-based API
- No timing issues

**Code**:
```gdscript
func _ready():
    # Services already exist as autoloads!
    # Just verify they're there
    if not IPCService or not ToolRegistryService:
        push_error("Services not found!")
        return

    # Connect to global signals
    IPCService.connected_to_server.connect(_on_server_connected)

func _on_server_connected():
    # Create agents - super simple!
    var agent = SimpleAgent.new()
    agent.agent_id = "test_agent_001"
    agent.tool_completed.connect(_on_tool_done)
    add_child(agent)

    # Use tools immediately
    agent.call_tool("move_to", {"target_position": [10, 0, 5]})
```

## Side-by-Side Comparison

| Feature | Old (test_tool_execution) | New (test_autoload_services) |
|---------|---------------------------|------------------------------|
| Setup code | 82 lines | ~10 lines |
| Manual wiring | Yes (IPCClient ↔ ToolRegistry ↔ Agent) | No (auto-connected) |
| Tool registration | Manual (20+ lines) | Pre-registered |
| Survives scene changes | No | Yes |
| HTTPRequest issues | Yes (crashes) | No (singleton pattern) |
| Timing workarounds | Yes (startup_delay, call_deferred) | No (services ready at startup) |
| Connection per scene | Yes (reconnect overhead) | No (single persistent connection) |
| Signal handling | Per-scene setup | Global, scene-independent |

## Converting an Existing Test Scene

### Step 1: Remove Manual Setup

**Delete**:
- `var ipc_client: IPCClient`
- `var tool_registry: ToolRegistry`
- All `IPCClient.new()` and `ToolRegistry.new()` code
- All `register_tool()` calls (tools are pre-registered)
- All `set_ipc_client()` and `set_tool_registry()` calls
- Connection timing workarounds (startup_delay, call_deferred)

### Step 2: Use SimpleAgent

**Replace**:
```gdscript
# Old
var agent = Agent.new()
agent.name = "TestAgent"
agent.agent_id = "test_agent_001"
add_child(agent)
agent.set_tool_registry(tool_registry)

# New
var agent = SimpleAgent.new()
agent.agent_id = "test_agent_001"
add_child(agent)
# That's it! Auto-connects to services
```

### Step 3: Connect to Global Signals

**Replace**:
```gdscript
# Old
ipc_client.response_received.connect(_on_response_received)
ipc_client.connection_failed.connect(_on_connection_failed)

# New
IPCService.connected_to_server.connect(_on_connected)
IPCService.connection_failed.connect(_on_failed)
agent.tool_completed.connect(_on_tool_done)
```

### Step 4: Use Simple Tool Calls

**Replace**:
```gdscript
# Old
var result = agent.call_tool("move_to", params)
# Then wait for ipc_client.response_received signal

# New
agent.call_tool("move_to", params)
# Response comes via agent.tool_completed signal
```

## Example Migration: Complete File

### Before (118 lines)
```gdscript
extends Node

var ipc_client: IPCClient
var tool_registry: ToolRegistry
var agent: Agent
var test_running := true
var connection_verified := false
var connection_timeout := 10.0
var time_since_connect := 0.0
var connection_initiated := false
var startup_delay := 0.0

func _ready():
    get_tree().set_auto_accept_quit(false)
    set_process(true)

    # Create IPC Client
    ipc_client = IPCClient.new()
    ipc_client.name = "IPCClient"
    ipc_client.server_url = "http://127.0.0.1:5000"
    add_child(ipc_client)

    # Create Tool Registry
    tool_registry = ToolRegistry.new()
    tool_registry.name = "ToolRegistry"
    add_child(tool_registry)

    tool_registry.set_ipc_client(ipc_client)

    # Register tools (20+ lines omitted for brevity)
    # ...

    # Create Agent
    agent = Agent.new()
    agent.name = "TestAgent"
    agent.agent_id = "test_agent_001"
    add_child(agent)

    agent.set_tool_registry(tool_registry)

    ipc_client.response_received.connect(_on_response_received)
    ipc_client.connection_failed.connect(_on_connection_failed)

    # Complex timing workarounds...
    # (40+ lines omitted)

func _process(delta):
    # Connection timing logic (30+ lines omitted)
    # ...

func test_tools():
    var params = {"target_position": [10.0, 0.0, 5.0]}
    agent.call_tool("move_to", params)
    # (More test code...)
```

### After (40 lines)
```gdscript
extends Node

var agents: Array[Node] = []

func _ready():
    print("=== Simple Test ===")

    # Services already running - just verify
    if not IPCService or not ToolRegistryService:
        push_error("Services not found!")
        return

    # Connect to global signals
    IPCService.connected_to_server.connect(_on_connected)

func _on_connected():
    print("Connected! Creating agent...")

    # Create agent
    var agent = SimpleAgent.new()
    agent.agent_id = "test_agent_001"
    agent.tool_completed.connect(_on_tool_done)
    add_child(agent)

    agents.append(agent)

    # Run test
    test_tools()

func test_tools():
    print("Testing tools...")
    var params = {"target_position": [10.0, 0.0, 5.0]}
    agents[0].call_tool("move_to", params)

func _on_tool_done(tool_name: String, response: Dictionary):
    print("Tool completed: ", tool_name, " -> ", response)
```

**Result**: **66% less code**, cleaner, more maintainable!

## Testing the New Architecture

1. **Start Python server**:
   ```bash
   cd python
   venv\Scripts\activate
   python run_ipc_server.py
   ```

2. **Run new test scene**:
   ```bash
   "C:\Program Files\Godot\Godot_v4.5.1-stable_win64.exe" --path . res://scenes/tests/test_autoload_services.tscn
   ```

3. **Expected output**:
   ```
   === Autoload Services Test ===
   ✓ IPCService found
   ✓ ToolRegistryService found
   ✓ Available tools: [move_to, navigate_to, stop_movement, ...]
   ✓ Connected to Python backend!
   Creating agent: test_agent_000
   Creating agent: test_agent_001
   Creating agent: test_agent_002
   [Test 1] Agent 0: move_to
   [Agent Tool Completed] Agent: test_agent_000, Tool: move_to
   ...
   ```

## Key Takeaways

1. **Autoloads eliminate boilerplate**: No more manual setup in every scene
2. **Persistence is automatic**: Services survive scene changes
3. **Simpler code = fewer bugs**: Less code to maintain and debug
4. **Better separation of concerns**: Services vs. scene-specific logic
5. **Easier testing**: Can test agents without setting up entire infrastructure

## When to Use Each Approach

### Use Old Approach (Manual Setup) When:
- Never (it's deprecated)

### Use New Approach (Autoloads) When:
- Always! It's better in every way:
  - Cleaner code
  - Fewer bugs
  - Better performance
  - Easier maintenance
  - More scalable

## Deprecated Files

The following files are **deprecated** and should not be used for new code:

- ❌ `scripts/tests/test_tool_execution.gd` (old manual setup)
- ❌ `scenes/tests/test_tool_execution.tscn` (old manual setup)

Use these instead:

- ✅ `scripts/tests/test_autoload_services.gd` (new autoload approach)
- ✅ `scenes/tests/test_autoload_services.tscn` (new autoload approach)
- ✅ `scripts/simple_agent.gd` (easy-to-use agent wrapper)

## Questions?

See [autoload_architecture.md](../../docs/autoload_architecture.md) for full documentation.
