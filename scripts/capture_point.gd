extends Area3D

## Capture Point - Reusable scene for team capture objectives
## Provides visual feedback for ownership and capture progress

@export var point_name: String = "CapturePoint"
@export var capture_radius: float = 3.0

@onready var platform: MeshInstance3D = $Platform
@onready var status_label: Label3D = $StatusLabel
@onready var progress_bar: MeshInstance3D = $CaptureProgressBar

var progress_mesh: BoxMesh

# State
var owner_team: String = "neutral"
var capture_progress: float = 0.0
var capturing_team: String = ""
var agents_present: Array = []

# Visual materials
var neutral_material: StandardMaterial3D
var blue_material: StandardMaterial3D
var red_material: StandardMaterial3D
var capture_material: StandardMaterial3D

func _ready():
	# Create materials for different states
	neutral_material = StandardMaterial3D.new()
	neutral_material.albedo_color = Color(0.7, 0.7, 0.7, 1.0)
	neutral_material.metallic = 0.3
	neutral_material.roughness = 0.7

	blue_material = StandardMaterial3D.new()
	blue_material.albedo_color = Color(0.2, 0.4, 0.9, 1.0)
	blue_material.metallic = 0.4
	blue_material.roughness = 0.6
	blue_material.emission_enabled = true
	blue_material.emission = Color(0.1, 0.2, 0.5, 1.0)

	red_material = StandardMaterial3D.new()
	red_material.albedo_color = Color(0.9, 0.2, 0.2, 1.0)
	red_material.metallic = 0.4
	red_material.roughness = 0.6
	red_material.emission_enabled = true
	red_material.emission = Color(0.5, 0.1, 0.1, 1.0)

	capture_material = StandardMaterial3D.new()
	capture_material.albedo_color = Color(1.0, 0.8, 0.2, 1.0)
	capture_material.metallic = 0.5
	capture_material.roughness = 0.5

	# Create progress bar mesh
	progress_mesh = BoxMesh.new()
	progress_mesh.size = Vector3(2.0, 0.2, 0.2)
	if progress_bar:
		progress_bar.mesh = progress_mesh

	# Set initial state
	_update_visuals()

func _process(_delta):
	# Update label to face camera
	if status_label:
		_update_label()

func set_owner_team(team: String):
	"""Set the owning team (neutral, blue, red)"""
	owner_team = team
	_update_visuals()

func set_capture_progress(progress: float, team: String):
	"""Update capture progress (0.0 - 1.0)"""
	capture_progress = clamp(progress, 0.0, 1.0)
	capturing_team = team
	_update_visuals()

func reset_capture():
	"""Reset capture progress"""
	capture_progress = 0.0
	capturing_team = ""
	progress_bar.visible = false
	_update_visuals()

func _update_visuals():
	"""Update visual appearance based on state"""
	if platform == null:
		return

	# Update platform color based on owner
	match owner_team:
		"neutral":
			platform.set_surface_override_material(0, neutral_material)
		"blue":
			platform.set_surface_override_material(0, blue_material)
		"red":
			platform.set_surface_override_material(0, red_material)

	# Show progress bar if being captured
	if capturing_team != "" and capture_progress > 0.0:
		progress_bar.visible = true
		# Update progress bar scale based on capture progress
		progress_bar.scale = Vector3(capture_progress * 2.0, 0.2, 0.2)

		# Color progress bar based on capturing team
		var mat = StandardMaterial3D.new()
		if capturing_team == "blue":
			mat.albedo_color = Color(0.3, 0.5, 1.0, 1.0)
		elif capturing_team == "red":
			mat.albedo_color = Color(1.0, 0.3, 0.3, 1.0)
		progress_bar.set_surface_override_material(0, mat)
	else:
		progress_bar.visible = false

func _update_label():
	"""Update status label text"""
	if status_label == null:
		return

	var status_text = point_name + "\n"

	if capturing_team != "":
		status_text += "Capturing: %s (%d%%)" % [capturing_team.capitalize(), int(capture_progress * 100)]
		status_label.modulate = Color(1.0, 0.8, 0.2, 1.0)
	else:
		status_text += owner_team.capitalize()
		match owner_team:
			"neutral":
				status_label.modulate = Color(0.7, 0.7, 0.7, 1.0)
			"blue":
				status_label.modulate = Color(0.4, 0.6, 1.0, 1.0)
			"red":
				status_label.modulate = Color(1.0, 0.4, 0.4, 1.0)

	if agents_present.size() > 0:
		status_text += "\nAgents: %d" % agents_present.size()

	status_label.text = status_text

func get_state() -> Dictionary:
	"""Get current state as dictionary"""
	return {
		"name": point_name,
		"position": global_position,
		"owner": owner_team,
		"capture_progress": capture_progress,
		"capturing_team": capturing_team,
		"agents_present": agents_present,
		"node": self
	}
