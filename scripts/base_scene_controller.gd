extends Node3D
class_name SceneController

## Base class for benchmark scenes handling agent perception-action loop
##
## This class provides:
## - Automatic agent discovery and tracking
## - Simulation signal management
## - Per-tick observation distribution to agents
## - Tool completion signal routing
##
## Subclasses must implement:
## - _build_observations_for_agent(agent_data) -> Dictionary
##
## Subclasses can optionally override:
## - _on_scene_ready()
## - _on_scene_started()
## - _on_scene_stopped()
## - _on_scene_tick(tick)
## - _on_agent_tool_completed(agent_data, tool_name, response)

# Scene references (automatically discovered)
@onready var simulation_manager: Node = $SimulationManager
@onready var event_bus: Node = $EventBus
@onready var metrics_label: Label = $UI/MetricsLabel

# Agent tracking
var agents: Array[Dictionary] = []  # Array of {agent: Node, id: String, team: String, position: Vector3}

# Perception configuration (override in subclasses)
var perception_radius: float = 50.0  # Max distance agent can perceive objects
var line_of_sight_enabled: bool = true  # Set to false to disable LOS checks (x-ray vision)
var los_collision_mask: int = 2  # Collision layer for obstacles that block vision

# Exploration tracking
var visibility_tracker: VisibilityTracker = null
var exploration_enabled: bool = true  # Set to false to disable exploration tracking
var world_bounds_min: Vector2 = Vector2(-25, -25)  # Override in subclass for different world sizes
var world_bounds_max: Vector2 = Vector2(25, 25)

# Debug: Observation logging (press F9 to toggle, F10 for verbose mode, F11 for exploration overlay)
var debug_observations: bool = false  # Enable to log observations each tick
var debug_observations_verbose: bool = false  # Show full observation details
var debug_exploration_overlay: bool = false  # Show exploration grid overlay
var _last_observation_cache: Dictionary = {}  # For change detection

# Metrics
var start_time: float = 0.0
var scene_completed: bool = false

# Backend decision tracking
var backend_decisions: Array[Dictionary] = []  # Track all decisions for analysis
var waiting_for_decision := false  # Prevent concurrent requests
var http_request: HTTPRequest = null  # HTTP node for backend communication
var decisions_executed := 0  # Count of executed decisions
var decisions_skipped := 0  # Count of skipped decisions (idle)

func _ready():
	"""Initialize scene controller and discover agents"""
	print("SceneController initializing...")

	# Verify required nodes
	if simulation_manager == null:
		push_error("SimulationManager not found! Ensure scene has SimulationManager node.")
		return

	# Connect simulation signals
	simulation_manager.simulation_started.connect(_on_simulation_started)
	simulation_manager.simulation_stopped.connect(_on_simulation_stopped)
	simulation_manager.tick_advanced.connect(_on_tick_advanced)

	# Discover agents
	_discover_agents()

	print("✓ SceneController discovered %d agent(s)" % agents.size())

	# Setup exploration tracking
	if exploration_enabled:
		_setup_visibility_tracker()

	# Setup backend communication
	_setup_backend_communication()

	# Call scene-specific initialization
	_on_scene_ready()

func _discover_agents():
	"""Auto-discover SimpleAgent nodes in scene"""
	agents.clear()

	# Look for Agents node in scene tree
	var agents_node = get_node_or_null("Agents")
	if agents_node:
		_discover_agents_in_node(agents_node, "single")

	# Look for team-based agents (TeamBlue, TeamRed, etc.)
	for team_name in ["TeamBlue", "TeamRed", "TeamGreen", "TeamYellow"]:
		var team_node = get_node_or_null(team_name)
		if team_node:
			var team_id = team_name.to_lower().replace("team", "")
			_discover_agents_in_node(team_node, team_id)

