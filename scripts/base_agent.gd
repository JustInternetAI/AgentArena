extends Node3D
class_name BaseAgent
## Base class for all agent types in Agent Arena
##
## This class defines the agent contract that SceneController expects.
## All agent implementations must provide:
##   - perceive(observations: Dictionary) -> void
##   - call_tool(tool_name: String, parameters: Dictionary) -> Dictionary
##
## Agent types:
##   - SimpleAgent: AI-controlled via Python backend (IPC)
##   - PlayerControlledAgent: Keyboard-controlled for manual testing
##   - (Future: NetworkedAgent, RecordedAgent, etc.)

signal tool_completed(tool_name: String, response: Dictionary)

@export var agent_id: String = ""

func _ready():
	"""Override in subclass to perform agent-specific initialization"""
	if agent_id.is_empty():
		agent_id = "agent_" + str(Time.get_ticks_msec())
		print("BaseAgent: Auto-generated ID: ", agent_id)

func perceive(_observations: Dictionary) -> void:
	"""
	Receive observations from SceneController each tick.

	Override this method in subclasses to handle observations.
	Called by SceneController on every simulation tick.

	Args:
		_observations: Dictionary containing agent's current perceptions
	"""
	push_warning("BaseAgent.perceive() called but not overridden in subclass")

func call_tool(_tool_name: String, _parameters: Dictionary = {}) -> Dictionary:
	"""
	Execute a tool action for this agent.

	Override this method in subclasses to handle tool execution.
	Called when the agent needs to perform an action (move, pickup, etc.).

	Args:
		_tool_name: Name of the tool to execute
		_parameters: Tool-specific parameters

	Returns:
		Dictionary with execution result: {"success": bool, ...}
	"""
	push_error("BaseAgent.call_tool() called but not overridden in subclass")
	return {"success": false, "error": "Not implemented"}
