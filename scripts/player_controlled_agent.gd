extends Node3D
## Player Controlled Agent - Manual testing replacement for LLM-driven agent
##
## Allows keyboard control of an agent to test scene mechanics, animations,
## and tool execution without waiting for backend AI decisions.
##
## Controls:
##   WASD - Move agent
##   Shift - Run (faster movement)
##   1-9 - Trigger tools (scene-specific)
##   Tab - Toggle debug observation overlay
##
## This script should be attached to the same node structure as SimpleAgent:
##   Agent (Node3D with this script)
##     └── MixamoAgentVisual (or AgentVisual)

signal tool_completed(tool_name: String, response: Dictionary)

@export var agent_id: String = "player_agent"
@export var move_speed: float = 5.0
@export var run_speed: float = 10.0
@export var rotation_speed: float = 10.0
@export var show_debug_overlay: bool = true

# References
var visual: Node3D = null
var debug_label: Label3D = null

# Movement state
var velocity := Vector3.ZERO
var is_running := false

# Tool bindings (can be customized per scene)
var tool_bindings := {
	KEY_1: {"tool": "collect", "params": {}},
	KEY_2: {"tool": "move_to", "params": {}},
	KEY_3: {"tool": "idle", "params": {}},
}

# Current observations (for debug display)
var current_observations := {}

func _ready():
	print("PlayerControlledAgent '%s' initializing..." % agent_id)

	# Find visual child
	visual = get_node_or_null("MixamoAgentVisual")
	if visual == null:
		visual = get_node_or_null("AgentVisual")

	if visual:
		print("  Found visual: %s" % visual.name)
	else:
		print("  Warning: No visual found")

	# Create debug overlay
	if show_debug_overlay:
		_create_debug_overlay()

	print("PlayerControlledAgent '%s' ready" % agent_id)
	print("  Controls: WASD=move, Shift=run, Tab=debug, 1-3=tools")

func _create_debug_overlay():
	"""Create a Label3D above the agent to show observations"""
	debug_label = Label3D.new()
	debug_label.name = "DebugLabel"
	debug_label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	debug_label.no_depth_test = true
	debug_label.position = Vector3(0, 3.0, 0)
	debug_label.pixel_size = 0.005
	debug_label.font_size = 24
	debug_label.outline_size = 2
	debug_label.modulate = Color(1, 1, 0.8, 0.9)
	debug_label.text = "Player Agent"
	add_child(debug_label)

func _process(delta):
	_handle_movement(delta)
	_update_debug_overlay()

func _handle_movement(delta):
	"""Handle WASD movement input"""
	var input_dir := Vector3.ZERO

	# Get input
	if Input.is_key_pressed(KEY_W):
		input_dir.z -= 1
	if Input.is_key_pressed(KEY_S):
		input_dir.z += 1
	if Input.is_key_pressed(KEY_A):
		input_dir.x -= 1
	if Input.is_key_pressed(KEY_D):
		input_dir.x += 1

	is_running = Input.is_key_pressed(KEY_SHIFT)

	# Normalize and apply speed
	if input_dir.length() > 0:
		input_dir = input_dir.normalized()
		var speed = run_speed if is_running else move_speed
		velocity = input_dir * speed

		# Move agent
		global_position += velocity * delta

		# Rotate to face movement direction
		var target_rotation = atan2(input_dir.x, input_dir.z)
		rotation.y = lerp_angle(rotation.y, target_rotation, rotation_speed * delta)
	else:
		velocity = Vector3.ZERO

	# Update visual animation
	if visual and visual.has_method("set_movement_velocity"):
		visual.set_movement_velocity(velocity)

func _input(event):
	if event is InputEventKey and event.pressed:
		# Toggle debug overlay
		if event.keycode == KEY_TAB:
			show_debug_overlay = !show_debug_overlay
			if debug_label:
				debug_label.visible = show_debug_overlay
			return

		# Check tool bindings
		if event.keycode in tool_bindings:
			var binding = tool_bindings[event.keycode]
			call_tool(binding.tool, binding.params)

func _update_debug_overlay():
	"""Update the debug label with current observations"""
	if not debug_label or not show_debug_overlay:
		return

	var lines := ["[Player Agent: %s]" % agent_id]
	lines.append("Pos: (%.1f, %.1f, %.1f)" % [global_position.x, global_position.y, global_position.z])
	lines.append("Speed: %.1f %s" % [velocity.length(), "(running)" if is_running else ""])

	# Show observations if available
	if current_observations.has("resources_collected"):
		lines.append("Resources: %d" % current_observations.resources_collected)
	if current_observations.has("damage_taken"):
		lines.append("Damage: %.0f" % current_observations.damage_taken)
	if current_observations.has("nearby_resources"):
		var nearby = current_observations.nearby_resources
		if nearby.size() > 0:
			var closest = nearby[0]
			for r in nearby:
				if r.distance < closest.distance:
					closest = r
			lines.append("Nearest: %s (%.1fm)" % [closest.name, closest.distance])

	debug_label.text = "\n".join(lines)

## SimpleAgent-compatible API (so SceneController can discover this agent)

func perceive(observations: Dictionary):
	"""Receive observations from SceneController"""
	current_observations = observations

func call_tool(tool_name: String, parameters: Dictionary = {}) -> Dictionary:
	"""Execute a tool (logs action, scene handles actual effect)"""
	print("PlayerControlledAgent '%s' calling tool: %s" % [agent_id, tool_name])
	if parameters.size() > 0:
		print("  Params: %s" % parameters)

	# Emit signal for SceneController to handle
	var response = {"success": true, "message": "Tool '%s' triggered by player" % tool_name}
	tool_completed.emit(tool_name, response)

	return response

func set_tool_binding(key: int, tool_name: String, params: Dictionary = {}):
	"""Configure a key binding for a tool"""
	tool_bindings[key] = {"tool": tool_name, "params": params}
