extends Node3D

## Crafting Chain Benchmark Scene
## Goal: Craft complex items from base resources using crafting stations
## Metrics: Items crafted, recipe efficiency, resource waste, crafting time

@onready var simulation_manager = $SimulationManager
@onready var event_bus = $EventBus
@onready var tool_registry = $ToolRegistry
@onready var ipc_client = $IPCClient
@onready var agent = $Agents/Agent1
@onready var metrics_label = $UI/MetricsLabel

# Scene configuration
const COLLECTION_RADIUS = 2.0
const CRAFTING_RADIUS = 2.5
const TARGET_ITEM = "iron_sword"  # Final item to craft

# Crafting recipes
const RECIPES = {
	"iron_ingot": {
		"inputs": {"iron_ore": 1, "coal": 1},
		"station": "Furnace",
		"time": 3.0
	},
	"iron_rod": {
		"inputs": {"iron_ingot": 1},
		"station": "Anvil",
		"time": 2.0
	},
	"wooden_handle": {
		"inputs": {"wood": 2},
		"station": "Workbench",
		"time": 2.0
	},
	"iron_sword": {
		"inputs": {"iron_rod": 1, "wooden_handle": 1},
		"station": "Anvil",
		"time": 4.0
	}
}

# Metrics
var items_crafted = {}  # Dict of item_name: count
var total_items_crafted = 0
var resources_collected = 0
var resources_used = 0
var resources_wasted = 0
var crafting_attempts = 0
var successful_crafts = 0
var start_time = 0.0
var total_crafting_time = 0.0
var scene_completed = false

# Inventory
var agent_inventory = {}

# Scene elements
var base_resources = []
var crafting_stations = []
var current_craft = null  # Current crafting operation

func _ready():
	print("Crafting Chain Benchmark Scene Ready!")

	# Verify C++ nodes
	if simulation_manager == null or agent == null:
		push_error("GDExtension nodes not found!")
		return

	# Initialize agent
	agent.agent_id = "crafting_agent_001"

	# Connect tool system (IPCClient → ToolRegistry → Agent)
	if ipc_client != null and tool_registry != null and agent != null:
		tool_registry.set_ipc_client(ipc_client)
		agent.set_tool_registry(tool_registry)
		print("✓ Tool execution system connected!")
	else:
		push_warning("Tool execution system not fully available")

	# Connect signals
	simulation_manager.simulation_started.connect(_on_simulation_started)
	simulation_manager.simulation_stopped.connect(_on_simulation_stopped)
	simulation_manager.tick_advanced.connect(_on_tick_advanced)
	agent.action_decided.connect(_on_agent_action_decided)

	# Register tools
	_register_tools()

	# Initialize scene
	_initialize_scene()

	print("Base resources: ", base_resources.size())
	print("Crafting stations: ", crafting_stations.size())
	print("Recipes available: ", RECIPES.keys())

func _register_tools():
	"""Register available tools for the agent"""
	if tool_registry == null:
		return

	# Movement
	tool_registry.register_tool("move_to", {
		"name": "move_to",
		"description": "Move to a target position",
		"parameters": {
			"target_x": {"type": "float"},
			"target_y": {"type": "float"},
			"target_z": {"type": "float"}
		}
	})

	# Collection
	tool_registry.register_tool("collect", {
		"name": "collect",
		"description": "Collect a nearby resource",
		"parameters": {
			"resource_name": {"type": "string"}
		}
	})

	# Crafting
	tool_registry.register_tool("craft", {
		"name": "craft",
		"description": "Craft an item at a nearby station",
		"parameters": {
			"item_name": {"type": "string"},
			"station_name": {"type": "string"}
		}
	})

	# Query
	tool_registry.register_tool("query_inventory", {
		"name": "query_inventory",
		"description": "Check current inventory",
		"parameters": {}
	})

	tool_registry.register_tool("query_recipes", {
		"name": "query_recipes",
		"description": "Get available crafting recipes",
		"parameters": {}
	})

func _initialize_scene():
	"""Initialize resources and stations"""
	base_resources.clear()
	crafting_stations.clear()
	agent_inventory.clear()
	items_crafted.clear()

	# Collect base resources
	var resources_node = $BaseResources
	for child in resources_node.get_children():
		if child is Area3D:
			base_resources.append({
				"name": child.name,
				"position": child.global_position,
				"type": _get_resource_type(child.name),
				"collected": false,
				"node": child
			})

	# Collect crafting stations
	var stations_node = $CraftingStations
	for child in stations_node.get_children():
		if child is Area3D:
			crafting_stations.append({
				"name": child.name,
				"position": child.global_position,
				"type": child.name.to_lower(),
				"node": child
			})

func _get_resource_type(resource_name: String) -> String:
	"""Extract resource type from name"""
	if "IronOre" in resource_name:
		return "iron_ore"
	elif "Wood" in resource_name:
		return "wood"
	elif "Coal" in resource_name:
		return "coal"
	return "unknown"

func _process(_delta):
	_update_metrics_ui()

	# Update crafting progress
	if current_craft != null:
		_update_crafting()

