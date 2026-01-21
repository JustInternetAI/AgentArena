extends Node3D

## Test scene for Mixamo character import
## Controls:
## - WASD: Rotate camera around character
## - Q/E: Zoom in/out
## - 1: Play Idle animation
## - 2: Play Walking animation
## - 3: Play Running animation

@onready var camera: Camera3D = $Camera3D
@onready var character: Node3D = $Character

var camera_rotation := Vector2.ZERO
var camera_distance := 5.0
var animation_player: AnimationPlayer = null

func _ready():
	print("=== Mixamo Character Test ===")
	print("Character node: ", character)

	# Find AnimationPlayer in character
	animation_player = _find_animation_player(character)
	if animation_player:
		print("✓ AnimationPlayer found!")
		print("  Available animations:")
		for anim_name in animation_player.get_animation_list():
			print("    - ", anim_name)

		# Auto-play first animation if available
		var anim_list = animation_player.get_animation_list()
		if anim_list.size() > 0:
			var first_anim = anim_list[0]
			print("\n▶ Auto-playing first animation: ", first_anim)
			animation_player.play(first_anim)
	else:
		print("⚠ No AnimationPlayer found in character")

	# Print character structure
	print("\nCharacter node tree:")
	_print_node_tree(character, 0)

	print("\n" + "=".repeat(50))
	print("MIXAMO IMPORT ISSUE DETECTED")
	print("=".repeat(50))
	print("The animations imported as 'Take 001' instead of their real names.")
	print("This happens when downloading 'Without Skin' from Mixamo.")
	print("\nTo fix:")
	print("1. Re-download from Mixamo WITH skin included")
	print("2. OR manually rename animations in Godot")
	print("3. OR use an animation library/retargeting")
	print("=".repeat(50))

func _find_animation_player(node: Node) -> AnimationPlayer:
	"""Recursively find AnimationPlayer in node tree"""
	if node is AnimationPlayer:
		return node

	for child in node.get_children():
		var result = _find_animation_player(child)
		if result:
			return result

	return null

func _print_node_tree(node: Node, depth: int):
	"""Print node hierarchy for debugging"""
	var indent = "  ".repeat(depth)
	print(indent, "- ", node.name, " (", node.get_class(), ")")

	if depth < 3:  # Limit depth to avoid spam
		for child in node.get_children():
			_print_node_tree(child, depth + 1)

func _process(delta):
	_handle_camera_controls(delta)

func _handle_camera_controls(delta):
	var rotate_speed = 1.5
	var zoom_speed = 5.0

	# Rotate camera with WASD
	if Input.is_key_pressed(KEY_A):
		camera_rotation.x -= rotate_speed * delta
	if Input.is_key_pressed(KEY_D):
		camera_rotation.x += rotate_speed * delta
	if Input.is_key_pressed(KEY_W):
		camera_rotation.y = clamp(camera_rotation.y - rotate_speed * delta, -1.5, 1.5)
	if Input.is_key_pressed(KEY_S):
		camera_rotation.y = clamp(camera_rotation.y + rotate_speed * delta, -1.5, 1.5)

	# Zoom with Q/E
	if Input.is_key_pressed(KEY_Q):
		camera_distance = clamp(camera_distance - zoom_speed * delta, 2.0, 20.0)
	if Input.is_key_pressed(KEY_E):
		camera_distance = clamp(camera_distance + zoom_speed * delta, 2.0, 20.0)

	# Update camera position
	var cam_pos = Vector3.ZERO
	cam_pos.x = sin(camera_rotation.x) * cos(camera_rotation.y) * camera_distance
	cam_pos.y = sin(camera_rotation.y) * camera_distance + 2.0
	cam_pos.z = cos(camera_rotation.x) * cos(camera_rotation.y) * camera_distance

	camera.position = cam_pos
	camera.look_at(Vector3(0, 1, 0))

func _input(event):
	if not event is InputEventKey or not event.pressed:
		return

	print("Key pressed: ", event.keycode)

	if not animation_player:
		print("⚠ Cannot play animation - no AnimationPlayer found!")
		return

	match event.keycode:
		KEY_0:
			print("Key 0 pressed - playing built-in animation")
			_play_animation("mixamo_com")
		KEY_1:
			print("Key 1 pressed - attempting Idle animation")
			_load_and_play_animation("res://assets/characters/mixamo/Idle.fbx")
		KEY_2:
			print("Key 2 pressed - attempting Walking animation")
			_load_and_play_animation("res://assets/characters/mixamo/Walking.fbx")
		KEY_3:
			print("Key 3 pressed - attempting Running animation")
			_load_and_play_animation("res://assets/characters/mixamo/Running.fbx")
		KEY_T:
			print("Key T pressed - playing T-pose (base)")
			if animation_player:
				animation_player.stop()
		KEY_D:
			print("Key D pressed - debug animation state")
			if animation_player:
				print("  Current animation: ", animation_player.current_animation)
				print("  Is playing: ", animation_player.is_playing())
				print("  Current position: ", animation_player.current_animation_position)
				print("  All libraries: ", animation_player.get_animation_library_list())
		_:
			print("Unknown key: ", event.keycode)

func _load_and_play_animation(fbx_path: String):
	"""Load animation from separate FBX file and copy to character"""
	if not animation_player:
		print("⚠ No AnimationPlayer available")
		return

	# Load the FBX scene
	var anim_scene = load(fbx_path)
	if not anim_scene:
		print("⚠ Failed to load animation FBX: ", fbx_path)
		return

	# Instantiate to get the AnimationPlayer
	var anim_instance = anim_scene.instantiate()
	var source_anim_player = _find_animation_player(anim_instance)

	if not source_anim_player:
		print("⚠ No AnimationPlayer found in: ", fbx_path)
		anim_instance.queue_free()
		return

	# Get the first animation (usually "Take 001")
	var anim_list = source_anim_player.get_animation_list()
	if anim_list.size() == 0:
		print("⚠ No animations in: ", fbx_path)
		anim_instance.queue_free()
		return

	var source_anim_name = anim_list[0]
	var source_anim = source_anim_player.get_animation(source_anim_name)

	# Extract animation name from file path (e.g., "Idle" from "Idle.fbx")
	var file_name = fbx_path.get_file().get_basename()

	# Godot 4.x uses AnimationLibrary system
	var lib_name = "imported"

	# Get or create animation library
	if not animation_player.has_animation_library(lib_name):
		var new_lib = AnimationLibrary.new()
		animation_player.add_animation_library(lib_name, new_lib)

	var anim_lib = animation_player.get_animation_library(lib_name)

	# Add animation to library
	if anim_lib.has_animation(file_name):
		anim_lib.remove_animation(file_name)

	anim_lib.add_animation(file_name, source_anim)

	# Play it (use library prefix)
	var anim_path = lib_name + "/" + file_name
	print("▶ Playing animation: ", anim_path)
	animation_player.play(anim_path)

	# Clean up temporary instance
	anim_instance.queue_free()

func _play_animation(anim_name: String):
	"""Try to play animation by name (case-insensitive)"""
	if not animation_player:
		print("⚠ No AnimationPlayer available")
		return

	# Find matching animation (case-insensitive)
	var found_anim = ""
	for existing_anim in animation_player.get_animation_list():
		if existing_anim.to_lower() == anim_name.to_lower():
			found_anim = existing_anim
			break

	if found_anim:
		print("▶ Playing animation: ", found_anim)
		animation_player.play(found_anim)
	else:
		print("⚠ Animation not found: ", anim_name)
		print("  Available: ", animation_player.get_animation_list())