func _discover_agents_in_node(parent_node: Node, team: String):
	"""Discover agents in a specific parent node"""
	print("[SceneController] Searching for agents in: ", parent_node.name, " (", parent_node.get_children().size(), " children)")
	for child in parent_node.get_children():
		print("  Checking child: ", child.name)
		var has_perceive = child.has_method("perceive")
		var has_call_tool = child.has_method("call_tool")
		print("    - has perceive(): ", has_perceive)
		print("    - has call_tool(): ", has_call_tool)

		if has_perceive and has_call_tool:
			# This is a SimpleAgent (or subclass)
			var agent_id_value = child.agent_id if "agent_id" in child else child.name
			print("    ✓ FOUND AGENT! ID: ", agent_id_value)
			var agent_data = {
				"agent": child,
				"id": agent_id_value,
				"team": team,
				"position": child.global_position
			}
			agents.append(agent_data)

			# Connect to tool completion signal
			child.tool_completed.connect(
				func(tool_name: String, response: Dictionary):
					_on_agent_tool_completed(agent_data, tool_name, response)
			)

			# Create visual if available
			_create_agent_visual(child, agent_data)

			print("  - Discovered agent: %s (team: %s)" % [agent_data.id, team])
		else:
			print("    ✗ Not an agent (missing methods)")

func _create_agent_visual(agent_node: Node, agent_data: Dictionary):
	"""Create visual representation for an agent (if not already present)"""
	# Check if visual already exists as a child (check multiple common names)
	var existing_visual = agent_node.get_node_or_null("AgentVisual")
	if existing_visual == null:
		existing_visual = agent_node.get_node_or_null("MixamoAgentVisual")

	# Calculate common values
	var team_color = _get_team_color(agent_data.team)
	var agent_display_name = agent_data.id if agent_data.team == "single" else "%s_%s" % [agent_data.team, agent_data.id]

	if existing_visual != null:
		# Visual already exists in scene, just configure it
		if existing_visual.has_method("set_team_color"):
			existing_visual.set_team_color(team_color)
		if existing_visual.has_method("set_agent_name"):
			existing_visual.set_agent_name(agent_display_name)
		return

	# Create new visual at runtime (fallback for dynamically created agents)
	# Try Mixamo visual first, fall back to simple visual
	var visual_scene = load("res://scenes/mixamo_agent_visual.tscn")
	if visual_scene == null:
		visual_scene = load("res://scenes/agent_visual.tscn")
	if visual_scene == null:
		return

	var visual_instance = visual_scene.instantiate()
	agent_node.add_child(visual_instance)

	# Set team color
	if visual_instance.has_method("set_team_color"):
		visual_instance.set_team_color(team_color)

	# Set agent name
	if visual_instance.has_method("set_agent_name"):
		visual_instance.set_agent_name(agent_display_name)

func _get_team_color(team: String) -> Color:
	"""Get color for team"""
	match team:
		"blue": return Color(0.2, 0.4, 0.9)
		"red": return Color(0.9, 0.2, 0.2)
		"green": return Color(0.3, 0.8, 0.3)
		"yellow": return Color(0.9, 0.9, 0.2)
		"single": return Color(0.3, 0.8, 0.3)  # Default green for single agents
		_: return Color(0.5, 0.5, 0.5)  # Default gray

func _on_simulation_started():
	"""Handle simulation start"""
	start_time = Time.get_ticks_msec() / 1000.0
	scene_completed = false
	_on_scene_started()

func _on_simulation_stopped():
	"""Handle simulation stop"""
	_on_scene_stopped()

func _on_tick_advanced(tick: int):
	"""Send observations to all agents each tick"""
	# Update agent positions
	for agent_data in agents:
		agent_data.position = agent_data.agent.global_position

	# Update exploration tracking for each agent
	for agent_data in agents:
		_update_exploration(agent_data)

	# Send perception to each agent
	for agent_data in agents:
		var observations = _build_observations_for_agent(agent_data)

		# Debug logging if enabled
		if debug_observations:
			_log_observation_debug(agent_data, observations, tick)

		agent_data.agent.perceive(observations)

	# Call scene-specific tick logic
	_on_scene_tick(tick)

## Virtual methods to override in subclasses

func _on_scene_ready():
	"""Override: Called after SceneController setup is complete"""
	pass

func _on_scene_started():
	"""Override: Called when simulation starts"""
	pass

func _on_scene_stopped():
	"""Override: Called when simulation stops"""
	pass

func _on_scene_tick(_tick: int):
	"""Override: Called each simulation tick after observations sent

	Base implementation requests backend decision. Override in subclass
	and call super._on_scene_tick(tick) to keep backend decision functionality.
	"""
	# Request backend decision (async, doesn't block)
	_request_backend_decision()

