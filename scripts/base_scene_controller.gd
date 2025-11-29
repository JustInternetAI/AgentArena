extends Node3D
class_name SceneController

## Base class for benchmark scenes handling agent perception-action loop
##
## This class provides:
## - Automatic agent discovery and tracking
## - Simulation signal management
## - Per-tick observation distribution to agents
## - Tool completion signal routing
##
## Subclasses must implement:
## - _build_observations_for_agent(agent_data) -> Dictionary
##
## Subclasses can optionally override:
## - _on_scene_ready()
## - _on_scene_started()
## - _on_scene_stopped()
## - _on_scene_tick(tick)
## - _on_agent_tool_completed(agent_data, tool_name, response)

# Scene references (automatically discovered)
@onready var simulation_manager: Node = $SimulationManager
@onready var event_bus: Node = $EventBus
@onready var metrics_label: Label = $UI/MetricsLabel

# Agent tracking
var agents: Array[Dictionary] = []  # Array of {agent: Node, id: String, team: String, position: Vector3}

# Metrics
var start_time: float = 0.0
var scene_completed: bool = false

func _ready():
	"""Initialize scene controller and discover agents"""
	print("SceneController initializing...")

	# Verify required nodes
	if simulation_manager == null:
		push_error("SimulationManager not found! Ensure scene has SimulationManager node.")
		return

	# Connect simulation signals
	simulation_manager.simulation_started.connect(_on_simulation_started)
	simulation_manager.simulation_stopped.connect(_on_simulation_stopped)
	simulation_manager.tick_advanced.connect(_on_tick_advanced)

	# Discover agents
	_discover_agents()

	print("✓ SceneController discovered %d agent(s)" % agents.size())

	# Call scene-specific initialization
	_on_scene_ready()

func _discover_agents():
	"""Auto-discover SimpleAgent nodes in scene"""
	agents.clear()

	# Look for Agents node in scene tree
	var agents_node = get_node_or_null("Agents")
	if agents_node:
		_discover_agents_in_node(agents_node, "single")

	# Look for team-based agents (TeamBlue, TeamRed, etc.)
	for team_name in ["TeamBlue", "TeamRed", "TeamGreen", "TeamYellow"]:
		var team_node = get_node_or_null(team_name)
		if team_node:
			var team_id = team_name.to_lower().replace("team", "")
			_discover_agents_in_node(team_node, team_id)

func _discover_agents_in_node(parent_node: Node, team: String):
	"""Discover agents in a specific parent node"""
	for child in parent_node.get_children():
		if child.has_method("perceive") and child.has_method("call_tool"):
			# This is a SimpleAgent (or subclass)
			var agent_data = {
				"agent": child,
				"id": child.agent_id if "agent_id" in child else child.name,
				"team": team,
				"position": child.global_position
			}
			agents.append(agent_data)

			# Connect to tool completion signal
			child.tool_completed.connect(
				func(tool_name: String, response: Dictionary):
					_on_agent_tool_completed(agent_data, tool_name, response)
			)

			# Create visual if available
			_create_agent_visual(child, agent_data)

			print("  - Discovered agent: %s (team: %s)" % [agent_data.id, team])

func _create_agent_visual(agent_node: Node, agent_data: Dictionary):
	"""Create visual representation for an agent (if not already present)"""
	# Check if visual already exists as a child
	var existing_visual = agent_node.get_node_or_null("AgentVisual")
	if existing_visual != null:
		# Visual already exists in scene, just configure it
		var color = _get_team_color(agent_data.team)
		if existing_visual.has_method("set_team_color"):
			existing_visual.set_team_color(color)
		var display_name = agent_data.id if agent_data.team == "single" else "%s_%s" % [agent_data.team, agent_data.id]
		if existing_visual.has_method("set_agent_name"):
			existing_visual.set_agent_name(display_name)
		return

	# Create new visual at runtime (fallback for dynamically created agents)
	var visual_scene = load("res://scenes/agent_visual.tscn")
	if visual_scene == null:
		return

	var visual_instance = visual_scene.instantiate()
	agent_node.add_child(visual_instance)

	# Set team color
	var color = _get_team_color(agent_data.team)
	if visual_instance.has_method("set_team_color"):
		visual_instance.set_team_color(color)

	# Set agent name
	var display_name = agent_data.id if agent_data.team == "single" else "%s_%s" % [agent_data.team, agent_data.id]
	if visual_instance.has_method("set_agent_name"):
		visual_instance.set_agent_name(display_name)

func _get_team_color(team: String) -> Color:
	"""Get color for team"""
	match team:
		"blue": return Color(0.2, 0.4, 0.9)
		"red": return Color(0.9, 0.2, 0.2)
		"green": return Color(0.3, 0.8, 0.3)
		"yellow": return Color(0.9, 0.9, 0.2)
		"single": return Color(0.3, 0.8, 0.3)  # Default green for single agents
		_: return Color(0.5, 0.5, 0.5)  # Default gray

func _on_simulation_started():
	"""Handle simulation start"""
	start_time = Time.get_ticks_msec() / 1000.0
	scene_completed = false
	_on_scene_started()

func _on_simulation_stopped():
	"""Handle simulation stop"""
	_on_scene_stopped()

func _on_tick_advanced(tick: int):
	"""Send observations to all agents each tick"""
	# Update agent positions
	for agent_data in agents:
		agent_data.position = agent_data.agent.global_position

	# Send perception to each agent
	for agent_data in agents:
		var observations = _build_observations_for_agent(agent_data)
		agent_data.agent.perceive(observations)

	# Call scene-specific tick logic
	_on_scene_tick(tick)

## Virtual methods to override in subclasses

func _on_scene_ready():
	"""Override: Called after SceneController setup is complete"""
	pass

func _on_scene_started():
	"""Override: Called when simulation starts"""
	pass

func _on_scene_stopped():
	"""Override: Called when simulation stops"""
	pass

func _on_scene_tick(tick: int):
	"""Override: Called each simulation tick after observations sent"""
	pass

func _build_observations_for_agent(agent_data: Dictionary) -> Dictionary:
	"""Override: Build scene-specific observations for an agent

	Args:
		agent_data: Dictionary with {agent: Node, id: String, team: String, position: Vector3}

	Returns:
		Dictionary with observations to send to agent
	"""
	# Default implementation - subclasses should override
	return {
		"agent_id": agent_data.id,
		"team": agent_data.team,
		"position": agent_data.position,
		"tick": simulation_manager.current_tick
	}

func _on_agent_tool_completed(agent_data: Dictionary, tool_name: String, response: Dictionary):
	"""Override: Handle tool completion from an agent

	Args:
		agent_data: Dictionary with {agent: Node, id: String, team: String, position: Vector3}
		tool_name: Name of the tool that was executed
		response: Response dictionary from tool execution
	"""
	# Default implementation - just log
	print("SceneController: Agent '%s' completed tool '%s': %s" % [agent_data.id, tool_name, response])

## Helper methods

func get_agents_by_team(team: String) -> Array[Dictionary]:
	"""Get all agents on a specific team"""
	var team_agents: Array[Dictionary] = []
	for agent_data in agents:
		if agent_data.team == team:
			team_agents.append(agent_data)
	return team_agents

func get_agent_by_id(agent_id: String) -> Dictionary:
	"""Get agent data by ID"""
	for agent_data in agents:
		if agent_data.id == agent_id:
			return agent_data
	return {}

func get_elapsed_time() -> float:
	"""Get elapsed time since simulation start"""
	if simulation_manager and simulation_manager.is_running:
		return (Time.get_ticks_msec() / 1000.0) - start_time
	return 0.0
