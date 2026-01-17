extends Node3D

## Fixed Mixamo Character Test
## Properly handles animation retargeting for separate FBX files

@onready var camera: Camera3D = $Camera3D
@onready var character: Node3D = $Character

var camera_rotation := Vector2.ZERO
var camera_distance := 5.0
var animation_player: AnimationPlayer = null
var skeleton: Skeleton3D = null

# Store loaded animations
var loaded_animations := {}

func _ready():
	print("=== Mixamo Character Test (FIXED) ===")
	print("Character node: ", character)

	# Find Skeleton3D
	skeleton = _find_skeleton(character)
	if skeleton:
		print("✓ Skeleton3D found! Bones: ", skeleton.get_bone_count())
	else:
		print("⚠ No Skeleton3D found")

	# Find AnimationPlayer in character
	animation_player = _find_animation_player(character)
	if animation_player:
		print("✓ AnimationPlayer found!")
		print("  Available animations:")
		for lib_name in animation_player.get_animation_library_list():
			var lib = animation_player.get_animation_library(lib_name)
			for anim_name in lib.get_animation_list():
				var full_name = lib_name + "/" + anim_name if lib_name else anim_name
				print("    - ", full_name)

		# Auto-play first animation if available
		if animation_player.get_animation_library_list().size() > 0:
			var first_lib = animation_player.get_animation_library_list()[0]
			var anim_lib = animation_player.get_animation_library(first_lib)
			var anim_list = anim_lib.get_animation_list()
			if anim_list.size() > 0:
				var first_anim = first_lib + "/" + anim_list[0] if first_lib else anim_list[0]
				print("\n▶ Auto-playing: ", first_anim)
				animation_player.play(first_anim)
	else:
		print("⚠ No AnimationPlayer found in character")

	# Print character structure
	print("\nCharacter node tree:")
	_print_node_tree(character, 0)

	print("\n" + "=".repeat(50))
	print("CONTROLS:")
	print("  WASD - Rotate camera")
	print("  Q/E - Zoom in/out")
	print("  0 - Play built-in animation")
	print("  1 - Load & play Idle")
	print("  2 - Load & play Walking")
	print("  3 - Load & play Running")
	print("  T - Stop (T-pose)")
	print("  D - Debug animation state")
	print("=".repeat(50))

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

func _print_node_tree(node: Node, depth: int):
	"""Print node hierarchy for debugging"""
	var indent = "  ".repeat(depth)
	var extra = ""

	if node is Skeleton3D:
		extra = " [%d bones]" % node.get_bone_count()
	elif node is AnimationPlayer:
		extra = " [has animations]"

	print(indent, "- ", node.name, " (", node.get_class(), ")", extra)

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

	if not animation_player:
		print("⚠ Cannot play animation - no AnimationPlayer found!")
		return

	match event.keycode:
		KEY_0:
			print("\n[KEY 0] Playing built-in animation")
			_play_builtin_animation()
		KEY_1:
			print("\n[KEY 1] Loading Idle animation")
			_load_and_play_animation("res://assets/characters/mixamo/Idle.fbx", "Idle")
		KEY_2:
			print("\n[KEY 2] Loading Walking animation")
			_load_and_play_animation("res://assets/characters/mixamo/Walking.fbx", "Walking")
		KEY_3:
			print("\n[KEY 3] Loading Running animation")
			_load_and_play_animation("res://assets/characters/mixamo/Running.fbx", "Running")
		KEY_T:
			print("\n[KEY T] Stopping animation (T-pose)")
			animation_player.stop()
		KEY_D:
			print("\n[KEY D] Debug info:")
			_print_debug_info()

func _play_builtin_animation():
	"""Play the built-in mixamo_com animation (should work)"""
	var anim_name = "mixamo_com"
	if animation_player.has_animation(anim_name):
		print("▶ Playing built-in: ", anim_name)
		animation_player.play(anim_name)
	else:
		print("⚠ No mixamo_com animation found, trying first available...")
		for lib_name in animation_player.get_animation_library_list():
			var lib = animation_player.get_animation_library(lib_name)
			var anim_list = lib.get_animation_list()
			if anim_list.size() > 0:
				var full_name = lib_name + "/" + anim_list[0] if lib_name else anim_list[0]
				print("▶ Playing: ", full_name)
				animation_player.play(full_name)
				return
		print("⚠ No built-in animations found")

