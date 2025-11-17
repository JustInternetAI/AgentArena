extends Node
## Test script for tool execution system
##
## This script tests the complete tool execution pipeline:
## Agent -> ToolRegistry -> IPCClient -> Python IPC Server -> ToolDispatcher -> Tool Functions

var ipc_client: IPCClient
var tool_registry: ToolRegistry
var agent: Agent

func _ready():
	print("=== Tool Execution Test ===")

	# Create IPC Client
	ipc_client = IPCClient.new()
	ipc_client.name = "IPCClient"
	ipc_client.server_url = "http://127.0.0.1:5000"
	add_child(ipc_client)

	# Create Tool Registry
	tool_registry = ToolRegistry.new()
	tool_registry.name = "ToolRegistry"
	add_child(tool_registry)

	# Connect tool registry to IPC client
	tool_registry.set_ipc_client(ipc_client)

	# Register some tools
	var move_schema = {}
	move_schema["name"] = "move_to"
	move_schema["description"] = "Move to a target position"
	move_schema["parameters"] = {}
	tool_registry.register_tool("move_to", move_schema)

	var pickup_schema = {}
	pickup_schema["name"] = "pickup_item"
	pickup_schema["description"] = "Pick up an item"
	pickup_schema["parameters"] = {}
	tool_registry.register_tool("pickup_item", pickup_schema)

	# Create Agent
	agent = Agent.new()
	agent.name = "TestAgent"
	agent.agent_id = "test_agent_001"
	add_child(agent)

	# Connect agent to tool registry
	agent.set_tool_registry(tool_registry)

	# Connect signals BEFORE attempting connection
	ipc_client.response_received.connect(_on_response_received)
	ipc_client.connection_failed.connect(_on_connection_failed)

	# Connect to server
	print("Connecting to IPC server...")
	print("IMPORTANT: Make sure Python IPC server is running!")
	print("  cd python && venv\\Scripts\\activate && python run_ipc_server.py")

	ipc_client.connect_to_server("http://127.0.0.1:5000")

	# Wait a moment for connection, then test tools
	print("Waiting 3 seconds for connection...")
	await get_tree().create_timer(3.0).timeout

	if not ipc_client.is_server_connected():
		print("\n[WARNING] Not connected to server!")
		print("Please check that:")
		print("1. Python IPC server is running")
		print("2. Server is on http://127.0.0.1:5000")
		print("3. No firewall is blocking the connection")
		print("\nTrying to test tools anyway...")

	test_tools()

func test_tools():
	print("\n=== Testing Tool Execution ===")
	print("Note: Tool execution is async - responses come via signals")
	print("Check the IPC Response Received section below for actual results\n")

	# Test 1: Move tool
	print("[Test 1] Testing move_to tool...")
	var move_params = {
		"target_position": [10.0, 0.0, 5.0],
		"speed": 1.5
	}
	var move_result = agent.call_tool("move_to", move_params)
	print("Request sent: ", move_result)
	await get_tree().create_timer(0.5).timeout

	# Test 2: Pickup item tool
	print("\n[Test 2] Testing pickup_item tool...")
	var pickup_params = {
		"item_id": "sword_001"
	}
	var pickup_result = agent.call_tool("pickup_item", pickup_params)
	print("Request sent: ", pickup_result)
	await get_tree().create_timer(0.5).timeout

	# Test 3: Stop movement tool
	print("\n[Test 3] Testing stop_movement tool...")
	var stop_result = agent.call_tool("stop_movement", {})
	print("Request sent: ", stop_result)
	await get_tree().create_timer(0.5).timeout

	# Test 4: Get inventory tool
	print("\n[Test 4] Testing get_inventory tool...")
	var inventory_result = agent.call_tool("get_inventory", {})
	print("Request sent: ", inventory_result)
	await get_tree().create_timer(0.5).timeout

	# Test 5: Direct ToolRegistry execution
	print("\n[Test 5] Testing navigate_to tool...")
	var direct_result = tool_registry.execute_tool("navigate_to", {
		"target_position": [20.0, 0.0, 10.0]
	})
	print("Request sent: ", direct_result)

	print("\n=== All Tool Requests Sent ===")
	print("Waiting for responses (check 'IPC Response Received' below)...")
	print("Python server log should show tool executions")

	# Wait a bit for all responses
	await get_tree().create_timer(2.0).timeout
	print("\n=== Test Complete ===")
	print("If you saw response_received callbacks above, tool execution works!")

func _on_response_received(response: Dictionary):
	print("\n[IPC Response Received]")
	print("Response: ", response)

func _on_connection_failed(error: String):
	print("\n[IPC Connection Failed]")
	print("Error: ", error)
	print("Make sure Python IPC server is running:")
	print("  cd python")
	print("  venv\\Scripts\\activate")
	print("  python run_ipc_server.py")

func _input(event):
	if event is InputEventKey and event.pressed:
		if event.keycode == KEY_T:
			test_tools()
		elif event.keycode == KEY_Q:
			print("Quitting...")
			get_tree().quit()