func _build_observations_for_agent(agent_data: Dictionary) -> Dictionary:
	"""Override: Build scene-specific observations for an agent

	Args:
		agent_data: Dictionary with {agent: Node, id: String, team: String, position: Vector3}

	Returns:
		Dictionary with observations to send to agent
	"""
	# Default implementation - subclasses should override
	return {
		"agent_id": agent_data.id,
		"team": agent_data.team,
		"position": agent_data.position,
		"tick": simulation_manager.current_tick
	}

func _on_agent_tool_completed(agent_data: Dictionary, tool_name: String, response: Dictionary):
	"""Override: Handle tool completion from an agent

	Args:
		agent_data: Dictionary with {agent: Node, id: String, team: String, position: Vector3}
		tool_name: Name of the tool that was executed
		response: Response dictionary from tool execution
	"""
	# Default implementation - just log
	print("SceneController: Agent '%s' completed tool '%s': %s" % [agent_data.id, tool_name, response])

## Helper methods

func get_agents_by_team(team: String) -> Array[Dictionary]:
	"""Get all agents on a specific team"""
	var team_agents: Array[Dictionary] = []
	for agent_data in agents:
		if agent_data.team == team:
			team_agents.append(agent_data)
	return team_agents

func get_agent_by_id(agent_id: String) -> Dictionary:
	"""Get agent data by ID"""
	for agent_data in agents:
		if agent_data.id == agent_id:
			return agent_data
	return {}

func get_elapsed_time() -> float:
	"""Get elapsed time since simulation start"""
	if simulation_manager and simulation_manager.is_running:
		return (Time.get_ticks_msec() / 1000.0) - start_time
	return 0.0

func has_line_of_sight(agent_node: Node3D, from_pos: Vector3, to_pos: Vector3, target_node: Node3D = null) -> bool:
	"""Check if there's a clear line of sight between two positions.

	Args:
		agent_node: The agent node (excluded from raycast)
		from_pos: Starting position (agent position)
		to_pos: Target position to check visibility
		target_node: Optional target node - if ray hits this, still counts as visible

	Returns:
		true if:
		- No obstacle blocks the path, OR
		- The first thing hit is the target itself (if target_node provided)

	Note: Uses los_collision_mask to determine which layers block vision.
	Set obstacles to collision layer 2 (or your configured layer) to block LOS.
	"""
	if not line_of_sight_enabled:
		return true

	var space_state = get_world_3d().direct_space_state
	if space_state == null:
		return true  # Fallback: assume visible if no physics

	# Raycast from agent eye level to target
	var eye_offset = Vector3(0, 1.0, 0)  # Agent "eyes" are 1 unit above position
	var ray_start = from_pos + eye_offset
	var ray_end = to_pos + Vector3(0, 0.5, 0)  # Target center (slightly above ground)

	var query = PhysicsRayQueryParameters3D.create(ray_start, ray_end)

	# Exclude the agent itself from raycast
	if agent_node is CollisionObject3D:
		query.exclude = [agent_node.get_rid()]

	# Only check against obstacle collision layer
	query.collision_mask = los_collision_mask

	var result = space_state.intersect_ray(query)

	# No hit means clear line of sight
	if result.is_empty():
		return true

	# If we hit the target itself, that counts as visible
	if target_node != null and result.collider == target_node:
		return true

	# Something else is blocking the view
	return false

func is_within_perception(agent_pos: Vector3, target_pos: Vector3) -> bool:
	"""Check if a target is within the agent's perception radius"""
	return agent_pos.distance_to(target_pos) <= perception_radius

## Observation Debug Logging

func _unhandled_input(event):
	"""Handle debug key presses"""
	if event is InputEventKey and event.pressed:
		if event.keycode == KEY_F9:
			debug_observations = not debug_observations
			print("[DEBUG] Observation logging: %s" % ("ON" if debug_observations else "OFF"))
		elif event.keycode == KEY_F10:
			debug_observations_verbose = not debug_observations_verbose
			print("[DEBUG] Verbose mode: %s" % ("ON" if debug_observations_verbose else "OFF"))
		elif event.keycode == KEY_F11:
			_toggle_exploration_overlay()

