extends Node3D
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

signal tool_completed(tool_name: String, response: Dictionary)
signal tick_completed(response: Dictionary)

@export var agent_id: String = ""
@export var auto_connect: bool = true
@export var move_speed: float = 5.0  # Units per second

var _cpp_agent: Agent
var _target_position: Vector3 = Vector3.ZERO
var _is_moving: bool = false
var _movement_speed: float = 1.0

func _ready():
	if agent_id.is_empty():
		agent_id = "agent_" + str(Time.get_ticks_msec())
		print("SimpleAgent: Auto-generated ID: ", agent_id)

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
	if not ToolRegistryService:
		push_error("SimpleAgent: ToolRegistryService not found!")
		return {"success": false, "error": "ToolRegistryService not available"}

	print("SimpleAgent '", agent_id, "' calling tool: ", tool_name)

	# Handle movement locally
	if tool_name == "move_to" and parameters.has("target_position"):
		var target = parameters.target_position
		# Convert array to Vector3 if needed
		if target is Array and target.size() >= 3:
			_target_position = Vector3(target[0], target[1], target[2])
		elif target is Vector3:
			_target_position = target
		else:
			print("SimpleAgent: Invalid target_position format: ", target)
			return {"success": false, "error": "Invalid target_position"}

		_movement_speed = parameters.get("speed", 1.0)
		_is_moving = true
		print("SimpleAgent '", agent_id, "' starting movement to ", _target_position, " at speed ", _movement_speed)

	return ToolRegistryService.execute_tool(agent_id, tool_name, parameters)

func send_tick(tick: int, perceptions: Array) -> void:
	"""
	Send a tick update for this agent using the global IPCService.
	Actual response comes via signal.
	"""
	if not IPCService:
		push_error("SimpleAgent: IPCService not found!")
		return

	IPCService.send_tick(agent_id, tick, perceptions)

func _process(delta):
	"""Handle movement each frame"""
	if _is_moving:
		var distance = global_position.distance_to(_target_position)

		# Stop if close enough (0.1 unit tolerance)
		if distance < 0.1:
			_is_moving = false
			global_position = _target_position
			return

		# Move toward target
		var direction = (_target_position - global_position).normalized()
		var move_distance = _movement_speed * move_speed * delta

		# Don't overshoot the target
		if move_distance > distance:
			global_position = _target_position
			_is_moving = false
		else:
			global_position += direction * move_distance

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
