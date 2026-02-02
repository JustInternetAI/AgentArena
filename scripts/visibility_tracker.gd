extends Node
class_name VisibilityTracker

## Tracks which areas of the world the agent has seen.
##
## Uses a 2D grid (ignoring Y) to track visibility. Each cell can be:
## - unseen: Never in agent's line of sight
## - seen: Agent has had line of sight to this cell
##
## Provides exploration summaries for LLM prompts:
## - Percentage of area explored
## - Directions to nearest unexplored frontiers
##
## Usage:
##   var tracker = VisibilityTracker.new()
##   add_child(tracker)
##   tracker.set_world_bounds(Vector2(-25, -25), Vector2(25, 25))
##   # Each tick:
##   tracker.update_visibility(agent_position, perception_radius)
##   var summary = tracker.get_exploration_summary(agent_position)

signal exploration_updated(percentage: float)

## Configuration
@export var cell_size: float = 2.0  ## Size of each grid cell in world units
@export var use_raycasting: bool = false  ## If true, use raycasts to check for walls blocking vision

## Debug visualization
var _debug_enabled: bool = false
var _debug_mesh_instance: MeshInstance3D = null
var _debug_needs_update: bool = false

## World bounds (set via set_world_bounds or auto-detect)
var world_min: Vector2 = Vector2(-25, -25)
var world_max: Vector2 = Vector2(25, 25)

## Grid storage: Vector2i -> bool (true = seen)
var _seen_cells: Dictionary = {}

## Cached metrics
var _total_navigable_cells: int = 0
var _seen_cell_count: int = 0
var _exploration_percentage: float = 0.0

## Reference to physics space for raycasting (set in _ready or by parent)
var _space_state: PhysicsDirectSpaceState3D = null
var _los_collision_mask: int = 2  ## Collision layer for obstacles that block vision

func _ready():
	# Try to get physics space state
	if get_tree() and get_tree().root:
		var world_3d = get_tree().root.get_world_3d()
		if world_3d:
			_space_state = world_3d.direct_space_state

func set_world_bounds(min_pos: Vector2, max_pos: Vector2) -> void:
	"""Set the world bounds for exploration tracking."""
	world_min = min_pos
	world_max = max_pos
	_calculate_total_cells()
	print("[VisibilityTracker] World bounds set: %s to %s (%d total cells)" % [
		world_min, world_max, _total_navigable_cells
	])

func set_los_collision_mask(mask: int) -> void:
	"""Set the collision mask for line-of-sight checks."""
	_los_collision_mask = mask

func _calculate_total_cells() -> void:
	"""Calculate total number of cells in the world bounds."""
	var width = int((world_max.x - world_min.x) / cell_size) + 1
	var height = int((world_max.y - world_min.y) / cell_size) + 1
	_total_navigable_cells = width * height

func world_to_cell(world_pos: Vector3) -> Vector2i:
	"""Convert world position to grid cell coordinates."""
	return Vector2i(
		int(floor(world_pos.x / cell_size)),
		int(floor(world_pos.z / cell_size))  # Use Z for 2D grid (ignore Y)
	)

func cell_to_world(cell: Vector2i) -> Vector3:
	"""Convert grid cell to world position (center of cell)."""
	return Vector3(
		(cell.x + 0.5) * cell_size,
		0.0,  # Ground level
		(cell.y + 0.5) * cell_size
	)

func is_cell_in_bounds(cell: Vector2i) -> bool:
	"""Check if a cell is within world bounds."""
	var world_x = cell.x * cell_size
	var world_z = cell.y * cell_size
	return (world_x >= world_min.x and world_x <= world_max.x and
			world_z >= world_min.y and world_z <= world_max.y)

