extends BaseAgent
## SimpleAgent - Godot agent wrapper for Python-driven decision making
##
## This GDScript handles the Godot side of agent behavior:
## - Movement and animation in the game world
## - Connection to IPC services for Python communication
## - Tool execution via ToolRegistryService
##
## All decision-making logic (memory, planning, reasoning) lives in Python.
## This script just provides the "body" that executes Python's decisions.
##
## Usage:
##   var agent = SimpleAgent.new()
##   agent.agent_id = "foraging_agent_001"  # Must match Python registration
##   add_child(agent)
##   agent.call_tool("move_to", {"target_position": [10, 0, 5]})

signal tick_completed(response: Dictionary)

@export var auto_connect: bool = true
@export var move_speed: float = 5.0  # Units per second

var _cpp_agent: Agent
var _target_position: Vector3 = Vector3.ZERO
var _is_moving: bool = false
var _movement_speed: float = 1.0

# Stuck detection for movement completion (Issue #71)
var _movement_start_tick: int = 0
var _position_samples: Array[Vector3] = []
var _stuck_check_timer: int = 0
const STUCK_SAMPLE_INTERVAL: int = 20   # sample every ~0.33s at 60fps
const STUCK_SAMPLE_COUNT: int = 5       # need 5 samples before deciding
const STUCK_THRESHOLD: float = 0.3      # total movement threshold
var _current_move_tool: String = ""     # "move_to" or "explore_direction"

# Collision deduplication - prevent reporting same collision multiple times per tick
var _reported_collisions_this_tick: Dictionary = {}  # object_name -> true
var _last_collision_report_tick: int = -1

func _ready():
	super._ready()  # Call BaseAgent._ready() for ID generation if needed

	print("SimpleAgent: Initializing agent_id: ", agent_id)

	# Create the C++ Agent node
	_cpp_agent = Agent.new()
	_cpp_agent.name = "AgentCore"
	_cpp_agent.set_agent_id(agent_id)
	add_child(_cpp_agent)

	if auto_connect:
		_connect_to_services()

	print("SimpleAgent '", agent_id, "' ready")

func _connect_to_services():
	"""Connect to the global autoload services"""
	# Wait for autoload services to be ready
	await get_tree().process_frame

	# Connect to IPCService signals
	if IPCService:
		IPCService.tool_response.connect(_on_tool_response)
		IPCService.tick_response.connect(_on_tick_response)
		print("SimpleAgent '", agent_id, "': Connected to IPCService")
	else:
		push_error("SimpleAgent: IPCService not found!")

	# The C++ Agent doesn't need a direct ToolRegistry reference anymore
	# since we route through the autoload services
	print("SimpleAgent '", agent_id, "': Connected to services")