func _log_observation_debug(agent_data: Dictionary, observations: Dictionary, tick: int):
	"""Log observation data for debugging LOS and visibility."""
	var agent_id = agent_data.id
	var agent_pos = agent_data.position

	# Get previous observation for change detection
	var prev_obs = _last_observation_cache.get(agent_id, {})
	var prev_resources = prev_obs.get("resource_names", [])
	var prev_hazards = prev_obs.get("hazard_names", [])

	# Extract current visible names
	var current_resources = []
	var current_hazards = []

	if observations.has("nearby_resources"):
		for r in observations.nearby_resources:
			current_resources.append(r.name if r is Dictionary else str(r))

	if observations.has("nearby_hazards"):
		for h in observations.nearby_hazards:
			current_hazards.append(h.name if h is Dictionary else str(h))

	# Detect changes
	var gained_resources = []
	var lost_resources = []
	var gained_hazards = []
	var lost_hazards = []

	for obj_name in current_resources:
		if obj_name not in prev_resources:
			gained_resources.append(obj_name)

	for obj_name in prev_resources:
		if obj_name not in current_resources:
			lost_resources.append(obj_name)

	for obj_name in current_hazards:
		if obj_name not in prev_hazards:
			gained_hazards.append(obj_name)

	for obj_name in prev_hazards:
		if obj_name not in current_hazards:
			lost_hazards.append(obj_name)

	# Update cache
	_last_observation_cache[agent_id] = {
		"resource_names": current_resources,
		"hazard_names": current_hazards
	}

	# Print debug output
	var has_changes = gained_resources.size() > 0 or lost_resources.size() > 0 or gained_hazards.size() > 0 or lost_hazards.size() > 0

	if debug_observations_verbose or has_changes:
		print("\n[OBS] Tick %d | Agent: %s | Pos: (%.1f, %.1f, %.1f)" % [
			tick, agent_id, agent_pos.x, agent_pos.y, agent_pos.z
		])

		if debug_observations_verbose:
			print("  Visible: %d resources, %d hazards" % [current_resources.size(), current_hazards.size()])
			if current_resources.size() > 0:
				print("    Resources: %s" % ", ".join(current_resources))
			if current_hazards.size() > 0:
				print("    Hazards: %s" % ", ".join(current_hazards))

		if gained_resources.size() > 0:
			print("  >> GAINED visibility: %s" % ", ".join(gained_resources))
		if lost_resources.size() > 0:
			print("  << LOST visibility: %s" % ", ".join(lost_resources))
		if gained_hazards.size() > 0:
			print("  >> GAINED hazard visibility: %s" % ", ".join(gained_hazards))
		if lost_hazards.size() > 0:
			print("  << LOST hazard visibility: %s" % ", ".join(lost_hazards))

func enable_observation_debug(verbose: bool = false):
	"""Programmatically enable observation debugging."""
	debug_observations = true
	debug_observations_verbose = verbose
	print("[DEBUG] Observation logging enabled (verbose=%s)" % verbose)

func disable_observation_debug():
	"""Programmatically disable observation debugging."""
	debug_observations = false
	print("[DEBUG] Observation logging disabled")

## Exploration tracking

func _setup_visibility_tracker():
	"""Initialize visibility tracker for exploration."""
	visibility_tracker = VisibilityTracker.new()
	visibility_tracker.name = "VisibilityTracker"
	visibility_tracker.cell_size = 2.0  # 2 meter cells
	visibility_tracker.use_raycasting = line_of_sight_enabled
	add_child(visibility_tracker)

	# Set world bounds
	visibility_tracker.set_world_bounds(world_bounds_min, world_bounds_max)
	visibility_tracker.set_los_collision_mask(los_collision_mask)

	print("✓ VisibilityTracker initialized (bounds: %s to %s)" % [world_bounds_min, world_bounds_max])

func _update_exploration(agent_data: Dictionary):
	"""Update exploration tracking for an agent."""
	if visibility_tracker and exploration_enabled:
		visibility_tracker.update_visibility(
			agent_data.position,
			perception_radius,
			agent_data.agent
		)

func get_exploration_summary(agent_pos: Vector3) -> Dictionary:
	"""Get exploration summary for an agent position."""
	if visibility_tracker and exploration_enabled:
		return visibility_tracker.get_exploration_summary(agent_pos)
	return {}

func reset_exploration():
	"""Reset exploration tracking (call on scene reset)."""
	if visibility_tracker:
		visibility_tracker.clear()

