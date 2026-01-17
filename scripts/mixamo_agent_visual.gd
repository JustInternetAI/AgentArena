extends Node3D

## Mixamo Agent Visual Representation
## Uses Mixamo Y Bot character with animation support
## Provides the same interface as AgentVisual for easy swapping

@export var agent_name: String = "Agent"
@export var team_color: Color = Color(0.3, 0.7, 1.0)  # Default blue
@export var show_direction_indicator: bool = true

# Animation paths
const IDLE_ANIMATION_PATH = "res://assets/characters/mixamo/Idle.fbx"
const WALK_ANIMATION_PATH = "res://assets/characters/mixamo/Walking.fbx"
const RUN_ANIMATION_PATH = "res://assets/characters/mixamo/Running.fbx"

# Node references
var character: Node3D
var skeleton: Skeleton3D
var animation_player: AnimationPlayer
var label: Label3D
var direction_indicator: MeshInstance3D

# Animation state
enum AnimState { IDLE, WALKING, RUNNING }
var current_anim_state: AnimState = AnimState.IDLE
var loaded_animations := {}

# Movement tracking for animation blending
var velocity := Vector3.ZERO
var walk_speed_threshold := 0.5
var run_speed_threshold := 3.0

func _ready():
	_setup_character()
	_setup_label()
	_setup_direction_indicator()
	_load_animations()
	_update_team_color()

func _setup_character():
	"""Find character components"""
	character = $Character
	if not character:
		push_error("MixamoAgentVisual: No Character node found")
		return

	skeleton = _find_skeleton(character)
	if skeleton:
		print("MixamoAgentVisual: Skeleton found with %d bones" % skeleton.get_bone_count())
	else:
		push_error("MixamoAgentVisual: No Skeleton3D found in character")

	animation_player = _find_animation_player(character)
	if animation_player:
		print("MixamoAgentVisual: AnimationPlayer found")
	else:
		push_error("MixamoAgentVisual: No AnimationPlayer found in character")

func _setup_label():
	"""Setup the agent name label"""
	label = $Label3D
	if label:
		label.text = agent_name
		label.modulate = team_color.lightened(0.3)

func _setup_direction_indicator():
	"""Setup direction indicator"""
	direction_indicator = $DirectionIndicator
	if direction_indicator:
		direction_indicator.visible = show_direction_indicator

func _load_animations():
	"""Pre-load all animations"""
	if not animation_player or not skeleton:
		push_error("MixamoAgentVisual: Cannot load animations - missing AnimationPlayer or Skeleton")
		return

	print("MixamoAgentVisual: Loading animations...")

	# Load animations
	_load_animation_from_fbx(IDLE_ANIMATION_PATH, "idle")
	_load_animation_from_fbx(WALK_ANIMATION_PATH, "walk")
	_load_animation_from_fbx(RUN_ANIMATION_PATH, "run")

	print("MixamoAgentVisual: Loaded %d animations" % loaded_animations.size())

	# Start with idle
	play_animation("idle")

func _find_skeleton(node: Node) -> Skeleton3D:
	"""Recursively find Skeleton3D in node tree"""
	if node is Skeleton3D:
		return node
	for child in node.get_children():
		var result = _find_skeleton(child)
		if result:
			return result
	return null

func _find_animation_player(node: Node) -> AnimationPlayer:
	"""Recursively find AnimationPlayer in node tree"""
	if node is AnimationPlayer:
		return node
	for child in node.get_children():
		var result = _find_animation_player(child)
		if result:
			return result
	return null

# ============================================================================
# Animation Loading (from test_mixamo_fixed.gd)
# ============================================================================

func _load_animation_from_fbx(fbx_path: String, anim_name: String):
	"""Load animation from separate FBX file with proper retargeting"""
	if not animation_player or not skeleton:
		print("  [%s] Skipped - no animation_player or skeleton" % anim_name)
		return

	if loaded_animations.has(anim_name):
		print("  [%s] Already loaded" % anim_name)
		return  # Already loaded

	# Check if file exists
	if not ResourceLoader.exists(fbx_path):
		push_warning("Animation file not found: %s" % fbx_path)
		return

	print("  [%s] Loading from %s" % [anim_name, fbx_path])

	# Load the FBX scene
	var anim_scene = load(fbx_path)
	if not anim_scene:
		push_warning("Failed to load animation FBX: %s" % fbx_path)
		return

	# Instantiate temporarily
	var anim_instance = anim_scene.instantiate()
	var source_anim_player = _find_animation_player(anim_instance)

	if not source_anim_player:
		print("  [%s] No AnimationPlayer in FBX" % anim_name)
		anim_instance.queue_free()
		return

	# Get animation with most keyframes (skip static "Take 001" pose)
	var source_anim: Animation = null
	var best_key_count = 0

	for lib_name in source_anim_player.get_animation_library_list():
		var lib = source_anim_player.get_animation_library(lib_name)
		for source_anim_name in lib.get_animation_list():
			var anim = lib.get_animation(source_anim_name)
			var total_keys = 0
			for t in range(anim.get_track_count()):
				total_keys += anim.track_get_key_count(t)
			if total_keys > best_key_count:
				best_key_count = total_keys
				source_anim = anim

	if not source_anim:
		print("  [%s] No animation found in FBX" % anim_name)
		anim_instance.queue_free()
		return

	print("  [%s] Found animation with %d keys" % [anim_name, best_key_count])

	# Retarget animation
	var retargeted_anim = _retarget_animation(source_anim)
	if not retargeted_anim:
		print("  [%s] Retargeting failed" % anim_name)
		anim_instance.queue_free()
		return

	# Get or create "imported" library
	var lib_name = "imported"
	if not animation_player.has_animation_library(lib_name):
		var new_lib = AnimationLibrary.new()
		animation_player.add_animation_library(lib_name, new_lib)

	var anim_lib = animation_player.get_animation_library(lib_name)

	# Add retargeted animation
	if anim_lib.has_animation(anim_name):
		anim_lib.remove_animation(anim_name)

	anim_lib.add_animation(anim_name, retargeted_anim)
	loaded_animations[anim_name] = true
	print("  [%s] Loaded successfully (%d tracks)" % [anim_name, retargeted_anim.get_track_count()])

	# Clean up
	anim_instance.queue_free()

