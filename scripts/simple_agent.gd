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
		print("[SimpleAgent] ✓ Movement configured:")
		print("[SimpleAgent]   - _target_position: ", _target_position)
		print("[SimpleAgent]   - _movement_speed: ", _movement_speed)
		print("[SimpleAgent]   - _is_moving: ", _is_moving)
		print("[SimpleAgent]   - Distance to target: ", global_position.distance_to(_target_position))

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

func _process(delta):
	"""Handle movement each frame"""
	# Debug: Print every 60 frames if moving
	if _is_moving and Engine.get_process_frames() % 60 == 0:
		print("[SimpleAgent._process] Frame check - _is_moving=", _is_moving, " pos=", global_position, " target=", _target_position)

	if _is_moving:
		var distance = global_position.distance_to(_target_position)

		# Stop if close enough (0.1 unit tolerance)
		if distance < 0.1:
			print("[SimpleAgent._process] ✓ Reached target! Final position: ", global_position)
			_is_moving = false
			global_position = _target_position
			return

		# Move toward target
		var direction = (_target_position - global_position).normalized()
		var move_distance = _movement_speed * move_speed * delta

		# Debug print every 60 frames (~1 second)
		if Engine.get_process_frames() % 60 == 0:
			print("[SimpleAgent._process] Moving...")
			print("  Current position: ", global_position)
			print("  Target position: ", _target_position)
			print("  Distance remaining: ", distance)
			print("  Direction: ", direction)
			print("  Move distance this frame: ", move_distance)
			print("  Effective speed: ", move_distance / delta)

		# Don't overshoot the target
		if move_distance > distance:
			global_position = _target_position
			_is_moving = false
			print("[SimpleAgent._process] ✓ Reached target (overshoot prevention)! Final position: ", global_position)
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