func update_visibility(agent_pos: Vector3, perception_radius: float, agent_node: Node3D = null) -> void:
	"""Update visibility grid based on agent's current position and perception radius.

	Args:
		agent_pos: Agent's current world position
		perception_radius: How far the agent can see
		agent_node: Optional agent node for raycast exclusion
	"""
	var center_cell = world_to_cell(agent_pos)
	var cells_radius = int(ceil(perception_radius / cell_size))

	var new_cells_seen = 0

	# Mark cells within perception radius as seen
	for dx in range(-cells_radius, cells_radius + 1):
		for dz in range(-cells_radius, cells_radius + 1):
			var cell = Vector2i(center_cell.x + dx, center_cell.y + dz)

			# Skip if outside world bounds
			if not is_cell_in_bounds(cell):
				continue

			# Skip if already seen
			if _seen_cells.has(cell):
				continue

			# Get cell world position
			var cell_world = cell_to_world(cell)
			var distance = agent_pos.distance_to(cell_world)

			# Skip if beyond perception radius
			if distance > perception_radius:
				continue

			# Optional: Check line of sight (if enabled and we have physics)
			if use_raycasting and _space_state and agent_node:
				if not _has_line_of_sight(agent_pos, cell_world, agent_node):
					continue

			# Mark as seen
			_seen_cells[cell] = true
			new_cells_seen += 1

	# Update metrics
	if new_cells_seen > 0:
		_seen_cell_count = _seen_cells.size()
		_exploration_percentage = (float(_seen_cell_count) / float(_total_navigable_cells)) * 100.0 if _total_navigable_cells > 0 else 0.0
		exploration_updated.emit(_exploration_percentage)
		# Request debug visualization update
		if _debug_enabled:
			request_debug_update()

func _has_line_of_sight(from_pos: Vector3, to_pos: Vector3, agent_node: Node3D) -> bool:
	"""Check if there's clear line of sight between two positions."""
	if _space_state == null:
		return true

	var eye_offset = Vector3(0, 1.0, 0)
	var ray_start = from_pos + eye_offset
	var ray_end = to_pos + Vector3(0, 0.5, 0)

	var query = PhysicsRayQueryParameters3D.create(ray_start, ray_end)

	if agent_node is CollisionObject3D:
		query.exclude = [agent_node.get_rid()]

	query.collision_mask = _los_collision_mask

	var result = _space_state.intersect_ray(query)
	return result.is_empty()

func get_frontier_cells() -> Array[Vector2i]:
	"""Get cells that are seen and adjacent to unseen cells (frontiers)."""
	var frontiers: Array[Vector2i] = []

	for cell in _seen_cells.keys():
		# Check 4-connected neighbors
		var neighbors = [
			Vector2i(cell.x - 1, cell.y),
			Vector2i(cell.x + 1, cell.y),
			Vector2i(cell.x, cell.y - 1),
			Vector2i(cell.x, cell.y + 1)
		]

		for neighbor in neighbors:
			# If neighbor is in bounds but not seen, this is a frontier
			if is_cell_in_bounds(neighbor) and not _seen_cells.has(neighbor):
				frontiers.append(cell)
				break  # Only add cell once

	return frontiers

func get_cardinal_direction(from_pos: Vector3, to_pos: Vector3) -> String:
	"""Get cardinal/intercardinal direction from one position to another."""
	var dx = to_pos.x - from_pos.x
	var dz = to_pos.z - from_pos.z

	# Calculate angle in degrees (0 = east, 90 = north)
	var angle = rad_to_deg(atan2(-dz, dx))  # Negative Z because Godot Z points "south"

	# Normalize to 0-360
	if angle < 0:
		angle += 360

	# Map to 8 directions (each covers 45 degrees)
	if angle >= 337.5 or angle < 22.5:
		return "east"
	elif angle >= 22.5 and angle < 67.5:
		return "northeast"
	elif angle >= 67.5 and angle < 112.5:
		return "north"
	elif angle >= 112.5 and angle < 157.5:
		return "northwest"
	elif angle >= 157.5 and angle < 202.5:
		return "west"
	elif angle >= 202.5 and angle < 247.5:
		return "southwest"
	elif angle >= 247.5 and angle < 292.5:
		return "south"
	else:  # 292.5 to 337.5
		return "southeast"