func _retarget_animation(source_anim: Animation) -> Animation:
	"""Retarget animation tracks to work with target skeleton"""
	if not skeleton or not animation_player:
		return null

	var new_anim = Animation.new()
	new_anim.length = source_anim.length
	new_anim.loop_mode = Animation.LOOP_LINEAR

	# Get skeleton path relative to AnimationPlayer's root_node
	var target_skeleton_path = _get_skeleton_path_for_animation()
	if target_skeleton_path == NodePath():
		return null

	# Copy and retarget each track
	for i in range(source_anim.get_track_count()):
		var track_path = source_anim.track_get_path(i)
		var track_type = source_anim.track_get_type(i)

		# Extract bone name from track path
		var path_str = str(track_path)
		var bone_name = ""

		if ":" in path_str:
			bone_name = path_str.split(":")[1]
		else:
			continue

		# Check if bone exists in target skeleton
		var bone_idx = skeleton.find_bone(bone_name)
		if bone_idx == -1:
			continue

		# Create new track path
		var new_track_path = String(target_skeleton_path) + ":" + bone_name

		# Add track to new animation
		var new_track_idx = new_anim.add_track(track_type)
		new_anim.track_set_path(new_track_idx, new_track_path)
		new_anim.track_set_interpolation_type(new_track_idx, source_anim.track_get_interpolation_type(i))

		# Copy all keyframes
		for key_idx in range(source_anim.track_get_key_count(i)):
			var key_time = source_anim.track_get_key_time(i, key_idx)
			var key_value = source_anim.track_get_key_value(i, key_idx)
			new_anim.track_insert_key(new_track_idx, key_time, key_value)

	return new_anim if new_anim.get_track_count() > 0 else null

func _get_skeleton_path_for_animation() -> NodePath:
	"""Get skeleton path relative to AnimationPlayer's root_node"""
	if not animation_player or not skeleton:
		print("    _get_skeleton_path: Missing animation_player or skeleton")
		return NodePath()

	# Get the AnimationPlayer's root node
	var anim_root = animation_player.get_node_or_null(animation_player.root_node)
	if not anim_root:
		print("    _get_skeleton_path: AnimationPlayer root_node '%s' does not resolve" % animation_player.root_node)
		return NodePath()

	# Get relative path from anim_root to skeleton
	var root_path = anim_root.get_path()
	var target_path = skeleton.get_path()

	var root_parts = []
	for i in range(root_path.get_name_count()):
		root_parts.append(root_path.get_name(i))

	var target_parts = []
	for i in range(target_path.get_name_count()):
		target_parts.append(target_path.get_name(i))

	# Find common prefix length
	var common_length = 0
	while common_length < root_parts.size() and common_length < target_parts.size():
		if root_parts[common_length] != target_parts[common_length]:
			break
		common_length += 1

	# Build relative path
	var path_parts = []
	for i in range(root_parts.size() - common_length):
		path_parts.append("..")
	for i in range(common_length, target_parts.size()):
		path_parts.append(target_parts[i])

	if path_parts.size() == 0:
		return NodePath()

	return NodePath("/".join(path_parts))

# ============================================================================
# Public Animation API
# ============================================================================

func play_animation(anim_name: String):
	"""Play a named animation"""
	if not animation_player:
		return

	var full_path = "imported/" + anim_name
	if animation_player.has_animation(full_path):
		animation_player.play(full_path)

func set_movement_velocity(vel: Vector3):
	"""Update velocity to auto-select appropriate animation"""
	velocity = vel
	var speed = vel.length()

	var new_state: AnimState
	if speed < walk_speed_threshold:
		new_state = AnimState.IDLE
	elif speed < run_speed_threshold:
		new_state = AnimState.WALKING
	else:
		new_state = AnimState.RUNNING

	if new_state != current_anim_state:
		current_anim_state = new_state
		match current_anim_state:
			AnimState.IDLE:
				play_animation("idle")
			AnimState.WALKING:
				play_animation("walk")
			AnimState.RUNNING:
				play_animation("run")

# ============================================================================
# AgentVisual Compatible API
# ============================================================================

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
	"""Update visual elements with team color"""
	if label:
		label.modulate = team_color.lightened(0.3)

	if direction_indicator:
		var mat = direction_indicator.get_surface_override_material(0)
		if mat is StandardMaterial3D:
			mat.albedo_color = team_color.lightened(0.4)

func set_highlight(enabled: bool):
	"""Highlight the agent (e.g., when selected or performing action)"""
	# Could add emission to character material if needed
	pass

func _process(_delta):
	# Keep direction indicator facing movement direction
	if direction_indicator and velocity.length() > 0.1:
		var flat_vel = Vector3(velocity.x, 0, velocity.z)
		if flat_vel.length() > 0.1:
			direction_indicator.look_at(global_position + flat_vel, Vector3.UP)
