extends Area3D
class_name CraftingStation

## Base class for crafting stations (Furnace, Anvil, Workbench)

@export var station_type: String = "unknown"
@export var station_name: String = "Crafting Station"
@export var interaction_radius: float = 2.5

signal agent_entered(agent: Node)
signal agent_exited(agent: Node)
signal crafting_started(recipe: String)
signal crafting_completed(item: String)

var agents_in_range: Array[Node] = []
var is_crafting: bool = false
var current_recipe: Dictionary = {}

func _ready():
	body_entered.connect(_on_body_entered)
	body_exited.connect(_on_body_exited)

func _on_body_entered(body: Node):
	if not agents_in_range.has(body):
		agents_in_range.append(body)
		agent_entered.emit(body)
		print("%s: Agent entered range" % station_name)

func _on_body_exited(body: Node):
	if agents_in_range.has(body):
		agents_in_range.erase(body)
		agent_exited.emit(body)
		print("%s: Agent left range" % station_name)

func can_craft(recipe: Dictionary) -> bool:
	"""Check if this station can craft the given recipe"""
	if is_crafting:
		return false

	# Check if recipe requires this station type
	if recipe.has("station") and recipe["station"].to_lower() == station_type.to_lower():
		return true

	return false

func start_crafting(recipe: Dictionary) -> bool:
	"""Start crafting an item"""
	if not can_craft(recipe):
		return false

	is_crafting = true
	current_recipe = recipe
	crafting_started.emit(recipe.get("name", "unknown"))

	print("%s: Started crafting %s" % [station_name, recipe.get("name", "unknown")])
	return true

func complete_crafting() -> String:
	"""Complete the current crafting operation"""
	if not is_crafting:
		return ""

	var item_name = current_recipe.get("name", "")
	is_crafting = false

	crafting_completed.emit(item_name)
	print("%s: Completed crafting %s" % [station_name, item_name])

	current_recipe.clear()
	return item_name

func is_agent_in_range(agent: Node) -> bool:
	"""Check if a specific agent is in range"""
	return agents_in_range.has(agent)

func get_agents_in_range() -> Array[Node]:
	"""Get all agents currently in range"""
	return agents_in_range.duplicate()
