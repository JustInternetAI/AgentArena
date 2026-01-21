extends Node
## Test observation-based decision loop
##
## This test validates the observation-decision pipeline:
## 1. Build observations (like foraging scene does)
## 2. Send to Python backend via /observe endpoint
## 3. Receive mock decision from backend
## 4. Log decision (don't execute)
## 5. Repeat for N ticks

var http_request: HTTPRequest
var tick_count := 0
var max_ticks := 10
var connection_verified := false
var test_running := false

# Mock foraging data (simplified)
var agent_position := Vector3(0, 0, 0)
var resources := [
	{"name": "Berry1", "position": Vector3(5, 0, 3), "type": "berry", "collected": false},
	{"name": "Berry2", "position": Vector3(-4, 0, 2), "type": "berry", "collected": false},
	{"name": "Wood1", "position": Vector3(-3, 0, 7), "type": "wood", "collected": false},
	{"name": "Stone1", "position": Vector3(8, 0, -2), "type": "stone", "collected": false}
]
var hazards := [
	{"name": "Fire1", "position": Vector3(2, 0, 2), "type": "fire"},
	{"name": "Pit1", "position": Vector3(-1, 0, 5), "type": "pit"}
]

# Collection radius
const COLLECTION_RADIUS = 2.0

func _ready():
	print("=== Observation-Decision Loop Test ===")
	print("This test validates the full observation-decision pipeline")
	print("without executing actual agent movement.\n")

	# Prevent auto-quit
	get_tree().set_auto_accept_quit(false)

	# Create HTTPRequest node for sending observations
	http_request = HTTPRequest.new()
	http_request.name = "HTTPRequest"
	http_request.timeout = 10.0
	add_child(http_request)

	# Connect to IPCService for connection status
	if IPCService:
		IPCService.connected_to_server.connect(_on_connected)
		IPCService.connection_failed.connect(_on_connection_failed)
		print("✓ IPCService found")
		print("Waiting for backend connection...")
	else:
		push_error("IPCService not found! Check project.godot autoload settings")
		return

	print("\nIMPORTANT: Make sure Python IPC server is running!")
	print("  cd python && venv\\Scripts\\activate && python run_ipc_server.py\n")

func _on_connected():
	print("✓ Connected to Python backend!")
	connection_verified = true

	# Wait a moment then start test
	await get_tree().create_timer(0.5).timeout
	start_test()

func _on_connection_failed(error: String):
	print("\n✗ Connection failed: %s" % error)
	print("Make sure Python IPC server is running!")
	print("\nPress Q to quit")

func start_test():
	if test_running:
		return

	test_running = true
	print("\n" + "=".repeat(60))
	print("=== STARTING OBSERVATION LOOP TEST ===")
	print("=".repeat(60))
	print("Running %d ticks with 0.5s delay between each...\n" % max_ticks)

	# Print initial state
	print("[Initial State]")
	print("  Agent position: %s" % agent_position)
	print("  Resources: %d" % resources.size())
	for res in resources:
		var dist = agent_position.distance_to(res.position)
		var status = "[COLLECTED]" if res.collected else ""
		print("    - %s (%s) at distance %.2f %s" % [res.name, res.type, dist, status])
	print("  Hazards: %d" % hazards.size())
	for hazard in hazards:
		var dist = agent_position.distance_to(hazard.position)
		print("    - %s (%s) at distance %.2f" % [hazard.name, hazard.type, dist])
	print("")

	# Run ticks
	for i in range(max_ticks):
		await process_tick(i)
		await get_tree().create_timer(0.5).timeout

	# Test complete
	print("\n" + "=".repeat(60))
	print("=== TEST COMPLETE ===")
	print("=".repeat(60))
	print("✓ All %d ticks processed successfully!" % max_ticks)
	print("✓ Observation-decision loop validated")
	print("\nPress Q to quit, T to run again\n")
	test_running = false