func get_exploration_summary(agent_pos: Vector3) -> Dictionary:
	"""Get a summary of exploration status for LLM prompts.

	Returns:
		Dictionary with:
		- exploration_percentage: float (0-100)
		- total_cells: int
		- seen_cells: int
		- frontiers_by_direction: Dictionary mapping direction -> nearest distance
		- suggested_explore_targets: Array of {direction, position, distance}
	"""
	var frontiers = get_frontier_cells()

	# Group frontiers by direction and find nearest in each
	var frontiers_by_direction: Dictionary = {}
	var direction_positions: Dictionary = {}  # Store best position for each direction

	for cell in frontiers:
		var cell_world = cell_to_world(cell)
		var direction = get_cardinal_direction(agent_pos, cell_world)
		var distance = agent_pos.distance_to(cell_world)

		if not frontiers_by_direction.has(direction):
			frontiers_by_direction[direction] = distance
			direction_positions[direction] = cell_world
		elif distance < frontiers_by_direction[direction]:
			frontiers_by_direction[direction] = distance
			direction_positions[direction] = cell_world

	# Build suggested explore targets (sorted by distance)
	var explore_targets: Array[Dictionary] = []
	for direction in frontiers_by_direction.keys():
		explore_targets.append({
			"direction": direction,
			"distance": frontiers_by_direction[direction],
			"position": [
				direction_positions[direction].x,
				direction_positions[direction].y,
				direction_positions[direction].z
			]
		})

	# Sort by distance
	explore_targets.sort_custom(func(a, b): return a.distance < b.distance)

	return {
		"exploration_percentage": _exploration_percentage,
		"total_cells": _total_navigable_cells,
		"seen_cells": _seen_cell_count,
		"frontiers_by_direction": frontiers_by_direction,
		"explore_targets": explore_targets.slice(0, 5)  # Top 5 targets
	}

func get_unexplored_position_in_direction(agent_pos: Vector3, direction: String) -> Dictionary:
	"""Get a navigable unexplored position in the given direction.

	Args:
		agent_pos: Agent's current position
		direction: "north", "south", "east", "west", "northeast", etc.

	Returns:
		Dictionary with:
		- success: bool
		- position: [x, y, z] if success
		- distance: float if success
		- has_unexplored: bool
	"""
	var frontiers = get_frontier_cells()

	# Filter frontiers by direction
	var best_distance = INF
	var best_position: Vector3 = Vector3.ZERO
	var found = false

	for cell in frontiers:
		var cell_world = cell_to_world(cell)
		var cell_direction = get_cardinal_direction(agent_pos, cell_world)

		if cell_direction == direction:
			var distance = agent_pos.distance_to(cell_world)
			if distance < best_distance:
				best_distance = distance
				best_position = cell_world
				found = true

	if found:
		return {
			"success": true,
			"position": [best_position.x, best_position.y, best_position.z],
			"distance": best_distance,
			"has_unexplored": true
		}
	else:
		return {
			"success": false,
			"has_unexplored": false,
			"reason": "No unexplored areas in direction: " + direction
		}

func is_position_explored(world_pos: Vector3) -> bool:
	"""Check if a specific position has been explored."""
	var cell = world_to_cell(world_pos)
	return _seen_cells.has(cell)

func clear() -> void:
	"""Clear all exploration data (call on episode reset)."""
	_seen_cells.clear()
	_seen_cell_count = 0
	_exploration_percentage = 0.0
	print("[VisibilityTracker] Exploration data cleared")

func get_debug_info() -> Dictionary:
	"""Get debug information about the tracker state."""
	return {
		"cell_size": cell_size,
		"world_bounds": [world_min, world_max],
		"total_cells": _total_navigable_cells,
		"seen_cells": _seen_cell_count,
		"exploration_percentage": _exploration_percentage,
		"frontier_count": get_frontier_cells().size()
	}

## Debug Visualization

func toggle_debug_visualization() -> bool:
	"""Toggle debug overlay on/off. Returns new state."""
	_debug_enabled = not _debug_enabled
	if _debug_enabled:
		_create_debug_mesh()
		_update_debug_mesh()
		print("[VisibilityTracker] Debug visualization ENABLED")
	else:
		_destroy_debug_mesh()
		print("[VisibilityTracker] Debug visualization DISABLED")
	return _debug_enabled

