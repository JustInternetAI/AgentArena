extends Node
class_name ObservationDebugger

## Debug utility for inspecting agent observations and line-of-sight behavior.
##
## Attach to a SceneController to log observation data each tick.
## Shows what agents see, what's out of range, and what's blocked by LOS.
##
## Usage:
##   1. Attach this script to any node in your scene
##   2. Set scene_controller to your SceneController node
##   3. Press F10 to toggle observation logging
##   4. Press F11 to dump full observation state
##   5. Check output in Godot console or export to JSON file

@export var scene_controller: SceneController
@export var log_to_console: bool = true
@export var log_to_file: bool = false
@export var log_file_path: String = "user://observation_debug.jsonl"

# Tracking
var logging_enabled: bool = false
var observation_history: Array[Dictionary] = []
var max_history_size: int = 100  # Keep last N observations

# Comparison data
var last_visible_resources: Dictionary = {}  # agent_id -> Array of resource names
var last_visible_hazards: Dictionary = {}  # agent_id -> Array of hazard names

func _ready():
	if scene_controller == null:
		# Try to find scene controller as parent
		var parent = get_parent()
		if parent is SceneController:
			scene_controller = parent
		else:
			push_warning("ObservationDebugger: No SceneController assigned. Set scene_controller export.")
			return

	# Hook into tick to capture observations
	if scene_controller.simulation_manager:
		scene_controller.simulation_manager.tick_advanced.connect(_on_tick_for_debug)

	print("ObservationDebugger ready - Press F10 to toggle logging, F11 for full dump")

func _input(event):
	if event is InputEventKey and event.pressed:
		if event.keycode == KEY_F10:
			logging_enabled = not logging_enabled
			print("[ObservationDebugger] Logging %s" % ("ENABLED" if logging_enabled else "DISABLED"))
		elif event.keycode == KEY_F11:
			_dump_full_state()
		elif event.keycode == KEY_F12:
			_export_history_to_file()

func _on_tick_for_debug(tick: int):
	"""Called each tick to capture and analyze observations."""
	if not logging_enabled:
		return

	if scene_controller == null or scene_controller.agents.size() == 0:
		return

	for agent_data in scene_controller.agents:
		var debug_info = _analyze_observation(agent_data, tick)

		if log_to_console:
			_print_observation_debug(debug_info)

		if log_to_file:
			_append_to_log_file(debug_info)

		# Store in history
		observation_history.append(debug_info)
		if observation_history.size() > max_history_size:
			observation_history.pop_front()