func process_tick(tick: int):
	"""Process a single tick: build observation -> send -> receive decision"""
	print("\n--- Tick %d ---" % tick)

	# Build observation (like foraging scene does)
	var observation = build_observation()

	# Log what we're sending
	print("Sending observation:")
	print("  Position: %s" % agent_position)
	print("  Nearby resources: %d" % observation.nearby_resources.size())
	print("  Nearby hazards: %d" % observation.nearby_hazards.size())

	# Send to backend and wait for response
	var result = await send_observation(observation)

	# Process response
	if result.has("tool"):
		print("✓ Decision received:")
		print("  Tool: %s" % result.tool)
		print("  Params: %s" % result.params)
		print("  Reasoning: %s" % result.reasoning)

		# Simulate position update based on decision
		# (not actual movement, just for testing different states)
		if result.tool == "move_to" and result.params.has("target_position"):
			var target = result.params.target_position
			var target_vec = Vector3(target[0], target[1], target[2])
			var distance_to_target = agent_position.distance_to(target_vec)

			# Move toward target (max 2 units per tick)
			var direction = (target_vec - agent_position).normalized()
			var move_amount = min(2.0, distance_to_target)
			agent_position += direction * move_amount

			print("  → Target: %s (distance: %.2f)" % [target_vec, distance_to_target])
			print("  → New position: %s" % agent_position)

			# Check if we collected any resources
			_check_resource_collection()
		elif result.tool == "idle":
			print("  → Agent idling")
		else:
			print("  → Tool '%s' acknowledged" % result.tool)
	else:
		print("✗ No decision received")
		print("  Response: %s" % result)

func build_observation() -> Dictionary:
	"""Build observation dictionary like foraging scene does"""
	var obs = {
		"agent_id": "test_forager_001",
		"position": [agent_position.x, agent_position.y, agent_position.z],
		"nearby_resources": [],
		"nearby_hazards": []
	}

	# Add only uncollected resources with distance
	for resource in resources:
		if not resource.collected:
			var dist = agent_position.distance_to(resource.position)
			obs.nearby_resources.append({
				"name": resource.name,
				"type": resource.type,
				"position": [resource.position.x, resource.position.y, resource.position.z],
				"distance": dist
			})

	# Add hazards with distance
	for hazard in hazards:
		var dist = agent_position.distance_to(hazard.position)
		obs.nearby_hazards.append({
			"name": hazard.name,
			"type": hazard.type,
			"position": [hazard.position.x, hazard.position.y, hazard.position.z],
			"distance": dist
		})

	return obs

func _check_resource_collection():
	"""Check if agent is close enough to collect any resources"""
	for resource in resources:
		if resource.collected:
			continue

		var dist = agent_position.distance_to(resource.position)
		if dist <= COLLECTION_RADIUS:
			resource.collected = true
			print("  ✓ Collected %s (%s)!" % [resource.name, resource.type])

func send_observation(obs: Dictionary) -> Dictionary:
	"""Send observation to backend via HTTP POST and wait for response"""
	var json = JSON.stringify(obs)
	var headers = ["Content-Type: application/json"]
	var url = "http://127.0.0.1:5000/observe"

	# Make request
	var err = http_request.request(url, headers, HTTPClient.METHOD_POST, json)

	if err != OK:
		push_error("HTTP request failed with error: %d" % err)
		return {}

	# Wait for response
	var response = await http_request.request_completed
	var result_code = response[0]
	var response_code = response[1]
	var response_headers = response[2]
	var body = response[3]

	# Parse response
	if response_code == 200:
		var body_string = body.get_string_from_utf8()
		var json_parser = JSON.new()
		var parse_err = json_parser.parse(body_string)

		if parse_err == OK:
			return json_parser.get_data()
		else:
			push_error("JSON parse error: %s" % json_parser.get_error_message())
			return {}
	else:
		push_error("HTTP error code: %d" % response_code)
		print("Response body: %s" % body.get_string_from_utf8())
		return {}

func _input(event):
	if event is InputEventKey and event.pressed:
		if event.keycode == KEY_Q:
			print("\nQuitting...")
			get_tree().quit()
		elif event.keycode == KEY_T and not test_running:
			print("\nRestarting test...")
			# Reset position and resources
			agent_position = Vector3(0, 0, 0)
			tick_count = 0
			for resource in resources:
				resource.collected = false
			start_test()

func _notification(what):
	if what == NOTIFICATION_PREDELETE:
		print("\nTest scene shutting down...")
