extends Node

var log_file: FileAccess

func write_log(message: String):
	if log_file:
		log_file.store_line(message)
		log_file.flush()
	print(message)

func _ready():
	log_file = FileAccess.open("user://test_gdextension_nodes.log", FileAccess.WRITE)
	write_log("=== GDExtension Nodes Test - " + Time.get_datetime_string_from_system() + " ===")

	# Add a timer to keep the scene alive
	var timer = Timer.new()
	timer.wait_time = 10.0
	timer.one_shot = true
	timer.timeout.connect(_on_timeout)
	add_child(timer)
	timer.start()
	write_log("Started 10-second timer")

	# Defer the actual tests
	call_deferred("run_tests")

func run_tests():
	write_log("\n--- Test 1: Creating IPCClient ---")
	var ipc_client = IPCClient.new()
	write_log("IPCClient created successfully")
	ipc_client.name = "IPCClient"
	ipc_client.server_url = "http://127.0.0.1:5000"
	add_child(ipc_client)
	write_log("IPCClient added as child")

	await get_tree().create_timer(0.5).timeout
	write_log("Waited 0.5 seconds after IPCClient")

	write_log("\n--- Test 2: Creating ToolRegistry ---")
	var tool_registry = ToolRegistry.new()
	write_log("ToolRegistry created successfully")
	tool_registry.name = "ToolRegistry"
	add_child(tool_registry)
	write_log("ToolRegistry added as child")

	await get_tree().create_timer(0.5).timeout
	write_log("Waited 0.5 seconds after ToolRegistry")

	write_log("\n--- Test 3: Connecting ToolRegistry to IPCClient ---")
	tool_registry.set_ipc_client(ipc_client)
	write_log("ToolRegistry connected to IPCClient")

	await get_tree().create_timer(0.5).timeout
	write_log("Waited 0.5 seconds after connection")

	write_log("\n--- Test 4: Creating Agent ---")
	var agent = Agent.new()
	write_log("Agent created successfully")
	agent.name = "TestAgent"
	agent.agent_id = "test_agent_001"
	add_child(agent)
	write_log("Agent added as child")

	await get_tree().create_timer(0.5).timeout
	write_log("Waited 0.5 seconds after Agent")

	write_log("\n--- Test 5: Connecting Agent to ToolRegistry ---")
	agent.set_tool_registry(tool_registry)
	write_log("Agent connected to ToolRegistry")

	await get_tree().create_timer(0.5).timeout
	write_log("Waited 0.5 seconds after agent connection")

	write_log("\n=== ALL TESTS PASSED ===")
	write_log("All GDExtension nodes created and connected successfully!")

func _process(delta):
	write_log("_process called, delta=" + str(delta))

func _on_timeout():
	write_log("\nTimer expired - 10 seconds elapsed")
	if log_file:
		log_file.close()
	get_tree().quit()
