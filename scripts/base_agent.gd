extends CharacterBody3D
class_name BaseAgent
## Base class for all agent types in Agent Arena
##
## Now extends CharacterBody3D for physics-based movement with collision detection.
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

@warning_ignore("unused_signal")  # Used by external systems connecting to agent
signal tool_completed(tool_name: String, response: Dictionary)
signal damage_taken(amount: float, source: Node, source_type: String)
@warning_ignore("unused_signal")  # Used by external systems connecting to agent
signal collision_detected(collision: KinematicCollision3D)

@export var agent_id: String = ""
@export var max_health: float = 100.0
@export var current_health: float = 100.0

func _ready():
	"""Override in subclass to perform agent-specific initialization"""
	# Configure collision layers
	# Layer 4 = Agents, Mask = Ground (1) + Obstacles (2)
	collision_layer = 4
	collision_mask = 3

	if agent_id.is_empty():
		agent_id = "agent_" + str(Time.get_ticks_msec())
		print("BaseAgent: Auto-generated ID: ", agent_id)

func take_damage(amount: float, source: Node = null, source_type: String = "unknown") -> void:
	"""Apply damage to this agent and emit signal."""
	current_health -= amount
	current_health = max(current_health, 0.0)
	damage_taken.emit(amount, source, source_type)
	print("Agent '%s' took %.1f damage from %s. Health: %.1f/%.1f" % [
		agent_id, amount, source_type, current_health, max_health
	])

func heal(amount: float) -> void:
	"""Heal this agent."""
	current_health += amount
	current_health = min(current_health, max_health)

func is_alive() -> bool:
	"""Check if agent is still alive."""
	return current_health > 0.0

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
