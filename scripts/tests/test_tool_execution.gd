extends Node
## Test script for tool execution system
##
## This script tests the complete tool execution pipeline:
## Agent -> ToolRegistry -> IPCClient -> Python IPC Server -> ToolDispatcher -> Tool Functions

var ipc_client: IPCClient
var tool_registry: ToolRegistry
var agent: Agent
var test_running := true  # Keep scene alive
var wait_time := 0.0
var tests_started := false
var connection_verified := false
var connection_timeout := 10.0  # seconds
var time_since_connect := 0.0
var log_file: FileAccess
var connection_initiated := false
var startup_delay := 0.0

func write_log(message: String):
	if log_file and log_file.is_open():
		log_file.store_line(message)
		log_file.flush()
	print(message)

func _ready():
	# Open log file
	log_file = FileAccess.open("user://test_tool_execution.log", FileAccess.WRITE)
	if not log_file:
		print("ERROR: Could not open log file!")
		print("FileAccess error: ", FileAccess.get_open_error())
	write_log("=== Tool Execution Test - " + Time.get_datetime_string_from_system() + " ===")
	write_log("Scene starting up...")

	# Prevent scene from auto-closing - CRITICAL!
	get_tree().set_auto_accept_quit(false)
	write_log("Set auto_accept_quit to false")

	# Keep process running
	set_process(true)
	set_physics_process(true)

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

	# Register all tools being tested
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

	var stop_schema = {}
	stop_schema["name"] = "stop_movement"
	stop_schema["description"] = "Stop all movement"
	stop_schema["parameters"] = {}
	tool_registry.register_tool("stop_movement", stop_schema)

	var inventory_schema = {}
	inventory_schema["name"] = "get_inventory"
	inventory_schema["description"] = "Get current inventory contents"
	inventory_schema["parameters"] = {}
	tool_registry.register_tool("get_inventory", inventory_schema)

	var navigate_schema = {}
	navigate_schema["name"] = "navigate_to"
	navigate_schema["description"] = "Navigate to target using pathfinding"
	navigate_schema["parameters"] = {}
	tool_registry.register_tool("navigate_to", navigate_schema)

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

	# Don't use call_deferred or async - handle connection in _process() instead
	print("Waiting for IPCClient to initialize...")
	write_log("Will connect in _process() after 2.0 second delay")

	# WORKAROUND: Force scene to stay alive by creating a timer
	var timer = Timer.new()
	timer.wait_time = 15.0  # 15 seconds
	timer.one_shot = true
	timer.timeout.connect(_on_timer_timeout)
	add_child(timer)
	timer.start()
	write_log("Started 15-second keep-alive timer")

func _on_timer_timeout():
	write_log("Timer expired - scene has been running for 15 seconds")
	write_log("Tests should have completed by now. Quitting...")
	if log_file:
		log_file.close()
	get_tree().quit()

func _delayed_connect():
	# Wait a moment to ensure all nodes are fully initialized
	write_log("Waiting 0.5 seconds before connecting...")
	await get_tree().create_timer(0.5).timeout
	write_log("Delay complete, now connecting...")
	_connect_to_server()
	write_log("Back from _connect_to_server(), function will now return")
	# Function completes here - does scene crash when async function returns?

func _connect_to_server():
	# This is called after IPCClient's _ready() has completed
	write_log("_connect_to_server() called")
	print("Connecting to IPC server...")
	print("IMPORTANT: Make sure Python IPC server is running!")
	print("  cd python && venv\\Scripts\\activate && python run_ipc_server.py")

	# BREAKPOINT: Uncomment the line below to pause execution here in Godot debugger
	# breakpoint

	write_log("About to call ipc_client.connect_to_server()...")
	write_log("IPCClient node path: " + str(ipc_client.get_path()))
	write_log("IPCClient is in tree: " + str(ipc_client.is_inside_tree()))

	# Re-enable connection now that set_owner() fix is in place
	write_log("Using call_deferred to connect on next frame...")
	ipc_client.call_deferred("connect_to_server", "http://127.0.0.1:5000")
	write_log("call_deferred queued successfully")

	time_since_connect = 0.01  # Start slightly above 0 so _process can increment it
	write_log("Set time_since_connect to 0.01")

	print("Waiting for connection to be established...")
	print("(This may take a moment as the health check is asynchronous)")
	write_log("_connect_to_server() complete")

func _process(delta):
	write_log("DEBUG: _process called, delta=" + str(delta) + " time_since_connect=" + str(time_since_connect))

	# Handle connection after startup delay (avoid race conditions)
	if not connection_initiated:
		startup_delay += delta
		if startup_delay >= 2.0:  # Increased from 0.5 to 2.0 seconds
			write_log("Startup delay complete (2 seconds), initiating connection...")
			connection_initiated = true
			_connect_to_server()
			write_log("Connection initiated from _process()")

	# Track connection timeout
	if not connection_verified and time_since_connect > 0:
		time_since_connect += delta

		# Print periodic status to show we're alive
		if int(time_since_connect) != int(time_since_connect - delta):
			write_log("Waiting... " + str(int(time_since_connect)) + " seconds")

		if time_since_connect > connection_timeout:
			write_log("\n[ERROR] Connection timeout after " + str(connection_timeout) + " seconds")
			write_log("The HTTP request never completed. Possible issues:")
			write_log("1. Python server not responding")
			write_log("2. HTTPRequest configuration issue")
			write_log("3. Network/firewall blocking localhost")
			write_log("\nPress Q to quit")
			time_since_connect = -1  # Prevent repeated messages

	# Start tests once connection is verified
	if connection_verified and not tests_started:
		write_log("\n[SUCCESS] Connected to IPC server!")
		write_log("About to call test_tools()...")
		tests_started = true
		test_tools()
		write_log("test_tools() call completed")

func test_tools():
	print("\n=== Testing Tool Execution ===")
	print("Note: Tool execution is async - responses come via signals")
	print("Check the IPC Response Received section below for actual results\n")

	# Test 1: Move to tool
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
	print("Waiting for async responses from Python server...")
	print("Python server log should show tool executions")
	print("Scene will stay running - press Q to quit when done")
	print("\nWatch for '[IPC Response Received]' messages below...")

func _on_response_received(response: Dictionary):
	write_log("\n[IPC Response Received]")
	write_log("Response: " + str(response))

	# If this is the first response (health check), mark connection as verified
	if not connection_verified and response.has("status"):
		connection_verified = true
		write_log("Connection to IPC server verified!")

func _on_connection_failed(error: String):
	print("\n[IPC Connection Failed]")
	print("Error: ", error)
	print("Make sure Python IPC server is running:")
	print("  cd python")
	print("  venv\\Scripts\\activate")
	print("  python run_ipc_server.py")

func _notification(what):
	if what == NOTIFICATION_WM_CLOSE_REQUEST:
		write_log("NOTIFICATION: Close request received!")
		get_tree().quit()
	elif what == NOTIFICATION_EXIT_TREE:
		write_log("NOTIFICATION: Exiting tree!")
	elif what == NOTIFICATION_PREDELETE:
		write_log("NOTIFICATION: About to be deleted!")

func _input(event):
	if event is InputEventKey and event.pressed:
		if event.keycode == KEY_T:
			test_tools()
		elif event.keycode == KEY_Q:
			print("Quitting...")
			get_tree().quit()