func _load_and_play_animation(fbx_path: String, anim_display_name: String):
	"""Load animation from separate FBX file

	This is the FIXED version that properly handles animation retargeting
	"""
	if not animation_player or not skeleton:
		print("⚠ Missing AnimationPlayer or Skeleton")
		return

	print("  Loading: %s" % fbx_path)

	# Check if already loaded
	if loaded_animations.has(anim_display_name):
		print("  ✓ Using cached animation")
		_play_animation(anim_display_name)
		return

	# Load the FBX scene
	var anim_scene = load(fbx_path)
	if not anim_scene:
		print("  ❌ Failed to load FBX")
		return

	# Instantiate temporarily
	var anim_instance = anim_scene.instantiate()
	var source_skeleton = _find_skeleton(anim_instance)
	var source_anim_player = _find_animation_player(anim_instance)

	if not source_anim_player:
		print("  ❌ No AnimationPlayer in FBX")
		anim_instance.queue_free()
		return

	# Get animation with most keyframes (skip static "Take 001" pose)
	var source_anim: Animation = null
	var best_key_count = 0
	print("  Source AnimationPlayer libraries:")
	for lib_name in source_anim_player.get_animation_library_list():
		var lib = source_anim_player.get_animation_library(lib_name)
		var anim_list = lib.get_animation_list()
		print("    Library '%s': %s" % [lib_name, anim_list])
		for anim_name in anim_list:
			var anim = lib.get_animation(anim_name)
			var total_keys = 0
			for t in range(anim.get_track_count()):
				total_keys += anim.track_get_key_count(t)
			print("      '%s': length=%.2fs, tracks=%d, total_keys=%d" % [anim_name, anim.length, anim.get_track_count(), total_keys])
			# Pick animation with most keyframes (the actual animation, not static pose)
			if total_keys > best_key_count:
				best_key_count = total_keys
				source_anim = anim

	if not source_anim:
		print("  ❌ No animation found in FBX")
		anim_instance.queue_free()
		return

	print("  ✓ Found animation (length: %.2fs, %d tracks)" % [source_anim.length, source_anim.get_track_count()])

	# CRITICAL FIX: Retarget animation tracks to target skeleton
	var retargeted_anim = _retarget_animation(source_anim, source_skeleton)

	if not retargeted_anim:
		print("  ❌ Failed to retarget animation")
		anim_instance.queue_free()
		return

	# Get or create "imported" library
	var lib_name = "imported"
	if not animation_player.has_animation_library(lib_name):
		var new_lib = AnimationLibrary.new()
		animation_player.add_animation_library(lib_name, new_lib)

	var anim_lib = animation_player.get_animation_library(lib_name)

	# Add retargeted animation
	if anim_lib.has_animation(anim_display_name):
		anim_lib.remove_animation(anim_display_name)

	anim_lib.add_animation(anim_display_name, retargeted_anim)
	loaded_animations[anim_display_name] = true

	print("  ✓ Animation imported successfully")

	# Clean up
	anim_instance.queue_free()

	# Play it
	_play_animation(anim_display_name)

