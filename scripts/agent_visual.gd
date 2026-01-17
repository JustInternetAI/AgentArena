extends Node3D

## Agent Visual Representation
## Provides visual feedback for agent state, team color, and identification

@export var agent_name: String = "Agent"
@export var team_color: Color = Color(0.3, 0.7, 1.0)  # Default blue
@export var show_direction_indicator: bool = true

@onready var body: MeshInstance3D = $Body
@onready var head: MeshInstance3D = $Head
@onready var arms: MeshInstance3D = $Arms
@onready var left_leg: MeshInstance3D = $Legs/LeftLeg
@onready var right_leg: MeshInstance3D = $Legs/RightLeg
@onready var direction_indicator: MeshInstance3D = $DirectionIndicator
@onready var label: Label3D = $Label3D

# Materials
var body_material: StandardMaterial3D
var head_material: StandardMaterial3D
var limb_material: StandardMaterial3D
var indicator_material: StandardMaterial3D

func _ready():
	_setup_visuals()
	_update_team_color()

func _setup_visuals():
	"""Setup meshes and materials"""
	# Direction indicator visibility
	direction_indicator.visible = show_direction_indicator

	# Create materials
	body_material = StandardMaterial3D.new()
	body_material.albedo_color = team_color
	body_material.metallic = 0.3
	body_material.roughness = 0.7

	head_material = StandardMaterial3D.new()
	head_material.albedo_color = team_color.lightened(0.2)
	head_material.metallic = 0.2
	head_material.roughness = 0.6

	limb_material = StandardMaterial3D.new()
	limb_material.albedo_color = team_color.darkened(0.1)
	limb_material.metallic = 0.2
	limb_material.roughness = 0.7

	indicator_material = StandardMaterial3D.new()
	indicator_material.albedo_color = team_color.lightened(0.4)
	indicator_material.metallic = 0.4
	indicator_material.roughness = 0.5

	# Apply materials
	body.set_surface_override_material(0, body_material)
	head.set_surface_override_material(0, head_material)
	arms.set_surface_override_material(0, limb_material)
	left_leg.set_surface_override_material(0, limb_material)
	right_leg.set_surface_override_material(0, limb_material)
	direction_indicator.set_surface_override_material(0, indicator_material)

	# Update label
	if label:
		label.text = agent_name
		label.modulate = team_color.lightened(0.3)

func set_team_color(color: Color):
	"""Set the team color for this agent"""
	team_color = color
	_update_team_color()

func set_agent_name(name: String):
	"""Set the agent's display name"""
	agent_name = name
	if label:
		label.text = name

func _update_team_color():
	"""Update all materials with the team color"""
	if body_material:
		body_material.albedo_color = team_color
	if head_material:
		head_material.albedo_color = team_color.lightened(0.2)
	if limb_material:
		limb_material.albedo_color = team_color.darkened(0.1)
	if indicator_material:
		indicator_material.albedo_color = team_color.lightened(0.4)
	if label:
		label.modulate = team_color.lightened(0.3)

func set_highlight(enabled: bool):
	"""Highlight the agent (e.g., when selected or performing action)"""
	if body_material:
		if enabled:
			body_material.emission_enabled = true
			body_material.emission = team_color * 0.3
		else:
			body_material.emission_enabled = false

func _process(_delta):
	# Keep label facing camera (billboard already handles this via Label3D billboard property)
	pass
