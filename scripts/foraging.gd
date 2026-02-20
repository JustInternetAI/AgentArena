extends SceneController

## Foraging Benchmark Scene
## Goal: Collect resources (berries, wood, stone) while avoiding hazards (fire, pits)
## Metrics: Resources collected, damage taken, distance traveled, time to completion

# Scene configuration
const MAX_RESOURCES = 7  # Total resources to collect
const FIRE_DAMAGE = 10.0
const PIT_DAMAGE = 25.0
const COLLECTION_RADIUS = 2.0
const HAZARD_RADIUS = 1.5
const CRAFTING_RADIUS = 2.5

# Crafting recipes
const RECIPES = {
	"torch": {"inputs": {"wood": 1, "stone": 1}, "station": "workbench"},
	"shelter": {"inputs": {"wood": 3, "stone": 2}, "station": "anvil"},
	"meal": {"inputs": {"berry": 2}, "station": "workbench"}
}

# Override base class perception settings if needed
# perception_radius = 10.0  # Inherited from SceneController (reduced from 50.0 for exploration)
# line_of_sight_enabled = true  # Inherited from SceneController

# Metrics (inherits start_time and scene_completed from SceneController)
var resources_collected = 0
var damage_taken = 0.0
var distance_traveled = 0.0
var last_position = Vector3.ZERO

# Resource tracking
var active_resources = []
var active_hazards = []

# Crafting tracking
var active_stations = []
var agent_inventory = {}  # resource_type -> count
var items_crafted = {}  # item_name -> count
var total_items_crafted = 0

func _on_scene_ready():
	"""Called after SceneController setup is complete"""
	print("Foraging Benchmark Scene Ready!")

	# Initialize scene-specific data
	_initialize_scene()

	print("Resources available: ", active_resources.size())
	print("Hazards: ", active_hazards.size())
	print("Crafting stations: ", active_stations.size())

	# Store initial agent position for distance tracking
	if agents.size() > 0:
		last_position = agents[0].position

	# Connect to agent damage signals for metrics tracking
	_connect_agent_damage_signals()

func _initialize_scene():
	"""Initialize resource, hazard, and station tracking"""
	active_resources.clear()
	active_hazards.clear()
	active_stations.clear()

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

	# Collect all crafting stations
	var stations_node = get_node_or_null("Stations")
	if stations_node:
		for child in stations_node.get_children():
			if child is CraftingStation:
				active_stations.append({
					"name": child.name,
					"position": child.global_position,
					"type": child.station_type,
					"node": child
				})

func _get_resource_type(resource_name: String) -> String:
	"""Extract resource type from name"""
	if "Berry" in resource_name or "Apple" in resource_name:
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
			# Block stepping if we're waiting for an LLM decision
			if waiting_for_decision:
				print("⏳ Waiting for backend decision... step blocked")
			else:
				simulation_manager.step_simulation()

func _on_scene_started():
	"""Called when simulation starts"""
	print("✓ Foraging benchmark started!")
	# start_time is set by SceneController

func _on_scene_stopped():
	"""Called when simulation stops"""
	print("✓ Foraging benchmark stopped!")
	_print_final_metrics()

func _on_scene_tick(tick: int):
	"""Called each simulation tick after observations sent"""
	# Call base class to request backend decision
	super._on_scene_tick(tick)

	# Update distance traveled (use first agent for single-agent scene)
	if agents.size() > 0:
		var current_position = agents[0].position
		distance_traveled += last_position.distance_to(current_position)
		last_position = current_position

	# Check for resource collection
	_check_resource_collection()

	# NOTE: Hazard damage is now handled by BaseHazard class via Area3D overlaps
	# The agent's damage_taken signal is connected in _connect_agent_damage_signals()

	# Check completion
	if resources_collected >= MAX_RESOURCES:
		_complete_scene()

func _build_observations_for_agent(agent_data: Dictionary) -> Dictionary:
	"""Build foraging-specific observations for an agent"""
	var agent_pos = agent_data.position
	var agent_node = agent_data.agent

	# Find nearby resources (with line-of-sight check)
	var nearby_resources = []
	for resource in active_resources:
		if not resource.collected:
			var dist = agent_pos.distance_to(resource.position)
			# Skip if beyond perception radius
			if dist > perception_radius:
				continue
			# Check line of sight (uses base class method)
			if not has_line_of_sight(agent_node, agent_pos, resource.position, resource.node):
				continue
			nearby_resources.append({
				"name": resource.name,
				"type": resource.type,
				"position": resource.position,
				"distance": dist
			})

	# Find nearby hazards (with line-of-sight check)
	var nearby_hazards = []
	for hazard in active_hazards:
		var dist = agent_pos.distance_to(hazard.position)
		# Skip if beyond perception radius
		if dist > perception_radius:
			continue
		# Check line of sight (uses base class method)
		if not has_line_of_sight(agent_node, agent_pos, hazard.position, hazard.node):
			continue
		nearby_hazards.append({
			"name": hazard.name,
			"type": hazard.type,
			"position": hazard.position,
			"distance": dist
		})

	# Find nearby stations (with line-of-sight check)
	var nearby_stations = []
	for station in active_stations:
		var dist = agent_pos.distance_to(station.position)
		if dist > perception_radius:
			continue
		if not has_line_of_sight(agent_node, agent_pos, station.position, station.node):
			continue
		nearby_stations.append({
			"name": station.name,
			"type": station.type,
			"position": station.position,
			"distance": dist
		})

	# Build observation dictionary
	return {
		"position": agent_pos,
		"health": agent_node.current_health if "current_health" in agent_node else 100.0,
		"max_health": agent_node.max_health if "max_health" in agent_node else 100.0,
		"resources_collected": resources_collected,
		"resources_remaining": MAX_RESOURCES - resources_collected,
		"damage_taken": damage_taken,
		"nearby_resources": nearby_resources,
		"nearby_hazards": nearby_hazards,
		"nearby_stations": nearby_stations,
		"inventory": agent_inventory.duplicate(),
		"recipes": RECIPES,
		"tick": simulation_manager.current_tick
	}

