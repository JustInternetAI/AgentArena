extends Node3D
## Simplified Agent - Automatically connects to global services
##
## This is a GDScript wrapper around the C++ Agent class that automatically
## connects to the IPCService and ToolRegistryService autoload singletons.
##
## Usage:
##   var agent = SimpleAgent.new()
##   agent.agent_id = "npc_guard_001"
##   add_child(agent)
##   agent.call_tool("move_to", {"target_position": [10, 0, 5]})

signal tool_completed(tool_name: String, response: Dictionary)
signal tick_completed(response: Dictionary)

@export var agent_id: String = ""
@export var auto_connect: bool = true

var _cpp_agent: Agent

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

func store_memory(key: String, value: Variant):
	"""Store a value in the agent's short-term memory"""
	if _cpp_agent:
		_cpp_agent.store_memory(key, value)

func retrieve_memory(key: String) -> Variant:
	"""Retrieve a value from the agent's short-term memory"""
	if _cpp_agent:
		return _cpp_agent.retrieve_memory(key)
	return null

func clear_short_term_memory():
	"""Clear all short-term memory"""
	if _cpp_agent:
		_cpp_agent.clear_short_term_memory()

func perceive(observations: Dictionary):
	"""Update agent's perceptions"""
	if _cpp_agent:
		_cpp_agent.perceive(observations)

func decide_action() -> Dictionary:
	"""Let the agent decide on an action"""
	if _cpp_agent:
		return _cpp_agent.decide_action()
	return {}

func execute_action(action: Dictionary):
	"""Execute an action"""
	if _cpp_agent:
		_cpp_agent.execute_action(action)

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