func _retarget_animation(source_anim: Animation, source_skeleton: Skeleton3D) -> Animation:
	"""Retarget animation tracks to work with target skeleton

	This fixes the main issue: animation tracks reference wrong skeleton paths
	"""
	if not skeleton:
		return null

	var new_anim = Animation.new()
	new_anim.length = source_anim.length
	new_anim.loop_mode = Animation.LOOP_LINEAR  # Force looping for testing

	# Find skeleton path in target character
	var target_skeleton_path = _get_node_path_from_root(skeleton)
	if target_skeleton_path == NodePath():
		print("    ⚠ Could not find skeleton path")
		return null

	print("    Target skeleton path: %s" % target_skeleton_path)
	print("    Target skeleton node: %s" % skeleton.name)

	# Debug: Print first source track to understand the format
	if source_anim.get_track_count() > 0:
		var first_track = source_anim.track_get_path(0)
		print("    Source track example: %s" % first_track)

	# Copy and retarget each track
	var tracks_added = 0
	for i in range(source_anim.get_track_count()):
		var track_path = source_anim.track_get_path(i)
		var track_type = source_anim.track_get_type(i)

		# Extract bone name from track path
		# Track paths typically look like: "Skeleton3D:BoneName"
		var path_str = str(track_path)
		var bone_name = ""

		if ":" in path_str:
			bone_name = path_str.split(":")[1]
		else:
			# Skip non-bone tracks
			continue

		# Check if bone exists in target skeleton
		var bone_idx = skeleton.find_bone(bone_name)
		if bone_idx == -1:
			# Bone doesn't exist in target, skip
			continue

		# Create new track path: "path/to/Skeleton3D:BoneName"
		var new_track_path = String(target_skeleton_path) + ":" + bone_name

		# Debug first few tracks
		if tracks_added < 3:
			var type_name = _get_track_type_name(track_type)
			var key_count = source_anim.track_get_key_count(i)
			print("    Track %d: '%s' -> '%s' (type: %s, keys: %d)" % [i, str(track_path), new_track_path, type_name, key_count])

		# Add track to new animation
		var new_track_idx = new_anim.add_track(track_type)
		new_anim.track_set_path(new_track_idx, new_track_path)
		new_anim.track_set_interpolation_type(new_track_idx, source_anim.track_get_interpolation_type(i))

		# Copy all keyframes
		for key_idx in range(source_anim.track_get_key_count(i)):
			var key_time = source_anim.track_get_key_time(i, key_idx)
			var key_value = source_anim.track_get_key_value(i, key_idx)

			new_anim.track_insert_key(new_track_idx, key_time, key_value)

		tracks_added += 1

	print("    ✓ Retargeted %d/%d tracks" % [tracks_added, source_anim.get_track_count()])

	# CRITICAL DEBUG: Test if animation player can actually find the skeleton
	if animation_player and tracks_added > 0:
		print("    Testing skeleton resolution...")
		var test_path = new_anim.track_get_path(0)
		print("    Test track path: %s" % test_path)
		var resolved_node = animation_player.get_node_or_null(NodePath(test_path.get_concatenated_names()))
		if resolved_node:
			print("    ✓ Skeleton path resolves correctly!")
		else:
			print("    ❌ WARNING: Skeleton path does NOT resolve from AnimationPlayer!")
			print("    AnimationPlayer is at: %s" % animation_player.get_path())
			print("    Trying to resolve: %s" % test_path)

	return new_anim if tracks_added > 0 else null

func _get_node_path_from_root(node: Node) -> NodePath:
	"""Get node path relative to AnimationPlayer's root_node setting"""
	if not animation_player:
		return NodePath()

	# Get the AnimationPlayer's root node (where paths are resolved from)
	var anim_root = animation_player.get_node_or_null(animation_player.root_node)
	if not anim_root:
		print("    ⚠ AnimationPlayer root_node does not resolve!")
		return NodePath()

	# Get relative path from anim_root to target node
	var root_path = anim_root.get_path()
	var target_path = node.get_path()

	# Find common ancestor and build relative path
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

	# Build relative path from root to target
	var path_parts = []

	# Add ".." for each level we need to go up from root
	for i in range(root_parts.size() - common_length):
		path_parts.append("..")

	# Add the path down to target
	for i in range(common_length, target_parts.size()):
		path_parts.append(target_parts[i])

	if path_parts.size() == 0:
		return NodePath()

	return NodePath("/".join(path_parts))

func _get_track_type_name(track_type: int) -> String:
	match track_type:
		Animation.TYPE_VALUE: return "VALUE"
		Animation.TYPE_POSITION_3D: return "POSITION_3D"
		Animation.TYPE_ROTATION_3D: return "ROTATION_3D"
		Animation.TYPE_SCALE_3D: return "SCALE_3D"
		Animation.TYPE_BLEND_SHAPE: return "BLEND_SHAPE"
		Animation.TYPE_METHOD: return "METHOD"
		Animation.TYPE_BEZIER: return "BEZIER"
		Animation.TYPE_AUDIO: return "AUDIO"
		Animation.TYPE_ANIMATION: return "ANIMATION"
		_: return "UNKNOWN(%d)" % track_type