func _analyze_observation(agent_data: Dictionary, tick: int) -> Dictionary:
	"""Analyze what an agent can see and why."""
	var agent_pos = agent_data.position
	var agent_node = agent_data.agent
	var agent_id = agent_data.id

	var debug_info = {
		"tick": tick,
		"agent_id": agent_id,
		"agent_position": _vec3_to_array(agent_pos),
		"perception_radius": scene_controller.perception_radius,
		"los_enabled": scene_controller.line_of_sight_enabled,
		"visible_resources": [],
		"out_of_range_resources": [],
		"los_blocked_resources": [],
		"visible_hazards": [],
		"out_of_range_hazards": [],
		"los_blocked_hazards": [],
		"changes": {}
	}

	# Analyze resources
	if scene_controller.has_method("_get_active_resources"):
		var resources = scene_controller._get_active_resources()
	elif "active_resources" in scene_controller:
		var resources = scene_controller.active_resources
		for resource in resources:
			if resource.get("collected", false):
				continue

			var dist = agent_pos.distance_to(resource.position)
			var resource_info = {
				"name": resource.name,
				"type": resource.type,
				"position": _vec3_to_array(resource.position),
				"distance": dist
			}

			# Check distance first
			if dist > scene_controller.perception_radius:
				resource_info["reason"] = "beyond_perception_radius"
				debug_info.out_of_range_resources.append(resource_info)
				continue

			# Check LOS
			var has_los = scene_controller.has_line_of_sight(agent_node, agent_pos, resource.position, resource.node)
			if not has_los:
				resource_info["reason"] = "blocked_by_obstacle"
				debug_info.los_blocked_resources.append(resource_info)
				continue

			# Visible!
			debug_info.visible_resources.append(resource_info)

	# Analyze hazards
	if "active_hazards" in scene_controller:
		var hazards = scene_controller.active_hazards
		for hazard in hazards:
			var dist = agent_pos.distance_to(hazard.position)
			var hazard_info = {
				"name": hazard.name,
				"type": hazard.type,
				"position": _vec3_to_array(hazard.position),
				"distance": dist
			}

			# Check distance first
			if dist > scene_controller.perception_radius:
				hazard_info["reason"] = "beyond_perception_radius"
				debug_info.out_of_range_hazards.append(hazard_info)
				continue

			# Check LOS
			var has_los = scene_controller.has_line_of_sight(agent_node, agent_pos, hazard.position, hazard.node)
			if not has_los:
				hazard_info["reason"] = "blocked_by_obstacle"
				debug_info.los_blocked_hazards.append(hazard_info)
				continue

			# Visible!
			debug_info.visible_hazards.append(hazard_info)

	# Detect changes from last observation
	var current_visible_names = []
	for r in debug_info.visible_resources:
		current_visible_names.append(r.name)

	var last_visible = last_visible_resources.get(agent_id, [])

	var newly_visible = []
	for name in current_visible_names:
		if name not in last_visible:
			newly_visible.append(name)

	var lost_visibility = []
	for name in last_visible:
		if name not in current_visible_names:
			lost_visibility.append(name)

	debug_info.changes = {
		"newly_visible_resources": newly_visible,
		"lost_visibility_resources": lost_visibility
	}

	# Same for hazards
	var current_visible_hazard_names = []
	for h in debug_info.visible_hazards:
		current_visible_hazard_names.append(h.name)

	var last_visible_h = last_visible_hazards.get(agent_id, [])

	var newly_visible_h = []
	for name in current_visible_hazard_names:
		if name not in last_visible_h:
			newly_visible_h.append(name)

	var lost_visibility_h = []
	for name in last_visible_h:
		if name not in current_visible_hazard_names:
			lost_visibility_h.append(name)

	debug_info.changes["newly_visible_hazards"] = newly_visible_h
	debug_info.changes["lost_visibility_hazards"] = lost_visibility_h

	# Update tracking
	last_visible_resources[agent_id] = current_visible_names
	last_visible_hazards[agent_id] = current_visible_hazard_names

	return debug_info

func _print_observation_debug(debug_info: Dictionary):
	"""Print formatted observation debug to console."""
	print("\n" + "=".repeat(60))
	print("[OBSERVATION DEBUG] Tick %d - Agent: %s" % [debug_info.tick, debug_info.agent_id])
	print("  Position: %s" % debug_info.agent_position)
	print("  Perception radius: %.1f | LOS enabled: %s" % [debug_info.perception_radius, debug_info.los_enabled])
	print("-".repeat(60))

	# Visible resources
	print("  VISIBLE RESOURCES (%d):" % debug_info.visible_resources.size())
	for r in debug_info.visible_resources:
		print("    + %s (%s) at %.1f units" % [r.name, r.type, r.distance])

	# Out of range
	if debug_info.out_of_range_resources.size() > 0:
		print("  OUT OF RANGE (%d):" % debug_info.out_of_range_resources.size())
		for r in debug_info.out_of_range_resources:
			print("    - %s at %.1f units (max: %.1f)" % [r.name, r.distance, debug_info.perception_radius])

	# LOS blocked
	if debug_info.los_blocked_resources.size() > 0:
		print("  LOS BLOCKED (%d):" % debug_info.los_blocked_resources.size())
		for r in debug_info.los_blocked_resources:
			print("    X %s at %.1f units (blocked by obstacle)" % [r.name, r.distance])

	# Hazards
	print("  VISIBLE HAZARDS (%d):" % debug_info.visible_hazards.size())
	for h in debug_info.visible_hazards:
		print("    ! %s (%s) at %.1f units" % [h.name, h.type, h.distance])

	# Changes
	if debug_info.changes.newly_visible_resources.size() > 0:
		print("  >> NEWLY VISIBLE: %s" % debug_info.changes.newly_visible_resources)
	if debug_info.changes.lost_visibility_resources.size() > 0:
		print("  << LOST VISIBILITY: %s" % debug_info.changes.lost_visibility_resources)

	print("=".repeat(60))

