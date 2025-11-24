extends Node
## Test script for the autoload service architecture
##
## This test demonstrates the new architecture where:
## - IPCService and ToolRegistryService are global singletons
## - SimpleAgent is a lightweight wrapper that uses those services
## - Services persist across scene changes
## - No manual setup required - everything is automatic!

var agents: Array[Node] = []
var test_phase := 0
var tests_completed := false

func _ready():
	print("=== Autoload Services Test ===")
	print("This test uses the global IPCService and ToolRegistryService")
	print("No manual setup required - services are already running!\n")

	# Verify services are available
	if not IPCService:
		push_error("IPCService not found! Check project.godot autoload settings")
		return

	if not ToolRegistryService:
		push_error("ToolRegistryService not found! Check project.godot autoload settings")
		return

	print("✓ IPCService found")
	print("✓ ToolRegistryService found")

	# Wait a frame for services to fully initialize
	await get_tree().process_frame

	print("✓ Available tools: ", ToolRegistryService.get_available_tools())
	print("")

	# Connect to service signals
	IPCService.connected_to_server.connect(_on_server_connected)
	IPCService.connection_failed.connect(_on_connection_failed)

	# Keep scene alive
	set_process(true)

	# Create a timeout timer to prevent hanging forever
	var timeout_timer = Timer.new()
	timeout_timer.wait_time = 30.0
	timeout_timer.one_shot = true
	timeout_timer.timeout.connect(_on_connection_timeout)
	add_child(timeout_timer)
	timeout_timer.start()

	# IPCService auto-connects in its _ready() - just wait for the signal
	print("\nWaiting for IPCService to connect to Python backend...")
	print("(Make sure Python IPC server is running: cd python && venv\\Scripts\\activate && python run_ipc_server.py)")
	print("Timeout: 30 seconds\n")

func _on_server_connected():
	print("\n✓ Connected to Python backend!")
	print("Starting tests in 1 second...\n")
	await get_tree().create_timer(1.0).timeout
	run_tests()

func _on_connection_failed(error: String):
	push_error("Failed to connect to Python backend: " + error)
	print("\nMake sure the Python IPC server is running:")
	print("  cd python")
	print("  venv\\Scripts\\activate")
	print("  python run_ipc_server.py")
	print("\nPress Q to quit")

func _on_connection_timeout():
	push_error("Connection timeout after 30 seconds!")
	print("\nThe HTTP request never completed. This could mean:")
	print("  1. Python server is not running")
	print("  2. HTTPRequest is crashing (the old bug)")
	print("  3. Network/firewall issue")
	print("\nCheck if scene is still running (you should be able to press Q to quit)")
	print("If Q works, the HTTPRequest crash is fixed!")
	print("\nPress Q to quit")

func run_tests():
	print("=== Creating Test Agents ===\n")

	# Test 1: Create multiple agents - they all share the same services!
	for i in range(3):
		var agent_script = load("res://scripts/simple_agent.gd")
		var agent = agent_script.new()
		agent.agent_id = "test_agent_%03d" % i
		agent.name = "Agent" + str(i)

		# Connect to agent's signals
		agent.tool_completed.connect(_on_agent_tool_completed.bind(agent.agent_id))

		add_child(agent)
		agents.append(agent)

		print("Created agent: ", agent.agent_id)

	print("\nAll agents created! They all use the same global IPCService and ToolRegistryService")
	print("This means:")
	print("  - Single persistent connection to Python backend")
	print("  - Services survive scene changes")
	print("  - No setup overhead per agent\n")

	# Wait a moment for agents to initialize
	await get_tree().create_timer(0.5).timeout

	print("=== Testing Tool Execution ===\n")

	# Test different tools with different agents
	test_phase = 1

	print("[Test 1] Agent 0: move_to")
	agents[0].call_tool("move_to", {
		"target_position": [10.0, 0.0, 5.0],
		"speed": 1.5
	})

	await get_tree().create_timer(0.5).timeout

	print("\n[Test 2] Agent 1: pickup_item")
	agents[1].call_tool("pickup_item", {
		"item_id": "sword_001"
	})

	await get_tree().create_timer(0.5).timeout

	print("\n[Test 3] Agent 2: get_inventory")
	agents[2].call_tool("get_inventory", {})

	await get_tree().create_timer(0.5).timeout

	print("\n[Test 4] Agent 0: navigate_to")
	agents[0].call_tool("navigate_to", {
		"target_position": [20.0, 0.0, 10.0]
	})

	await get_tree().create_timer(0.5).timeout

	print("\n[Test 5] Agent 1: stop_movement")
	agents[1].call_tool("stop_movement", {})

	print("\n=== All Tests Sent ===")
	print("Waiting for responses from Python backend...")
	print("(Watch for '[Agent Tool Completed]' messages below)")
	print("\nPress Q to quit when done\n")

	tests_completed = true

func _process(delta):
	# Just keep scene alive - actual work happens via signals
	pass

func _on_agent_tool_completed(tool_name: String, response: Dictionary, agent_id: String):
	print("\n[Agent Tool Completed]")
	print("  Agent: ", agent_id)
	print("  Tool: ", tool_name)
	print("  Response: ", response)

func _input(event):
	if event is InputEventKey and event.pressed:
		if event.keycode == KEY_Q:
			print("\nQuitting...")
			get_tree().quit()
		elif event.keycode == KEY_T and tests_completed:
			print("\nRe-running tests...")
			run_tests()

func _notification(what):
	if what == NOTIFICATION_PREDELETE:
		print("\nTest scene shutting down...")
		print("Note: IPCService and ToolRegistryService remain active!")
		print("They are global singletons and will persist until Godot closes.")