func _toggle_exploration_overlay():
	"""Toggle the exploration debug overlay."""
	if visibility_tracker:
		debug_exploration_overlay = visibility_tracker.toggle_debug_visualization()
		print("[DEBUG] Exploration overlay: %s (%.1f%% explored)" % [
			"ON" if debug_exploration_overlay else "OFF",
			visibility_tracker._exploration_percentage
		])
	else:
		print("[DEBUG] Exploration overlay not available (no VisibilityTracker)")

func set_exploration_overlay(enabled: bool):
	"""Programmatically enable/disable exploration overlay."""
	if visibility_tracker:
		visibility_tracker.set_debug_visualization(enabled)
		debug_exploration_overlay = enabled

## Navigation query methods

func query_plan_path(from_pos: Vector3, to_pos: Vector3, avoid_hazards: bool = true) -> Dictionary:
	"""Query path planning using Godot's NavigationServer3D."""
	var nav_map = NavigationServer3D.get_maps()[0] if NavigationServer3D.get_maps().size() > 0 else RID()
	if not nav_map.is_valid():
		return {
			"success": false,
			"blocked": true,
			"reason": "No navigation map available"
		}

	# Get path from NavigationServer3D
	var path = NavigationServer3D.map_get_path(nav_map, from_pos, to_pos, true)

	if path.size() == 0:
		return {
			"success": false,
			"blocked": true,
			"reason": "No path found to target"
		}

	# Calculate total distance
	var total_distance = 0.0
	for i in range(path.size() - 1):
		total_distance += path[i].distance_to(path[i + 1])

	# Convert path to array of arrays for JSON serialization
	var waypoints = []
	for point in path:
		waypoints.append([point.x, point.y, point.z])

	return {
		"success": true,
		"waypoints": waypoints,
		"distance": total_distance,
		"blocked": false,
		"avoid_hazards": avoid_hazards
	}

func query_explore_direction(agent_pos: Vector3, direction: String) -> Dictionary:
	"""Get exploration target in a specific direction."""
	if not visibility_tracker or not exploration_enabled:
		return {
			"success": false,
			"has_unexplored": false,
			"reason": "Exploration tracking not enabled"
		}

	return visibility_tracker.get_unexplored_position_in_direction(agent_pos, direction)

func query_exploration_status(agent_pos: Vector3) -> Dictionary:
	"""Get current exploration status."""
	if not visibility_tracker or not exploration_enabled:
		return {
			"success": false,
			"exploration_percentage": 0.0,
			"frontiers": {},
			"suggested_targets": []
		}

	var summary = visibility_tracker.get_exploration_summary(agent_pos)
	return {
		"success": true,
		"exploration_percentage": summary.get("exploration_percentage", 0.0),
		"frontiers": summary.get("frontiers_by_direction", {}),
		"suggested_targets": summary.get("explore_targets", [])
	}

## Backend decision communication

func _setup_backend_communication():
	"""Initialize HTTP request node for backend communication"""
	http_request = HTTPRequest.new()
	http_request.name = "HTTPRequest"
	http_request.timeout = 10.0
	add_child(http_request)

func _request_backend_decision():
	"""Request decision from backend for the first agent (single-agent scenes)"""
	print("[SceneController] _request_backend_decision called")
	print("  agents.size() = ", agents.size())
	print("  waiting_for_decision = ", waiting_for_decision)
	print("  IPCService exists = ", IPCService != null)
	if IPCService:
		print("  IPCService.is_connected = ", IPCService.is_connected)

	# Only request if we have an agent and not already waiting
	if agents.size() == 0:
		print("  ✗ No agents found, skipping backend request")
		return

	if waiting_for_decision:
		print("  ✗ Already waiting for decision, skipping")
		return

	# Check if backend is connected
	if not IPCService or not IPCService.is_connected:
		print("  ✗ Backend not connected, skipping")
		return

	print("  ✓ Sending observation to backend...")
	waiting_for_decision = true

	# Build observation for first agent (single-agent scene)
	var agent_data = agents[0]
	var observation = _build_observations_for_agent(agent_data)

	# Convert observation to backend format
	var full_observation = _convert_observation_to_backend_format(agent_data, observation)

	# Send to backend
	var json = JSON.stringify(full_observation)
	var headers = ["Content-Type: application/json"]
	var url = "http://127.0.0.1:5000/observe"

	var err = http_request.request(url, headers, HTTPClient.METHOD_POST, json)

	if err != OK:
		push_error("Failed to send observation to backend: %d" % err)
		waiting_for_decision = false
		return

	# Wait for response
	var response = await http_request.request_completed
	_on_decision_received(response)

