extends Node

## Agent Helper Script
## Attach this as a child to Agent nodes to automatically add visual representation
## This script should be added to Agent nodes in scenes

@export var agent_name: String = "Agent"
@export var team_color: Color = Color(0.3, 0.7, 1.0)  # Default blue
@export var show_visuals: bool = true

var visual_scene: PackedScene
var visual_instance: Node3D

func _ready():
	if show_visuals:
		_create_visual_representation()

func _create_visual_representation():
	"""Create and attach visual representation to parent Agent"""
	# Load the agent visual scene
	visual_scene = load("res://scenes/agent_visual.tscn")
	if visual_scene == null:
		push_error("Could not load agent_visual.tscn")
		return

	# Instance it
	visual_instance = visual_scene.instantiate()

	# Get parent (should be the Agent node)
	var agent = get_parent()
	if agent == null:
		push_error("AgentHelper must be a child of an Agent node")
		return

	# Add as child of Agent
	agent.add_child(visual_instance)

	# Configure visuals
	if visual_instance.has_method("set_team_color"):
		visual_instance.set_team_color(team_color)
	if visual_instance.has_method("set_agent_name"):
		visual_instance.set_agent_name(agent_name)

	print("✓ Created visual for agent: ", agent_name)

func set_team_color(color: Color):
	"""Update team color"""
	team_color = color
	if visual_instance and visual_instance.has_method("set_team_color"):
		visual_instance.set_team_color(color)

func set_agent_name(name: String):
	"""Update agent name"""
	agent_name = name
	if visual_instance and visual_instance.has_method("set_agent_name"):
		visual_instance.set_agent_name(name)

func set_highlight(enabled: bool):
	"""Highlight the agent"""
	if visual_instance and visual_instance.has_method("set_highlight"):
		visual_instance.set_highlight(enabled)