func _dump_full_state():
	"""Dump complete observation state for all tracked data."""
	print("\n" + "#".repeat(70))
	print("# FULL OBSERVATION STATE DUMP")
	print("#".repeat(70))

	if scene_controller == null:
		print("No scene controller!")
		return

	print("\nScene Configuration:")
	print("  perception_radius: %.1f" % scene_controller.perception_radius)
	print("  line_of_sight_enabled: %s" % scene_controller.line_of_sight_enabled)
	print("  los_collision_mask: %d" % scene_controller.los_collision_mask)

	print("\nAgents:")
	for agent_data in scene_controller.agents:
		print("  - %s at %s" % [agent_data.id, agent_data.position])

	if "active_resources" in scene_controller:
		print("\nAll Resources:")
		for r in scene_controller.active_resources:
			var status = "COLLECTED" if r.get("collected", false) else "ACTIVE"
			print("  - %s (%s) at %s [%s]" % [r.name, r.type, r.position, status])

	if "active_hazards" in scene_controller:
		print("\nAll Hazards:")
		for h in scene_controller.active_hazards:
			print("  - %s (%s) at %s" % [h.name, h.type, h.position])

	print("\nObservation History: %d entries" % observation_history.size())

	print("#".repeat(70))

func _export_history_to_file():
	"""Export observation history to JSONL file."""
	var file = FileAccess.open(log_file_path, FileAccess.WRITE)
	if file == null:
		push_error("Failed to open log file: %s" % log_file_path)
		return

	for entry in observation_history:
		file.store_line(JSON.stringify(entry))

	file.close()
	print("[ObservationDebugger] Exported %d observations to %s" % [observation_history.size(), log_file_path])

func _append_to_log_file(debug_info: Dictionary):
	"""Append single observation to log file."""
	var file = FileAccess.open(log_file_path, FileAccess.READ_WRITE)
	if file == null:
		file = FileAccess.open(log_file_path, FileAccess.WRITE)
	if file == null:
		return

	file.seek_end()
	file.store_line(JSON.stringify(debug_info))
	file.close()

func _vec3_to_array(v: Vector3) -> Array:
	return [v.x, v.y, v.z]

# Public API for external access

func get_last_observation(agent_id: String) -> Dictionary:
	"""Get the most recent observation for an agent."""
	for i in range(observation_history.size() - 1, -1, -1):
		if observation_history[i].agent_id == agent_id:
			return observation_history[i]
	return {}

func get_visibility_changes(agent_id: String, last_n_ticks: int = 10) -> Array:
	"""Get visibility changes for an agent over recent ticks."""
	var changes = []
	var count = 0
	for i in range(observation_history.size() - 1, -1, -1):
		var obs = observation_history[i]
		if obs.agent_id == agent_id:
			if obs.changes.newly_visible_resources.size() > 0 or obs.changes.lost_visibility_resources.size() > 0:
				changes.append({
					"tick": obs.tick,
					"gained": obs.changes.newly_visible_resources,
					"lost": obs.changes.lost_visibility_resources
				})
			count += 1
			if count >= last_n_ticks:
				break
	return changes

func is_resource_visible(agent_id: String, resource_name: String) -> bool:
	"""Check if a specific resource is currently visible to an agent."""
	var obs = get_last_observation(agent_id)
	if obs.is_empty():
		return false
	for r in obs.visible_resources:
		if r.name == resource_name:
			return true
	return false

func get_blocked_resources(agent_id: String) -> Array:
	"""Get list of resources blocked by LOS for an agent."""
	var obs = get_last_observation(agent_id)
	if obs.is_empty():
		return []
	return obs.los_blocked_resources