func _on_agent_tool_completed(agent_data: Dictionary, tool_name: String, response: Dictionary):
	"""Handle tool execution completion from agent"""
	print("Foraging: Agent '%s' completed tool '%s': %s" % [agent_data.id, tool_name, response])

func _convert_observation_to_backend_format(agent_data: Dictionary, observation: Dictionary) -> Dictionary:
	"""Override to include crafting data in backend observations"""
	var backend_obs = super._convert_observation_to_backend_format(agent_data, observation)

	# Add stations
	if observation.has("nearby_stations"):
		var stations_list = []
		for station in observation.nearby_stations:
			var st_dict = {
				"name": station.name,
				"type": station.type,
				"distance": station.distance
			}
			if station.position is Vector3:
				st_dict["position"] = [station.position.x, station.position.y, station.position.z]
			else:
				st_dict["position"] = station.position
			stations_list.append(st_dict)
		backend_obs["nearby_stations"] = stations_list

	# Add inventory and recipes under "custom" (not top-level "inventory"
	# which Observation.from_dict expects as list[ItemInfo], not a dict)
	if not backend_obs.has("custom"):
		backend_obs["custom"] = {}
	backend_obs["custom"]["inventory"] = observation.get("inventory", {})

	# Add recipes (static data, always sent so agent has complete info)
	var recipes_for_backend = {}
	for recipe_name in RECIPES:
		var recipe = RECIPES[recipe_name]
		recipes_for_backend[recipe_name] = {
			"inputs": recipe.inputs,
			"station": recipe.station
		}
	backend_obs["custom"]["recipes"] = recipes_for_backend

	return backend_obs

func _execute_backend_decision(decision: Dictionary):
	"""Override to handle craft_item tool locally"""
	if decision.tool == "craft_item":
		var recipe_name = decision.get("params", {}).get("recipe", "")
		var result = craft_item(recipe_name)
		print("  Craft result: %s" % str(result))
		decisions_executed += 1
		return

	# All other tools: use default behavior
	super._execute_backend_decision(decision)

func _connect_agent_damage_signals():
	"""Connect to agent damage_taken signals for metrics tracking"""
	for agent_data in agents:
		var agent = agent_data.agent
		if agent.has_signal("damage_taken"):
			# Use bind to pass agent_data to the callback
			agent.damage_taken.connect(_on_agent_damage_taken.bind(agent_data))
			print("Foraging: Connected to damage_taken signal for agent '%s'" % agent_data.id)

func _on_agent_damage_taken(amount: float, source: Node, source_type: String, agent_data: Dictionary):
	"""Handle damage taken by agent - update metrics"""
	damage_taken += amount

	# Record event
	if event_bus != null:
		event_bus.emit_event("hazard_damage", {
			"hazard_name": String(source.name) if source else "unknown",
			"hazard_type": source_type,
			"damage": amount,
			"position": agent_data.agent.global_position,
			"tick": simulation_manager.current_tick,
			"agent_health": agent_data.agent.current_health if "current_health" in agent_data.agent else 0.0
		})

	print("⚠ Agent took %.1f damage from %s! Total damage: %.1f" % [amount, source_type, damage_taken])

func _check_resource_collection():
	"""Check if agent is near any uncollected resources"""
	if agents.size() == 0:
		return

	var agent_pos = agents[0].position

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

	# Add to agent inventory
	var item_type = resource.type
	agent_inventory[item_type] = agent_inventory.get(item_type, 0) + 1

	# Hide the resource node
	if resource.node != null:
		resource.node.visible = false

	# Record event
	if event_bus != null:
		event_bus.emit_event("resource_collected", {
			"resource_name": resource.name,
			"resource_type": resource.type,
			"position": resource.position,
			"tick": simulation_manager.current_tick
		})

	print("✓ Collected %s (%d/%d) | Inventory: %s" % [resource.name, resources_collected, MAX_RESOURCES, str(agent_inventory)])