func _play_animation(anim_name: String):
	"""Play animation from imported library"""
	var full_path = "imported/" + anim_name
	print("  ▶ Playing: %s" % full_path)

	# Check if animation exists
	if not animation_player.has_animation(full_path):
		print("  ❌ Animation '%s' not found!" % full_path)
		print("  Available: ", animation_player.get_animation_list())
		return

	# Get the animation and verify it has content
	var anim = animation_player.get_animation(full_path)
	print("  Animation details: length=%.2fs, tracks=%d, loop=%s" % [anim.length, anim.get_track_count(), anim.loop_mode])

	animation_player.play(full_path)

	# Verify playback started
	await get_tree().process_frame
	print("  After play: is_playing=%s, current='%s', position=%.2f" % [
		animation_player.is_playing(),
		animation_player.current_animation,
		animation_player.current_animation_position
	])

func _print_debug_info():
	print("\n=== DEBUG INFO ===")

	# Check AnimationPlayer root node setting
	if animation_player:
		print("AnimationPlayer root_node: '%s'" % animation_player.root_node)
		var root = animation_player.get_node_or_null(animation_player.root_node)
		if root:
			print("  Resolves to: %s" % root.get_path())
		else:
			print("  ❌ Does not resolve!")

	# Compare built-in animation tracks with our retargeted tracks
	print("\n--- Track Comparison ---")
	if animation_player:
		# Get a built-in animation track
		var builtin_lib = animation_player.get_animation_library("")
		if builtin_lib and builtin_lib.get_animation_list().size() > 0:
			var builtin_anim = builtin_lib.get_animation("mixamo_com")
			if builtin_anim and builtin_anim.get_track_count() > 0:
				print("Built-in 'mixamo_com' first 3 tracks:")
				for i in range(min(3, builtin_anim.get_track_count())):
					var path = builtin_anim.track_get_path(i)
					var type = _get_track_type_name(builtin_anim.track_get_type(i))
					print("  [%d] path='%s', type=%s" % [i, path, type])

		# Get our imported animation track
		if animation_player.has_animation_library("imported"):
			var imported_lib = animation_player.get_animation_library("imported")
			if imported_lib.get_animation_list().size() > 0:
				var first_anim_name = imported_lib.get_animation_list()[0]
				var imported_anim = imported_lib.get_animation(first_anim_name)
				if imported_anim and imported_anim.get_track_count() > 0:
					print("Imported '%s' first 3 tracks:" % first_anim_name)
					for i in range(min(3, imported_anim.get_track_count())):
						var path = imported_anim.track_get_path(i)
						var type = _get_track_type_name(imported_anim.track_get_type(i))
						print("  [%d] path='%s', type=%s" % [i, path, type])
	print("------------------------")

	if character:
		print("Character path: %s" % character.get_path())

	if animation_player:
		print("AnimationPlayer path: %s" % animation_player.get_path())
		print("  Current animation: ", animation_player.current_animation)
		print("  Is playing: ", animation_player.is_playing())
		if animation_player.is_playing():
			print("  Position: %.2f" % animation_player.current_animation_position)
		print("  Libraries: ", animation_player.get_animation_library_list())

		for lib_name in animation_player.get_animation_library_list():
			var lib = animation_player.get_animation_library(lib_name)
			print("    %s: %s" % [lib_name, lib.get_animation_list()])

			# Show first animation's first track if available
			if lib.get_animation_list().size() > 0:
				var first_anim = lib.get_animation(lib.get_animation_list()[0])
				if first_anim.get_track_count() > 0:
					print("      First track: %s" % first_anim.track_get_path(0))

	if skeleton:
		print("Skeleton path: %s" % skeleton.get_path())
		print("  Bones: %d" % skeleton.get_bone_count())
		var first_bones = []
		for i in range(min(3, skeleton.get_bone_count())):
			first_bones.append(skeleton.get_bone_name(i))
		print("  First 3 bones: ", first_bones)

	# Calculate relative path from AnimationPlayer to Skeleton
	if animation_player and skeleton:
		var anim_path = animation_player.get_path()
		var skel_path = skeleton.get_path()
		print("\nPath relationship:")
		print("  From: %s" % anim_path)
		print("  To:   %s" % skel_path)

	print("=================\n")