func _input(event):
	if simulation_manager == null:
		return

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
		elif event.keycode == KEY_I:
			_print_inventory()

func _on_simulation_started():
	print("✓ Crafting chain benchmark started!")
	start_time = Time.get_ticks_msec() / 1000.0
	scene_completed = false

func _on_simulation_stopped():
	print("✓ Crafting chain benchmark stopped!")
	_print_final_metrics()

func _on_tick_advanced(tick: int):
	# Check for resource collection
	_check_resource_collection()

	# Send perception to agent
	_send_perception_to_agent()

	# Check completion
	if agent_inventory.get(TARGET_ITEM, 0) > 0:
		_complete_scene()

func _check_resource_collection():
	"""Auto-collect nearby resources"""
	var agent_pos = agent.global_position

	for resource in base_resources:
		if resource.collected:
			continue

		var dist = agent_pos.distance_to(resource.position)
		if dist <= COLLECTION_RADIUS:
			_collect_resource(resource)

func _collect_resource(resource: Dictionary):
	"""Collect a resource and add to inventory"""
	if resource.collected:
		return

	resource.collected = true
	resources_collected += 1

	# Add to inventory
	var item_type = resource.type
	agent_inventory[item_type] = agent_inventory.get(item_type, 0) + 1

	# Hide the node
	if resource.node != null:
		resource.node.visible = false

	# Record event
	if event_bus != null:
		event_bus.emit_event({
			"type": "resource_collected",
			"resource_name": resource.name,
			"resource_type": resource.type,
			"tick": simulation_manager.current_tick
		})

	print("✓ Collected %s (Inventory: %s)" % [resource.name, str(agent_inventory)])

func craft_item(item_name: String, station_name: String) -> bool:
	"""Attempt to craft an item"""
	crafting_attempts += 1

	# Check if recipe exists
	if not RECIPES.has(item_name):
		print("✗ Unknown recipe: %s" % item_name)
		return false

	var recipe = RECIPES[item_name]

	# Check if at correct station
	var agent_pos = agent.global_position
	var at_station = false
	for station in crafting_stations:
		if station.name.to_lower() == station_name.to_lower():
			var dist = agent_pos.distance_to(station.position)
			if dist <= CRAFTING_RADIUS:
				at_station = true
				break

	if not at_station:
		print("✗ Not at correct crafting station: %s" % station_name)
		return false

	# Check if correct station type
	if recipe.station.to_lower() != station_name.to_lower():
		print("✗ Wrong station. Need %s, at %s" % [recipe.station, station_name])
		return false

	# Check if we have required materials
	for input_item in recipe.inputs.keys():
		var required_amount = recipe.inputs[input_item]
		var current_amount = agent_inventory.get(input_item, 0)
		if current_amount < required_amount:
			print("✗ Missing materials for %s. Need %d %s, have %d" %
				[item_name, required_amount, input_item, current_amount])
			return false

	# Start crafting
	current_craft = {
		"item_name": item_name,
		"recipe": recipe,
		"start_time": Time.get_ticks_msec() / 1000.0,
		"duration": recipe.time
	}

	# Consume materials
	for input_item in recipe.inputs.keys():
		var amount = recipe.inputs[input_item]
		agent_inventory[input_item] -= amount
		resources_used += amount

	print("⚙ Crafting %s at %s (%.1fs)..." % [item_name, station_name, recipe.time])
	return true

func _update_crafting():
	"""Update current crafting operation"""
	if current_craft == null:
		return

	var elapsed = (Time.get_ticks_msec() / 1000.0) - current_craft.start_time
	if elapsed >= current_craft.duration:
		_complete_craft()

func _complete_craft():
	"""Complete the current craft"""
	if current_craft == null:
		return

	var item_name = current_craft.item_name

	# Add crafted item to inventory
	agent_inventory[item_name] = agent_inventory.get(item_name, 0) + 1

	# Update metrics
	items_crafted[item_name] = items_crafted.get(item_name, 0) + 1
	total_items_crafted += 1
	successful_crafts += 1
	total_crafting_time += current_craft.duration

	# Record event
	if event_bus != null:
		event_bus.emit_event({
			"type": "item_crafted",
			"item_name": item_name,
			"tick": simulation_manager.current_tick
		})

	print("✓ Crafted %s! (Inventory: %s)" % [item_name, str(agent_inventory)])

	current_craft = null

func _send_perception_to_agent():
	"""Send world observations to agent"""
	var agent_pos = agent.global_position

	# Find nearby resources
	var nearby_resources = []
	for resource in base_resources:
		if not resource.collected:
			var dist = agent_pos.distance_to(resource.position)
			nearby_resources.append({
				"name": resource.name,
				"type": resource.type,
				"position": resource.position,
				"distance": dist
			})

	# Find nearby stations
	var nearby_stations = []
	for station in crafting_stations:
		var dist = agent_pos.distance_to(station.position)
		nearby_stations.append({
			"name": station.name,
			"type": station.type,
			"position": station.position,
			"distance": dist
		})

	# Build observation
	var observations = {
		"position": agent_pos,
		"inventory": agent_inventory.duplicate(),
		"nearby_resources": nearby_resources,
		"nearby_stations": nearby_stations,
		"recipes": RECIPES,
		"target_item": TARGET_ITEM,
		"crafting": current_craft != null,
		"tick": simulation_manager.current_tick
	}

	agent.perceive(observations)