func call_tool(tool_name: String, parameters: Dictionary = {}) -> Dictionary:
	"""
	Execute a tool for this agent using the global ToolRegistryService.
	Returns immediately with a pending status - actual response comes via signal.
	"""
	print("[SimpleAgent] ==== call_tool START ====")
	print("[SimpleAgent] Agent ID: ", agent_id)
	print("[SimpleAgent] Tool: ", tool_name)
	print("[SimpleAgent] Parameters: ", parameters)
	print("[SimpleAgent] Current position: ", global_position)
	print("[SimpleAgent] Current _is_moving: ", _is_moving)

	if not ToolRegistryService:
		push_error("SimpleAgent: ToolRegistryService not found!")
		return {"success": false, "error": "ToolRegistryService not available"}

	# Handle movement locally
	if tool_name == "move_to" and parameters.has("target_position"):
		var target = parameters.target_position
		print("[SimpleAgent] move_to detected! Target value: ", target, " type: ", typeof(target))
		# Convert array to Vector3 if needed
		if target is Array and target.size() >= 3:
			_target_position = Vector3(target[0], target[1], target[2])
			print("[SimpleAgent] ✓ Converted array to Vector3: ", _target_position)
		elif target is Vector3:
			_target_position = target
			print("[SimpleAgent] ✓ Using Vector3 directly: ", _target_position)
		else:
			print("[SimpleAgent] ✗ Invalid target_position format!")
			return {"success": false, "error": "Invalid target_position"}

		_movement_speed = parameters.get("speed", 1.0)
		_is_moving = true
		_movement_start_tick = _get_current_tick()
		_position_samples.clear()
		_stuck_check_timer = 0
		_current_move_tool = "move_to"
		print("[SimpleAgent] ✓ Movement configured:")
		print("[SimpleAgent]   - _target_position: ", _target_position)
		print("[SimpleAgent]   - _movement_speed: ", _movement_speed)
		print("[SimpleAgent]   - _is_moving: ", _is_moving)
		print("[SimpleAgent]   - Distance to target: ", global_position.distance_to(_target_position))

	# Handle navigation query tools locally (they need Godot data)
	if tool_name == "plan_path":
		var scene_controller = _get_scene_controller()
		if scene_controller:
			var target = parameters.get("target_position", [0, 0, 0])
			var target_vec = Vector3(target[0], target[1], target[2]) if target is Array else target
			var avoid = parameters.get("avoid_hazards", true)
			var path_result = scene_controller.query_plan_path(global_position, target_vec, avoid)
			print("[SimpleAgent] plan_path result: ", path_result)
			return path_result
		return {"success": false, "error": "No scene controller"}

	if tool_name == "explore_direction":
		var scene_controller = _get_scene_controller()
		if scene_controller:
			var direction = parameters.get("direction", "north")
			var explore_result = scene_controller.query_explore_direction(global_position, direction)
			print("[SimpleAgent] explore_direction result: ", explore_result)
			# Actually move toward the exploration target
			if explore_result.get("success", false) and explore_result.has("target_position"):
				var target = explore_result.target_position
				if target is Vector3:
					_target_position = target
				elif target is Array and target.size() >= 3:
					_target_position = Vector3(target[0], target[1], target[2])
				_is_moving = true
				_movement_start_tick = _get_current_tick()
				_position_samples.clear()
				_stuck_check_timer = 0
				_current_move_tool = "explore_direction"
				print("[SimpleAgent] ✓ Exploring %s, moving to: %s" % [direction, _target_position])
			return explore_result
		return {"success": false, "error": "No scene controller"}

	if tool_name == "get_exploration_status":
		var scene_controller = _get_scene_controller()
		if scene_controller:
			var status_result = scene_controller.query_exploration_status(global_position)
			print("[SimpleAgent] get_exploration_status result: ", status_result)
			return status_result
		return {"success": false, "error": "No scene controller"}

	# Handle crafting tools via scene controller
	if tool_name == "craft_item":
		var scene_controller = _get_scene_controller()
		if scene_controller and scene_controller.has_method("craft_item"):
			var recipe = parameters.get("recipe", "")
			var craft_result = scene_controller.craft_item(recipe)
			print("[SimpleAgent] craft_item result: ", craft_result)
			return craft_result
		return {"success": false, "error": "Scene does not support crafting"}

	if tool_name == "get_recipes":
		var scene_controller = _get_scene_controller()
		if scene_controller and "RECIPES" in scene_controller:
			return {"success": true, "recipes": scene_controller.RECIPES}
		return {"success": false, "error": "No recipes available"}

	var result = ToolRegistryService.execute_tool(agent_id, tool_name, parameters)
	print("[SimpleAgent] ToolRegistryService.execute_tool returned: ", result)
	print("[SimpleAgent] ==== call_tool END ====")
	return result

func perceive(_observations: Dictionary) -> void:
	"""
	Receive observations from SceneController.
	SimpleAgent doesn't need to do anything with observations locally since
	they are sent directly to the backend via _request_backend_decision.
	This method exists to satisfy the SceneController's agent discovery.
	"""
	# Observations are handled by SceneController and sent to backend
	pass

func send_tick(tick: int, perceptions: Array) -> void:
	"""
	Send a tick update for this agent using the global IPCService.
	Actual response comes via signal.
	"""
	if not IPCService:
		push_error("SimpleAgent: IPCService not found!")
		return

	IPCService.send_tick(agent_id, tick, perceptions)

func _physics_process(_delta):
	"""Handle physics-based movement each frame"""
	if not _is_moving:
		velocity = Vector3.ZERO
		return

	var distance = global_position.distance_to(_target_position)

	# Stop if close enough (0.5 unit tolerance for physics-based movement)
	if distance < 0.5:
		print("[SimpleAgent._physics_process] ✓ Reached target! Final position: ", global_position)
		_is_moving = false
		velocity = Vector3.ZERO
		# Emit tool_completed with success (Issue #71)
		var duration = _get_current_tick() - _movement_start_tick
		tool_completed.emit(_current_move_tool, {
			"success": true,
			"final_position": [global_position.x, global_position.y, global_position.z],
			"target_position": [_target_position.x, _target_position.y, _target_position.z],
			"duration_ticks": duration
		})
		return

	# Calculate movement direction and velocity
	var direction = (_target_position - global_position).normalized()
	velocity = direction * _movement_speed * move_speed

	# Use move_and_slide for physics-based movement with collision
	move_and_slide()

	# Check for collisions after movement
	if get_slide_collision_count() > 0:
		for i in range(get_slide_collision_count()):
			var collision = get_slide_collision(i)
			_on_collision(collision)

	# Stuck detection: sample position periodically and check total movement (Issue #71)
	_stuck_check_timer += 1
	if _stuck_check_timer >= STUCK_SAMPLE_INTERVAL:
		_stuck_check_timer = 0
		_position_samples.append(global_position)

		if _position_samples.size() >= STUCK_SAMPLE_COUNT:
			# Sum total movement across samples
			var total_movement: float = 0.0
			for idx in range(_position_samples.size() - 1):
				total_movement += _position_samples[idx].distance_to(_position_samples[idx + 1])

			if total_movement < STUCK_THRESHOLD:
				print("[SimpleAgent._physics_process] Agent stuck! Total movement: %.3f < %.3f" % [total_movement, STUCK_THRESHOLD])
				_is_moving = false
				velocity = Vector3.ZERO
				var duration = _get_current_tick() - _movement_start_tick
				tool_completed.emit(_current_move_tool, {
					"success": false,
					"error": "stuck",
					"final_position": [global_position.x, global_position.y, global_position.z],
					"target_position": [_target_position.x, _target_position.y, _target_position.z],
					"distance_remaining": distance,
					"duration_ticks": duration
				})
				return

			# Keep only the last sample for next window
			_position_samples = [_position_samples[-1]]

	# Debug print every 60 frames (~1 second)
	if Engine.get_process_frames() % 60 == 0:
		print("[SimpleAgent._physics_process] Moving...")
		print("  Current position: ", global_position)
		print("  Target position: ", _target_position)
		print("  Distance remaining: ", distance)
		print("  Velocity: ", velocity)