func _convert_observation_to_backend_format(agent_data: Dictionary, observation: Dictionary) -> Dictionary:
	"""Convert observation dictionary to backend-compatible format

	Override this method in subclasses if you need custom observation formatting.
	Default implementation handles common Vector3 -> [x,y,z] conversions.
	"""
	var backend_obs = {
		"agent_id": agent_data.id,
		"tick": observation.get("tick", simulation_manager.current_tick),
		"position": [observation.position.x, observation.position.y, observation.position.z] if observation.has("position") and observation.position is Vector3 else observation.get("position", [0, 0, 0]),
		"health": observation.get("health", 100.0),
		"max_health": observation.get("max_health", 100.0),
		"nearby_resources": [],
		"nearby_hazards": []
	}

	# Convert resources if present
	if observation.has("nearby_resources"):
		for resource in observation.nearby_resources:
			var res_dict = {
				"name": resource.name,
				"type": resource.type,
				"distance": resource.distance
			}
			# Handle Vector3 position conversion
			if resource.position is Vector3:
				res_dict["position"] = [resource.position.x, resource.position.y, resource.position.z]
			else:
				res_dict["position"] = resource.position
			backend_obs.nearby_resources.append(res_dict)

	# Convert hazards if present
	if observation.has("nearby_hazards"):
		for hazard in observation.nearby_hazards:
			var haz_dict = {
				"name": hazard.name,
				"type": hazard.type,
				"distance": hazard.distance
			}
			# Handle Vector3 position conversion
			if hazard.position is Vector3:
				haz_dict["position"] = [hazard.position.x, hazard.position.y, hazard.position.z]
			else:
				haz_dict["position"] = hazard.position
			backend_obs.nearby_hazards.append(haz_dict)

	# Add exploration data if tracking is enabled
	if exploration_enabled and visibility_tracker:
		var agent_pos = agent_data.position
		var exploration = get_exploration_summary(agent_pos)
		backend_obs["exploration"] = exploration

	return backend_obs

func _on_decision_received(response: Array):
	"""Handle decision response from backend"""
	waiting_for_decision = false

	var _result_code = response[0]
	var response_code = response[1]
	var _response_headers = response[2]
	var body = response[3]

	# Parse response
	if response_code == 200:
		var body_string = body.get_string_from_utf8()
		var json_parser = JSON.new()
		var parse_err = json_parser.parse(body_string)

		if parse_err == OK:
			var decision = json_parser.get_data()
			_log_backend_decision(decision)
		else:
			push_error("JSON parse error: %s" % json_parser.get_error_message())
	else:
		push_error("Backend returned error code: %d" % response_code)

func _log_backend_decision(decision: Dictionary):
	"""Log, store, and execute backend decision"""
	# Add timestamp and tick
	decision["tick"] = simulation_manager.current_tick
	decision["timestamp"] = Time.get_ticks_msec()

	# Store decision
	backend_decisions.append(decision)

	# Log to console
	print("[Backend Decision] Tick %d: %s - %s" % [
		decision.tick,
		decision.tool,
		decision.reasoning
	])

	# Log params if present
	if decision.has("params") and decision.params.size() > 0:
		print("  Params: %s" % decision.params)

	# Execute decision
	_execute_backend_decision(decision)

func _execute_backend_decision(decision: Dictionary):
	"""Execute backend decision by calling agent tool

	Override this in subclass to add custom execution logic or filtering.
	Return false to skip execution (e.g., if scene handles movement differently).
	"""
	if agents.size() == 0:
		return

	var agent_data = agents[0]
	var tool_name = decision.tool
	var params = decision.get("params", {})

	# Skip idle tool (no action needed)
	if tool_name == "idle":
		print("  → Agent idling (no action)")
		decisions_skipped += 1
		return

	# Execute tool via SimpleAgent
	print("  → Executing tool: %s" % tool_name)
	agent_data.agent.call_tool(tool_name, params)
	decisions_executed += 1

func reset_backend_decisions():
	"""Reset backend decision tracking - call this in scene reset handlers"""
	backend_decisions.clear()
	waiting_for_decision = false
	decisions_executed = 0
	decisions_skipped = 0