func set_debug_visualization(enabled: bool) -> void:
	"""Enable or disable debug visualization."""
	if _debug_enabled == enabled:
		return
	toggle_debug_visualization()

func _create_debug_mesh() -> void:
	"""Create the mesh instance for debug visualization."""
	if _debug_mesh_instance != null:
		return

	_debug_mesh_instance = MeshInstance3D.new()
	_debug_mesh_instance.name = "ExplorationDebugMesh"

	# Create a simple material for the overlay
	var material = StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.cull_mode = BaseMaterial3D.CULL_DISABLED
	material.vertex_color_use_as_albedo = true

	_debug_mesh_instance.material_override = material
	add_child(_debug_mesh_instance)

func _destroy_debug_mesh() -> void:
	"""Remove the debug mesh."""
	if _debug_mesh_instance != null:
		_debug_mesh_instance.queue_free()
		_debug_mesh_instance = null

func _update_debug_mesh() -> void:
	"""Rebuild the debug mesh with current exploration state."""
	if not _debug_enabled or _debug_mesh_instance == null:
		return

	var frontiers = get_frontier_cells()
	var frontier_set: Dictionary = {}
	for cell in frontiers:
		frontier_set[cell] = true

	# Create immediate mesh
	var mesh = ImmediateMesh.new()
	mesh.surface_begin(Mesh.PRIMITIVE_TRIANGLES)

	# Cell half-size for quad vertices (slightly smaller for gaps between cells)
	var half = (cell_size * 0.48)
	var y_offset = 0.05  # Slightly above ground

	# Calculate grid bounds in cells
	var min_cell_x = int(floor(world_min.x / cell_size))
	var max_cell_x = int(floor(world_max.x / cell_size))
	var min_cell_z = int(floor(world_min.y / cell_size))
	var max_cell_z = int(floor(world_max.y / cell_size))

	# Draw each cell
	for cx in range(min_cell_x, max_cell_x + 1):
		for cz in range(min_cell_z, max_cell_z + 1):
			var cell = Vector2i(cx, cz)
			var center = cell_to_world(cell)
			center.y = y_offset

			var color: Color
			if frontier_set.has(cell):
				# Frontier cell - yellow/orange
				color = Color(1.0, 0.7, 0.0, 0.5)
			elif _seen_cells.has(cell):
				# Seen cell - light green transparent
				color = Color(0.2, 0.8, 0.2, 0.15)
			else:
				# Unseen cell - dark fog
				color = Color(0.1, 0.1, 0.15, 0.6)

			# Add quad (two triangles)
			_add_quad_to_mesh(mesh, center, half, color)

	mesh.surface_end()
	_debug_mesh_instance.mesh = mesh

func _add_quad_to_mesh(mesh: ImmediateMesh, center: Vector3, half: float, color: Color) -> void:
	"""Add a horizontal quad to the mesh."""
	var v1 = center + Vector3(-half, 0, -half)
	var v2 = center + Vector3(half, 0, -half)
	var v3 = center + Vector3(half, 0, half)
	var v4 = center + Vector3(-half, 0, half)

	# Normal pointing up
	mesh.surface_set_normal(Vector3.UP)
	mesh.surface_set_color(color)

	# Triangle 1
	mesh.surface_add_vertex(v1)
	mesh.surface_add_vertex(v2)
	mesh.surface_add_vertex(v3)

	# Triangle 2
	mesh.surface_add_vertex(v1)
	mesh.surface_add_vertex(v3)
	mesh.surface_add_vertex(v4)

func request_debug_update() -> void:
	"""Request a debug mesh update (call after visibility changes)."""
	_debug_needs_update = true

func _process(_delta: float) -> void:
	"""Update debug mesh if needed."""
	if _debug_needs_update and _debug_enabled:
		_update_debug_mesh()
		_debug_needs_update = false
