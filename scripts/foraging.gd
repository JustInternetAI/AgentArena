extends Node3D

## Foraging Benchmark Scene
## Goal: Collect resources (berries, wood, stone) while avoiding hazards (fire, pits)
## Metrics: Resources collected, damage taken, distance traveled, time to completion

@onready var simulation_manager = $SimulationManager
@onready var event_bus = $EventBus
@onready var agent = $Agents/Agent1
@onready var metrics_label = $UI/MetricsLabel

# Scene configuration
const MAX_RESOURCES = 7  # Total resources to collect
const FIRE_DAMAGE = 10.0
const PIT_DAMAGE = 25.0
const COLLECTION_RADIUS = 2.0
const HAZARD_RADIUS = 1.5

# Metrics
var resources_collected = 0
var damage_taken = 0.0
var distance_traveled = 0.0
var start_time = 0.0
var last_position = Vector3.ZERO
var scene_completed = false

# Resource tracking
var active_resources = []
var active_hazards = []

func _ready():
	print("Foraging Benchmark Scene Ready!")

	# Verify C++ nodes are loaded
	if simulation_manager == null or agent == null:
		push_error("GDExtension nodes not found! Extension may not be loaded.")
		return

	# Agent is now a SimpleAgent (auto-connects to services)
	last_position = agent.global_position

	# Create visual representation for agent
	_create_agent_visual(agent, "Forager", Color(0.3, 0.8, 0.3))  # Green color

	print("✓ SimpleAgent will use autoload services (IPCService and ToolRegistryService)")

	# Connect simulation signals
	simulation_manager.simulation_started.connect(_on_simulation_started)
	simulation_manager.simulation_stopped.connect(_on_simulation_stopped)
	simulation_manager.tick_advanced.connect(_on_tick_advanced)

	# Connect SimpleAgent signals (note: these come from SimpleAgent, not the C++ core)
	agent.tool_completed.connect(_on_tool_completed)

	# Initialize resources and hazards (tools already registered by ToolRegistryService)
	_initialize_scene()

	print("Resources available: ", active_resources.size())
	print("Hazards: ", active_resources.size())

func _initialize_scene():
	"""Initialize resource and hazard tracking"""
	active_resources.clear()
	active_hazards.clear()

	# Collect all resources
	var resources_node = $Resources
	for child in resources_node.get_children():
		if child is Area3D:
			active_resources.append({
				"name": child.name,
				"position": child.global_position,
				"type": _get_resource_type(child.name),
				"collected": false,
				"node": child
			})

	# Collect all hazards
	var hazards_node = $Hazards
	for child in hazards_node.get_children():
		if child is Area3D:
			active_hazards.append({
				"name": child.name,
				"position": child.global_position,
				"type": _get_hazard_type(child.name),
				"damage": FIRE_DAMAGE if "Fire" in child.name else PIT_DAMAGE,
				"node": child
			})

func _get_resource_type(resource_name: String) -> String:
	"""Extract resource type from name"""
	if "Berry" in resource_name:
		return "berry"
	elif "Wood" in resource_name:
		return "wood"
	elif "Stone" in resource_name:
		return "stone"
	return "unknown"

func _get_hazard_type(hazard_name: String) -> String:
	"""Extract hazard type from name"""
	if "Fire" in hazard_name:
		return "fire"
	elif "Pit" in hazard_name:
		return "pit"
	return "unknown"

func _process(_delta):
	_update_metrics_ui()

func _input(event):
	if simulation_manager == null:
		return

	# Control simulation with keyboard
	if event is InputEventKey and event.pressed:
		if event.keycode == KEY_SPACE:
			if simulation_manager.is_running:
				simulation_manager.stop_simulation()
			else:
				simulation_manager.start_simulation()
		elif event.keycode == KEY_R:
			_reset_scene()
		elif event.keycode == KEY_S:
			simulation_manager.step_simulation()

func _on_simulation_started():
	print("✓ Foraging benchmark started!")
	start_time = Time.get_ticks_msec() / 1000.0
	scene_completed = false

func _on_simulation_stopped():
	print("✓ Foraging benchmark stopped!")
	_print_final_metrics()

func _on_tick_advanced(tick: int):
	# Update distance traveled
	var current_position = agent.global_position
	distance_traveled += last_position.distance_to(current_position)
	last_position = current_position

	# Check for resource collection
	_check_resource_collection()

	# Check for hazard damage
	_check_hazard_damage()

	# Send perception to agent
	_send_perception_to_agent()

	# Check completion
	if resources_collected >= MAX_RESOURCES:
		_complete_scene()

func _check_resource_collection():
	"""Check if agent is near any uncollected resources"""
	var agent_pos = agent.global_position

	for resource in active_resources:
		if resource.collected:
			continue

		var dist = agent_pos.distance_to(resource.position)
		if dist <= COLLECTION_RADIUS:
			_collect_resource(resource)

func _collect_resource(resource: Dictionary):
	"""Collect a resource and update metrics"""
	if resource.collected:
		return

	resource.collected = true
	resources_collected += 1

	# Hide the resource node
	if resource.node != null:
		resource.node.visible = false

	# Record event
	if event_bus != null:
		event_bus.emit_event({
			"type": "resource_collected",
			"resource_name": resource.name,
			"resource_type": resource.type,
			"position": resource.position,
			"tick": simulation_manager.current_tick
		})

	print("✓ Collected %s (%d/%d)" % [resource.name, resources_collected, MAX_RESOURCES])