func _on_collision(collision: KinematicCollision3D):
	"""Handle collision with obstacle - emit signal and report to Python backend"""
	var collider = collision.get_collider()
	var collision_point = collision.get_position()
	var collision_normal = collision.get_normal()
	var collider_name = collider.name if collider else "obstacle"
	var current_tick = _get_current_tick()

	# Reset collision tracking if tick has changed
	if current_tick != _last_collision_report_tick:
		_reported_collisions_this_tick.clear()
		_last_collision_report_tick = current_tick

	# Skip if we already reported this collision this tick
	if _reported_collisions_this_tick.has(collider_name):
		return

	# Mark as reported
	_reported_collisions_this_tick[collider_name] = true

	print("[SimpleAgent] Collision detected!")
	print("  Collider: ", collider_name)
	print("  Position: ", collision_point)
	print("  Normal: ", collision_normal)

	# Emit signal for scene controller to handle
	collision_detected.emit(collision)

	# Report to Python backend via IPC
	_report_experience_to_backend({
		"agent_id": agent_id,
		"tick": current_tick,
		"event_type": "collision",
		"description": "Movement blocked by " + collider_name,
		"position": [collision_point.x, collision_point.y, collision_point.z],
		"object_name": collider_name
	})

func _report_experience_to_backend(data: Dictionary):
	"""Send experience event to Python backend."""
	if not IPCService or not IPCService.is_backend_connected():
		return

	# Use HTTPRequest for async POST
	var http = HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(_on_experience_reported.bind(http))

	var json = JSON.stringify(data)
	var headers = ["Content-Type: application/json"]
	var error = http.request("http://127.0.0.1:5000/experience", headers, HTTPClient.METHOD_POST, json)
	if error != OK:
		print("[SimpleAgent] Failed to send experience to backend: ", error)
		http.queue_free()

func _on_experience_reported(_result, _response_code, _headers, _body, http: HTTPRequest):
	"""Clean up HTTP request after experience is reported"""
	http.queue_free()

func _get_current_tick() -> int:
	"""Get current simulation tick from SimulationManager"""
	var controller = _get_scene_controller()
	if controller and controller.simulation_manager:
		return controller.simulation_manager.current_tick
	return 0

func _get_scene_controller() -> Node:
	"""Get reference to the scene controller managing this agent."""
	# Try common scene controller paths
	var paths = [
		"/root/ForagingScene",
		"/root/Main",
		"/root/ArenaScene"
	]
	for path in paths:
		var controller = get_tree().root.get_node_or_null(path.trim_prefix("/root/"))
		if controller and controller.has_method("query_plan_path"):
			return controller

	# Fallback: search parent nodes
	var parent = get_parent()
	while parent:
		if parent.has_method("query_plan_path"):
			return parent
		parent = parent.get_parent()

	return null

# Signal handlers
func _on_tool_response(response_agent_id: String, tool_name: String, response: Dictionary):
	"""Handle tool response from IPCService"""
	# Only process responses for this agent
	if response_agent_id == agent_id:
		print("SimpleAgent '", agent_id, "' received tool response for '", tool_name, "': ", response)
		tool_completed.emit(tool_name, response)

func _on_tick_response(response_agent_id: String, response: Dictionary):
	"""Handle tick response from IPCService"""
	# Only process responses for this agent
	if response_agent_id == agent_id:
		print("SimpleAgent '", agent_id, "' received tick response: ", response)
		tick_completed.emit(response)
