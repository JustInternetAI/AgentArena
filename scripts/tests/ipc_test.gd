extends Node

# Test script to demonstrate IPC communication between Godot and Python

var simulation_manager: SimulationManager
var ipc_client: IPCClient
var agent: Agent
var tick_count: int = 0

func _ready():
	print("=== IPC Test Starting ===")

	# Create simulation manager
	simulation_manager = SimulationManager.new()
	simulation_manager.name = "SimulationManager"
	add_child(simulation_manager)

	# Create IPC client
	ipc_client = IPCClient.new()
	ipc_client.name = "IPCClient"
	ipc_client.server_url = "http://127.0.0.1:5000"
	add_child(ipc_client)

	# Create test agent
	agent = Agent.new()
	agent.name = "TestAgent"
	agent.agent_id = "agent_001"
	add_child(agent)

	# Connect signals
	ipc_client.response_received.connect(_on_response_received)
	ipc_client.connection_failed.connect(_on_connection_failed)
	simulation_manager.tick_advanced.connect(_on_tick_advanced)

	# Wait a frame for nodes to initialize
	await get_tree().process_frame

	# Connect to Python server
	print("Connecting to IPC server...")
	ipc_client.connect_to_server("http://127.0.0.1:5000")

	# Wait for connection
	await get_tree().create_timer(1.0).timeout

	if ipc_client.is_server_connected():
		print("Connected to IPC server!")
		start_test()
	else:
		print("Failed to connect. Make sure Python IPC server is running:")
		print("  cd python && python run_ipc_server.py")

func start_test():
	print("Starting test simulation...")
	simulation_manager.start_simulation()

	# Run for 10 ticks
	for i in range(10):
		await get_tree().create_timer(0.5).timeout
		simulation_manager.step_simulation()

func _on_tick_advanced(tick: int):
	print("\n--- Tick ", tick, " ---")

	# Create perception data for agent
	var perceptions = []
	var perception = {
		"agent_id": agent.agent_id,
		"tick": tick,
		"position": [randf() * 10.0, 0.0, randf() * 10.0],
		"rotation": [0.0, randf() * 360.0, 0.0],
		"velocity": [0.0, 0.0, 0.0],
		"visible_entities": [],
		"inventory": [],
		"health": 100.0,
		"energy": 100.0,
		"custom_data": {}
	}
	perceptions.append(perception)

	# Send tick request to Python
	print("Sending tick request to Python...")
	ipc_client.send_tick_request(tick, perceptions)

func _on_response_received(response: Dictionary):
	print("Received response from Python:")
	print("  Tick: ", response.get("tick", -1))
	print("  Actions: ", response.get("actions", []))
	print("  Metrics: ", response.get("metrics", {}))

	# Execute actions
	var actions = response.get("actions", [])
	for action in actions:
		var agent_id = action.get("agent_id", "")
		var tool = action.get("tool", "")
		var params = action.get("params", {})
		var reasoning = action.get("reasoning", "")

		print("  Agent ", agent_id, " action: ", tool)
		if reasoning:
			print("    Reasoning: ", reasoning)

	tick_count += 1
	if tick_count >= 10:
		print("\n=== Test Complete ===")
		simulation_manager.stop_simulation()
		get_tree().quit()

func _on_connection_failed(error: String):
	print("Connection failed: ", error)
	print("\nMake sure the Python IPC server is running:")
	print("  cd python")
	print("  python run_ipc_server.py")
	get_tree().quit()