func _on_agent_action_decided(action):
	"""Handle agent action"""
	if action is Dictionary and action.has("tool"):
		var tool_name = action.tool
		var params = action.get("params", {})

		if tool_name == "craft":
			craft_item(params.get("item_name", ""), params.get("station_name", ""))

func _complete_scene():
	"""Complete the benchmark"""
	if scene_completed:
		return

	scene_completed = true
	simulation_manager.stop_simulation()

	print("\n" + "=".repeat(50))
	print("✓ CRAFTING CHAIN BENCHMARK COMPLETED!")
	_print_final_metrics()
	print("=".repeat(50))

func _print_final_metrics():
	"""Print final benchmark metrics"""
	var elapsed_time = (Time.get_ticks_msec() / 1000.0) - start_time

	print("\nFinal Metrics:")
	print("  Items Crafted:")
	for item_name in items_crafted.keys():
		print("    - %s: %d" % [item_name, items_crafted[item_name]])
	print("  Total Items: %d" % total_items_crafted)
	print("  Crafting Attempts: %d" % crafting_attempts)
	print("  Successful Crafts: %d" % successful_crafts)
	print("  Recipe Efficiency: %.1f%%" % _calculate_recipe_efficiency())
	print("  Resources Collected: %d" % resources_collected)
	print("  Resources Used: %d" % resources_used)
	print("  Resources Wasted: %d" % _calculate_waste())
	print("  Total Crafting Time: %.2f seconds" % total_crafting_time)
	print("  Total Time: %.2f seconds" % elapsed_time)
	print("  Efficiency Score: %.2f" % _calculate_efficiency_score())

func _calculate_recipe_efficiency() -> float:
	"""Calculate recipe efficiency (successful crafts / attempts)"""
	if crafting_attempts == 0:
		return 0.0
	return (float(successful_crafts) / float(crafting_attempts)) * 100.0

func _calculate_waste() -> int:
	"""Calculate wasted resources"""
	# Wasted = collected - used - remaining in inventory
	var remaining = 0
	for item in agent_inventory.values():
		remaining += item
	return resources_collected - resources_used - remaining

func _calculate_efficiency_score() -> float:
	"""Calculate overall efficiency score"""
	var efficiency = 0.0

	# Did we craft the target item?
	if agent_inventory.get(TARGET_ITEM, 0) > 0:
		efficiency += 50.0

	# Recipe efficiency bonus
	efficiency += _calculate_recipe_efficiency() * 0.3

	# Waste penalty
	var waste = _calculate_waste()
	efficiency -= waste * 5.0

	return max(efficiency, 0.0)

func _update_metrics_ui():
	"""Update metrics display"""
	if metrics_label == null:
		return

	var elapsed_time = 0.0
	if simulation_manager.is_running:
		elapsed_time = (Time.get_ticks_msec() / 1000.0) - start_time

	var status = "RUNNING" if simulation_manager.is_running else "STOPPED"
	if scene_completed:
		status = "COMPLETED"

	var crafting_status = "Idle"
	if current_craft != null:
		crafting_status = "Crafting %s..." % current_craft.item_name

	metrics_label.text = "Crafting Chain Benchmark [%s]
Tick: %d
Items Crafted: %d
Recipe Efficiency: %.1f%%
Resources Used: %d / %d
Resource Waste: %d
Crafting Time: %.2f s
Status: %s
Target: %s

Inventory: %s

Press SPACE to start/stop
Press R to reset
Press I to print inventory" % [
		status,
		simulation_manager.current_tick,
		total_items_crafted,
		_calculate_recipe_efficiency(),
		resources_used,
		resources_collected,
		_calculate_waste(),
		total_crafting_time,
		crafting_status,
		TARGET_ITEM,
		str(agent_inventory)
	]

func _print_inventory():
	"""Print current inventory"""
	print("\nCurrent Inventory:")
	for item in agent_inventory.keys():
		print("  - %s: %d" % [item, agent_inventory[item]])

func _reset_scene():
	"""Reset the scene"""
	print("Resetting crafting chain scene...")

	simulation_manager.reset_simulation()

	# Reset metrics
	items_crafted.clear()
	total_items_crafted = 0
	resources_collected = 0
	resources_used = 0
	resources_wasted = 0
	crafting_attempts = 0
	successful_crafts = 0
	start_time = 0.0
	total_crafting_time = 0.0
	scene_completed = false
	current_craft = null

	# Reset inventory
	agent_inventory.clear()

	# Reset agent position
	agent.global_position = Vector3(0, 1, 10)

	# Reset resources
	for resource in base_resources:
		resource.collected = false
		if resource.node != null:
			resource.node.visible = true

	print("✓ Scene reset!")