func craft_item(recipe_name: String) -> Dictionary:
	"""Attempt to craft an item at a nearby crafting station"""
	# Validate recipe exists
	if not RECIPES.has(recipe_name):
		return {"success": false, "error": "Unknown recipe: %s" % recipe_name}

	var recipe = RECIPES[recipe_name]

	# Check agent is near the correct station type
	if agents.size() == 0:
		return {"success": false, "error": "No agent"}

	var agent_pos = agents[0].position
	var at_station = false
	for station in active_stations:
		if station.type == recipe.station:
			var dist = agent_pos.distance_to(station.position)
			if dist <= CRAFTING_RADIUS:
				at_station = true
				break

	if not at_station:
		return {"success": false, "error": "Not near a %s station (need to be within %.1f units)" % [recipe.station, CRAFTING_RADIUS]}

	# Check ingredients
	for input_item in recipe.inputs.keys():
		var required = recipe.inputs[input_item]
		var have = agent_inventory.get(input_item, 0)
		if have < required:
			return {"success": false, "error": "Missing %s: need %d, have %d" % [input_item, required, have]}

	# Consume ingredients
	for input_item in recipe.inputs.keys():
		agent_inventory[input_item] -= recipe.inputs[input_item]
		if agent_inventory[input_item] <= 0:
			agent_inventory.erase(input_item)

	# Produce output
	agent_inventory[recipe_name] = agent_inventory.get(recipe_name, 0) + 1
	items_crafted[recipe_name] = items_crafted.get(recipe_name, 0) + 1
	total_items_crafted += 1

	# Record event
	if event_bus != null:
		event_bus.emit_event("item_crafted", {
			"item_name": recipe_name,
			"recipe": recipe_name,
			"tick": simulation_manager.current_tick
		})

	print("✓ Crafted %s! Inventory: %s" % [recipe_name, str(agent_inventory)])
	return {"success": true, "item": recipe_name, "inventory": agent_inventory.duplicate()}

func _check_hazard_damage():
	"""Check if agent is near any hazards and apply damage"""
	if agents.size() == 0:
		return

	var agent_pos = agents[0].position

	for hazard in active_hazards:
		var dist = agent_pos.distance_to(hazard.position)
		if dist <= HAZARD_RADIUS:
			_apply_hazard_damage(hazard)

func _apply_hazard_damage(hazard: Dictionary):
	"""Apply damage from a hazard"""
	damage_taken += hazard.damage

	# Record event
	if event_bus != null:
		event_bus.emit_event("hazard_damage", {
			"hazard_name": hazard.name,
			"hazard_type": hazard.type,
			"damage": hazard.damage,
			"position": hazard.position,
			"tick": simulation_manager.current_tick
		})

	print("⚠ Took %d damage from %s! Total damage: %d" % [hazard.damage, hazard.name, damage_taken])

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
	var elapsed_time = get_elapsed_time()

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

	var elapsed_time = get_elapsed_time()

	var status = "RUNNING" if simulation_manager.is_running else "STOPPED"
	if scene_completed:
		status = "COMPLETED"
	elif waiting_for_decision:
		status = "WAITING FOR LLM"

	# Get last decision info
	var last_decision_text = "None"
	if backend_decisions.size() > 0:
		var last_decision = backend_decisions[-1]
		last_decision_text = "%s (tick %d)" % [last_decision.tool, last_decision.tick]

	# Format inventory for display
	var inventory_text = "Empty"
	if agent_inventory.size() > 0:
		var items = []
		for item_type in agent_inventory:
			items.append("%s: %d" % [item_type, agent_inventory[item_type]])
		inventory_text = ", ".join(items)

	metrics_label.text = "Foraging Benchmark [%s]
Tick: %d
Resources Collected: %d/%d
Damage Taken: %.1f
Distance Traveled: %.2f m
Time Elapsed: %.2f s
Efficiency Score: %.1f
Inventory: %s
Items Crafted: %d
Last Backend Decision: %s
Decisions: %d (Executed: %d, Skipped: %d)

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
		_calculate_efficiency_score(),
		inventory_text,
		total_items_crafted,
		last_decision_text,
		backend_decisions.size(),
		decisions_executed,
		decisions_skipped
	]

func _reset_scene():
	"""Reset the scene to initial state"""
	print("Resetting foraging scene...")

	simulation_manager.reset_simulation()

	# Reset metrics
	resources_collected = 0
	damage_taken = 0.0
	distance_traveled = 0.0
	scene_completed = false

	# Reset backend decision tracking (call base class method)
	reset_backend_decisions()

	# Reset crafting state
	agent_inventory.clear()
	items_crafted.clear()
	total_items_crafted = 0

	# Reset agent position
	if agents.size() > 0:
		agents[0].agent.global_position = Vector3.ZERO
		agents[0].agent.global_position.y = 1.0
		last_position = agents[0].agent.global_position

	# Reset resources
	for resource in active_resources:
		resource.collected = false
		if resource.node != null:
			resource.node.visible = true

	print("✓ Scene reset!")
