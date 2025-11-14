@tool
extends EditorScript

## Run this script in the Godot editor via File -> Run to add collision shapes
## to all Area3D nodes in the crafting_chain scene

func _run():
	print("Adding collision shapes to Area3D nodes...")

	var scene_path = "res://scenes/crafting_chain.tscn"
	var scene = load(scene_path)

	if not scene:
		print("Error: Could not load scene")
		return

	var root = scene.instantiate()

	# Process all Area3D nodes
	var areas = _find_all_area3d(root)
	print("Found ", areas.size(), " Area3D nodes")

	for area in areas:
		# Check if already has a CollisionShape3D
		var has_collision = false
		for child in area.get_children():
			if child is CollisionShape3D:
				has_collision = true
				break

		if not has_collision:
			# Add CollisionShape3D
			var collision_shape = CollisionShape3D.new()
			collision_shape.name = "CollisionShape3D"

			# Create a box shape
			var box_shape = BoxShape3D.new()
			box_shape.size = Vector3(1, 1, 1)  # Adjust as needed

			collision_shape.shape = box_shape
			area.add_child(collision_shape)
			collision_shape.owner = root

			print("  Added collision shape to: ", area.name)

	# Save the modified scene
	var packed_scene = PackedScene.new()
	packed_scene.pack(root)

	var save_result = ResourceSaver.save(packed_scene, scene_path)

	if save_result == OK:
		print("✓ Scene saved successfully!")
	else:
		print("✗ Error saving scene: ", save_result)

	root.queue_free()

func _find_all_area3d(node: Node) -> Array:
	var areas = []

	if node is Area3D:
		areas.append(node)

	for child in node.get_children():
		areas.append_array(_find_all_area3d(child))

	return areas
