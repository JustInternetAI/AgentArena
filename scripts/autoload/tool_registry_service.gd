extends Node
## Global Tool Registry Service - Singleton for managing available tools
##
## This autoload singleton manages the global catalog of tools that agents can use.
## It wraps the ToolRegistry C++ node and provides a clean API.
##
## Usage:
##   ToolRegistryService.register_tool("move_to", schema)
##   ToolRegistryService.execute_tool(agent_id, "move_to", params)
##   ToolRegistryService.get_available_tools()

signal tool_registered(tool_name: String)
signal tool_executed(agent_id: String, tool_name: String)

var tool_registry: ToolRegistry
var is_ready := false

func _ready():
	print("=== ToolRegistryService Initializing ===")

	# Wait for IPCService to be ready first
	await get_tree().process_frame

	# Create the C++ ToolRegistry node
	tool_registry = ToolRegistry.new()
	tool_registry.name = "ToolRegistry"
	add_child(tool_registry)

	# Get reference to IPCService's IPCClient
	var ipc_service = get_node("/root/IPCService")
	if ipc_service and ipc_service.ipc_client:
		tool_registry.set_ipc_client(ipc_service.ipc_client)
		print("ToolRegistryService: Connected to IPCClient")
	else:
		push_error("ToolRegistryService: Could not find IPCService!")

	# Register default tools
	_register_default_tools()

	is_ready = true
	print("=== ToolRegistryService Ready ===")

func _register_default_tools():
	"""Register the standard set of tools available to all agents"""
	print("Registering default tools...")

	# Movement tools
	register_tool("move_to", {
		"name": "move_to",
		"description": "Move to a target position in the world",
		"parameters": {
			"target_position": {"type": "array", "description": "3D position [x, y, z]"},
			"speed": {"type": "number", "description": "Movement speed multiplier", "default": 1.0}
		}
	})

	register_tool("navigate_to", {
		"name": "navigate_to",
		"description": "Navigate to target using pathfinding (avoids obstacles)",
		"parameters": {
			"target_position": {"type": "array", "description": "3D position [x, y, z]"}
		}
	})

	register_tool("stop_movement", {
		"name": "stop_movement",
		"description": "Stop all movement immediately",
		"parameters": {}
	})

	# Interaction tools
	register_tool("pickup_item", {
		"name": "pickup_item",
		"description": "Pick up an item from the world",
		"parameters": {
			"item_id": {"type": "string", "description": "Unique identifier of the item"}
		}
	})

	register_tool("drop_item", {
		"name": "drop_item",
		"description": "Drop an item from inventory",
		"parameters": {
			"item_id": {"type": "string", "description": "Unique identifier of the item"}
		}
	})

	register_tool("use_item", {
		"name": "use_item",
		"description": "Use an item from inventory",
		"parameters": {
			"item_id": {"type": "string", "description": "Unique identifier of the item"}
		}
	})

	# Query tools
	register_tool("get_inventory", {
		"name": "get_inventory",
		"description": "Get current inventory contents",
		"parameters": {}
	})

	register_tool("look_at", {
		"name": "look_at",
		"description": "Get detailed information about an object or entity",
		"parameters": {
			"target_id": {"type": "string", "description": "ID of the object to examine"}
		}
	})

	# Navigation/Exploration tools
	register_tool("plan_path", {
		"name": "plan_path",
		"description": "Plan a path to a target position. Returns waypoints and distance.",
		"parameters": {
			"target_position": {"type": "array", "description": "Target [x, y, z] position"},
			"avoid_hazards": {"type": "boolean", "description": "Route around hazards", "default": true}
		}
	})

	register_tool("explore_direction", {
		"name": "explore_direction",
		"description": "Get a position to explore in a direction (north, south, east, west, etc.)",
		"parameters": {
			"direction": {"type": "string", "description": "Direction to explore"}
		}
	})

	register_tool("get_exploration_status", {
		"name": "get_exploration_status",
		"description": "Get exploration percentage and frontier locations",
		"parameters": {}
	})

	# Crafting tools
	register_tool("craft_item", {
		"name": "craft_item",
		"description": "Craft an item at a nearby crafting station using collected resources",
		"parameters": {
			"recipe": {"type": "string", "description": "Name of the recipe to craft (e.g., 'torch', 'shelter', 'meal')"}
		}
	})

	register_tool("get_recipes", {
		"name": "get_recipes",
		"description": "Get available crafting recipes and their requirements",
		"parameters": {}
	})

	print("Registered ", get_tool_count(), " default tools")

func register_tool(tool_name: String, schema: Dictionary) -> bool:
	"""Register a new tool with the given schema"""
	if not tool_registry:
		push_error("ToolRegistry not initialized!")
		return false

	tool_registry.register_tool(tool_name, schema)
	tool_registered.emit(tool_name)
	print("Tool registered: ", tool_name)
	return true

func execute_tool(agent_id: String, tool_name: String, parameters: Dictionary) -> Dictionary:
	"""Execute a tool for a specific agent"""
	if not is_ready:
		push_error("ToolRegistryService not ready yet!")
		return {"success": false, "error": "Service not ready"}

	if not tool_registry:
		push_error("ToolRegistry not initialized!")
		return {"success": false, "error": "Registry not initialized"}

	# Get IPC client to call execute_tool_sync with agent_id at top level
	var ipc_client = tool_registry.get_ipc_client()
	if not ipc_client:
		push_error("No IPC client available!")
		return {"success": false, "error": "No IPC client"}

	# Call IPCClient directly with agent_id as separate parameter
	# This ensures agent_id is at top level of request, not inside params
	var result = ipc_client.execute_tool_sync(tool_name, parameters, agent_id, 0)

	tool_executed.emit(agent_id, tool_name)
	return result

func get_available_tools() -> Array:
	"""Get list of all registered tool names"""
	if not tool_registry:
		return []

	return tool_registry.get_all_tool_names()

func get_tool_schema(tool_name: String) -> Dictionary:
	"""Get the schema for a specific tool"""
	if not tool_registry:
		return {}

	return tool_registry.get_tool_schema(tool_name)

func has_tool(tool_name: String) -> bool:
	"""Check if a tool is registered"""
	if not tool_registry:
		return false

	return tool_registry.has_tool(tool_name)

func get_tool_count() -> int:
	"""Get the total number of registered tools"""
	return get_available_tools().size()