func _check_hazard_damage():
	"""Check if agent is near any hazards and apply damage"""
	var agent_pos = agent.global_position

	for hazard in active_hazards:
		var dist = agent_pos.distance_to(hazard.position)
		if dist <= HAZARD_RADIUS:
			_apply_hazard_damage(hazard)

func _apply_hazard_damage(hazard: Dictionary):
	"""Apply damage from a hazard"""
	damage_taken += hazard.damage

	# Record event
	if event_bus != null:
		event_bus.emit_event({
			"type": "hazard_damage",
			"hazard_name": hazard.name,
			"hazard_type": hazard.type,
			"damage": hazard.damage,
			"position": hazard.position,
			"tick": simulation_manager.current_tick
		})

	print("⚠ Took %d damage from %s! Total damage: %d" % [hazard.damage, hazard.name, damage_taken])

func _send_perception_to_agent():
	"""Send world observations to the agent"""
	var agent_pos = agent.global_position

	# Find nearby entities
	var nearby_resources = []
	for resource in active_resources:
		if not resource.collected:
			var dist = agent_pos.distance_to(resource.position)
			nearby_resources.append({
				"name": resource.name,
				"type": resource.type,
				"position": resource.position,
				"distance": dist
			})

	var nearby_hazards = []
	for hazard in active_hazards:
		var dist = agent_pos.distance_to(hazard.position)
		nearby_hazards.append({
			"name": hazard.name,
			"type": hazard.type,
			"position": hazard.position,
			"distance": dist
		})

	# Build observation dictionary
	var observations = {
		"position": agent_pos,
		"resources_collected": resources_collected,
		"resources_remaining": MAX_RESOURCES - resources_collected,
		"damage_taken": damage_taken,
		"nearby_resources": nearby_resources,
		"nearby_hazards": nearby_hazards,
		"tick": simulation_manager.current_tick
	}

	# Send to agent
	agent.perceive(observations)

func _on_tool_completed(tool_name: String, response: Dictionary):
	"""Handle tool execution completion from SimpleAgent"""
	print("Tool '", tool_name, "' completed: ", response)

func _complete_scene():
	"""Complete the benchmark scene"""
	if scene_completed:
		return

	scene_completed = true
	simulation_manager.stop_simulation()

	print("\n" + "=".repeat(50))
	print("✓ FORAGING BENCHMARK COMPLETED!")
	_print_final_metrics()
	print("=".repeat(50))

func _print_final_metrics():
	"""Print final benchmark metrics"""
	var elapsed_time = (Time.get_ticks_msec() / 1000.0) - start_time

	print("\nFinal Metrics:")
	print("  Resources Collected: %d/%d" % [resources_collected, MAX_RESOURCES])
	print("  Damage Taken: %.1f" % damage_taken)
	print("  Distance Traveled: %.2f meters" % distance_traveled)
	print("  Time Elapsed: %.2f seconds" % elapsed_time)
	print("  Efficiency Score: %.2f" % _calculate_efficiency_score())

func _calculate_efficiency_score() -> float:
	"""Calculate overall efficiency score"""
	if resources_collected == 0:
		return 0.0

	# Score based on: resources collected, minimal damage, efficient pathing
	var resource_score = float(resources_collected) / float(MAX_RESOURCES) * 100.0
	var damage_penalty = min(damage_taken, 100.0)  # Cap penalty at 100
	var efficiency = resource_score - damage_penalty

	return max(efficiency, 0.0)

func _update_metrics_ui():
	"""Update the metrics display"""
	if metrics_label == null:
		return

	var elapsed_time = 0.0
	if simulation_manager.is_running:
		elapsed_time = (Time.get_ticks_msec() / 1000.0) - start_time

	var status = "RUNNING" if simulation_manager.is_running else "STOPPED"
	if scene_completed:
		status = "COMPLETED"

	metrics_label.text = "Foraging Benchmark [%s]
Tick: %d
Resources Collected: %d/%d
Damage Taken: %.1f
Distance Traveled: %.2f m
Time Elapsed: %.2f s
Efficiency Score: %.1f

Press SPACE to start/stop
Press R to reset
Press S to step" % [
		status,
		simulation_manager.current_tick,
		resources_collected,
		MAX_RESOURCES,
		damage_taken,
		distance_traveled,
		elapsed_time,
		_calculate_efficiency_score()
	]

func _create_agent_visual(agent_node: Node, agent_name: String, color: Color):
	"""Create visual representation for an agent"""
	var visual_scene = load("res://scenes/agent_visual.tscn")
	if visual_scene == null:
		push_warning("Could not load agent_visual.tscn")
		return

	var visual_instance = visual_scene.instantiate()
	agent_node.add_child(visual_instance)

	if visual_instance.has_method("set_team_color"):
		visual_instance.set_team_color(color)
	if visual_instance.has_method("set_agent_name"):
		visual_instance.set_agent_name(agent_name)

	print("✓ Created visual for: ", agent_name)

func _reset_scene():
	"""Reset the scene to initial state"""
	print("Resetting foraging scene...")

	simulation_manager.reset_simulation()

	# Reset metrics
	resources_collected = 0
	damage_taken = 0.0
	distance_traveled = 0.0
	start_time = 0.0
	scene_completed = false

	# Reset agent position
	agent.global_position = Vector3.ZERO
	agent.global_position.y = 1.0
	last_position = agent.global_position

	# Reset resources
	for resource in active_resources:
		resource.collected = false
		if resource.node != null:
			resource.node.visible = true

	print("✓ Scene reset!")
