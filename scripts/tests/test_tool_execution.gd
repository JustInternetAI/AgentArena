extends Node
## Test script for tool execution system
##
## This script tests the complete tool execution pipeline:
## SimpleAgent -> ToolRegistryService (autoload) -> IPCService (autoload) -> Python IPC Server

var agent  # SimpleAgent instance
var tests_started := false
var connection_verified := false

func _ready():
	print("=== Tool Execution Test (Using SimpleAgent) ===")

	# Prevent scene from auto-closing
	get_tree().set_auto_accept_quit(false)

	# Load SimpleAgent script
	var simple_agent_script = load("res://scripts/simple_agent.gd")
	if not simple_agent_script:
		push_error("Could not load simple_agent.gd!")
		return

	# Create SimpleAgent (will auto-connect to services)
	agent = simple_agent_script.new()
	agent.name = "TestAgent"
	agent.agent_id = "test_agent_001"
	add_child(agent)

	print("✓ SimpleAgent created (auto-connects to IPCService and ToolRegistryService)")

	# Connect to SimpleAgent signals
	agent.tool_completed.connect(_on_tool_completed)

	# Connect to IPCService to know when backend is ready
	if IPCService:
		IPCService.connected_to_server.connect(_on_connected_to_server)
		IPCService.connection_failed.connect(_on_connection_failed)

	print("\nWaiting for IPCService to connect to backend...")
	print("IMPORTANT: Make sure Python IPC server is running!")
	print("  cd python && venv\\Scripts\\activate && python run_ipc_server.py")

func test_tools():
	print("\n=== Testing Tool Execution ===")
	print("Note: Tool execution is async - responses come via signals\n")

	# Test 1: Move to tool
	print("[Test 1] Testing move_to tool...")
	var move_result = agent.call_tool("move_to", {
		"target_position": [10.0, 0.0, 5.0],
		"speed": 1.5
	})
	print("Request sent: ", move_result)

	# Test 2: Pickup item tool
	print("\n[Test 2] Testing pickup_item tool...")
	var pickup_result = agent.call_tool("pickup_item", {
		"item_id": "sword_001"
	})
	print("Request sent: ", pickup_result)

	# Test 3: Stop movement tool
	print("\n[Test 3] Testing stop_movement tool...")
	var stop_result = agent.call_tool("stop_movement", {})
	print("Request sent: ", stop_result)

	# Test 4: Get inventory tool
	print("\n[Test 4] Testing get_inventory tool...")
	var inventory_result = agent.call_tool("get_inventory", {})
	print("Request sent: ", inventory_result)

	# Test 5: Direct ToolRegistryService execution
	print("\n[Test 5] Testing navigate_to tool via ToolRegistryService...")
	if ToolRegistryService:
		var direct_result = ToolRegistryService.execute_tool(
			agent.agent_id,
			"navigate_to",
			{"target_position": [20.0, 0.0, 10.0]}
		)
		print("Request sent: ", direct_result)

	print("\n=== All Tool Requests Sent ===")
	print("Watch for '[Tool Completed]' signals below...")
	print("Press Q to quit when done")

func _on_connected_to_server():
	print("\n✓ Connected to IPC server!")
	connection_verified = true

	# Start tests after connection
	if not tests_started:
		tests_started = true
		await get_tree().create_timer(0.5).timeout  # Brief delay to ensure everything is ready
		test_tools()

func _on_tool_completed(tool_name: String, response: Dictionary):
	print("\n[Tool Completed]")
	print("Tool: ", tool_name)
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
			print("Running tests again...")
			test_tools()
		elif event.keycode == KEY_Q:
			print("Quitting...")
			get_tree().quit()
