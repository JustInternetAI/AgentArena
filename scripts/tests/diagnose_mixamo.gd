extends Node

## Diagnostic script to understand Mixamo import structure

func _ready():
	print("\n" + "=".repeat(60))
	print("MIXAMO CHARACTER DIAGNOSTIC")
	print("=".repeat(60))

	# Load the Y Bot character
	var character_scene = load("res://assets/characters/mixamo/Y Bot.fbx")
	if not character_scene:
		print("❌ Failed to load Y Bot.fbx")
		get_tree().quit()
		return

	print("✓ Loaded Y Bot.fbx")

	# Instantiate it
	var character = character_scene.instantiate()
	add_child(character)

	print("\n--- NODE TREE ---")
	_print_node_tree(character, 0)

	# Find skeleton
	var skeleton = _find_skeleton(character)
	if skeleton:
		print("\n--- SKELETON INFO ---")
		print("✓ Skeleton3D found: ", skeleton.name)
		print("  Bone count: ", skeleton.get_bone_count())
		print("  First 10 bones:")
		for i in range(min(10, skeleton.get_bone_count())):
			print("    [%d] %s" % [i, skeleton.get_bone_name(i)])
	else:
		print("\n❌ No Skeleton3D found")

	# Find AnimationPlayer
	var anim_player = _find_animation_player(character)
	if anim_player:
		print("\n--- ANIMATION PLAYER INFO ---")
		print("✓ AnimationPlayer found: ", anim_player.name)
		print("  Animation libraries: ", anim_player.get_animation_library_list())

		for lib_name in anim_player.get_animation_library_list():
			var lib = anim_player.get_animation_library(lib_name)
			print("\n  Library '%s':" % lib_name)
			var anim_list = lib.get_animation_list()
			print("    Animations: ", anim_list)

			# Examine first animation in detail
			if anim_list.size() > 0:
				var first_anim_name = anim_list[0]
				var anim = lib.get_animation(first_anim_name)
				print("\n    Animation '%s' details:" % first_anim_name)
				print("      Length: %.2f seconds" % anim.length)
				print("      Track count: %d" % anim.get_track_count())

				# Check first few tracks
				for i in range(min(5, anim.get_track_count())):
					var track_path = anim.track_get_path(i)
					var track_type = anim.track_get_type(i)
					print("      Track %d: %s (type: %d)" % [i, track_path, track_type])
	else:
		print("\n❌ No AnimationPlayer found")

	# Load separate animation file
	print("\n" + "=".repeat(60))
	print("SEPARATE ANIMATION FILE (Idle.fbx)")
	print("=".repeat(60))

	var idle_scene = load("res://assets/characters/mixamo/Idle.fbx")
	if idle_scene:
		var idle_instance = idle_scene.instantiate()
		print("✓ Loaded Idle.fbx")

		var idle_skeleton = _find_skeleton(idle_instance)
		if idle_skeleton:
			print("  Skeleton bone count: ", idle_skeleton.get_bone_count())
			print("  First 5 bones:")
			for i in range(min(5, idle_skeleton.get_bone_count())):
				print("    [%d] %s" % [i, idle_skeleton.get_bone_name(i)])

		var idle_anim_player = _find_animation_player(idle_instance)
		if idle_anim_player:
			print("  AnimationPlayer found")
			for lib_name in idle_anim_player.get_animation_library_list():
				var lib = idle_anim_player.get_animation_library(lib_name)
				var anim_list = lib.get_animation_list()
				print("  Library '%s': %s" % [lib_name, anim_list])

				if anim_list.size() > 0:
					var anim = lib.get_animation(anim_list[0])
					print("    Track count: %d" % anim.get_track_count())
					if anim.get_track_count() > 0:
						print("    First track path: %s" % anim.track_get_path(0))

		idle_instance.queue_free()
	else:
		print("❌ Failed to load Idle.fbx")

	print("\n" + "=".repeat(60))
	print("DIAGNOSTIC COMPLETE")
	print("=".repeat(60))

	await get_tree().create_timer(1.0).timeout
	get_tree().quit()

func _find_skeleton(node: Node) -> Skeleton3D:
	if node is Skeleton3D:
		return node
	for child in node.get_children():
		var result = _find_skeleton(child)
		if result:
			return result
	return null

func _find_animation_player(node: Node) -> AnimationPlayer:
	if node is AnimationPlayer:
		return node
	for child in node.get_children():
		var result = _find_animation_player(child)
		if result:
			return result
	return null

func _print_node_tree(node: Node, depth: int):
	var indent = "  ".repeat(depth)
	var type_info = node.get_class()

	# Add extra info for important node types
	var extra = ""
	if node is Skeleton3D:
		extra = " [%d bones]" % node.get_bone_count()
	elif node is AnimationPlayer:
		extra = " [%d libraries]" % node.get_animation_library_list().size()
	elif node is MeshInstance3D:
		extra = " [has mesh]" if node.mesh else " [no mesh]"

	print("%s- %s (%s)%s" % [indent, node.name, type_info, extra])

	if depth < 4:
		for child in node.get_children():
			_print_node_tree(child, depth + 1)
