extends Node3D

## Team Capture Benchmark Scene
## Goal: Multi-agent teams compete to capture and hold objectives
## Metrics: Objectives captured, team coordination, individual contribution, win rate

@onready var simulation_manager = $SimulationManager
@onready var event_bus = $EventBus
@onready var tool_registry = $ToolRegistry
@onready var metrics_label = $UI/MetricsLabel

# Scene configuration
const CAPTURE_RADIUS = 3.0
const CAPTURE_TIME = 5.0  # Seconds to capture
const POINTS_PER_CAPTURE = 10
const POINTS_PER_HOLD_TICK = 1
const MAX_POINTS = 100
const COMMUNICATION_RADIUS = 15.0

# Teams
var blue_team = []
var red_team = []

# Capture points
var capture_points = []

# Metrics
var blue_score = 0
var red_score = 0
var objectives_captured = {"blue": 0, "red": 0}
var total_captures = 0
var team_blue_contributions = {}
var team_red_contributions = {}
var start_time = 0.0
var scene_completed = false
var winning_team = ""

func _ready():
	print("Team Capture Benchmark Scene Ready!")

	# Verify C++ nodes
	if simulation_manager == null:
		push_error("GDExtension nodes not found!")
		return

	# Connect simulation signals
	simulation_manager.simulation_started.connect(_on_simulation_started)
	simulation_manager.simulation_stopped.connect(_on_simulation_stopped)
	simulation_manager.tick_advanced.connect(_on_tick_advanced)

	# Register tools
	_register_tools()

	# Initialize teams and capture points
	_initialize_scene()

	print("Blue team agents: ", blue_team.size())
	print("Red team agents: ", red_team.size())
	print("Capture points: ", capture_points.size())

func _register_tools():
	"""Register available tools for agents"""
	if tool_registry == null:
		return

	# Movement
	tool_registry.register_tool("move_to", {
		"name": "move_to",
		"description": "Move to a target position",
		"parameters": {
			"target_x": {"type": "float"},
			"target_y": {"type": "float"},
			"target_z": {"type": "float"}
		}
	})

	# Capture
	tool_registry.register_tool("capture_point", {
		"name": "capture_point",
		"description": "Attempt to capture a nearby point",
		"parameters": {
			"point_name": {"type": "string"}
		}
	})

	# Communication
	tool_registry.register_tool("send_message", {
		"name": "send_message",
		"description": "Send a message to nearby teammates",
		"parameters": {
			"message": {"type": "string"},
			"target_agent": {"type": "string"}
		}
	})

	# Query
	tool_registry.register_tool("query_team", {
		"name": "query_team",
		"description": "Get information about teammates",
		"parameters": {}
	})

	tool_registry.register_tool("query_objectives", {
		"name": "query_objectives",
		"description": "Get status of capture points",
		"parameters": {}
	})

func _initialize_scene():
	"""Initialize teams and capture points"""
	blue_team.clear()
	red_team.clear()
	capture_points.clear()
	team_blue_contributions.clear()
	team_red_contributions.clear()

	# Initialize Blue Team
	var blue_team_node = $TeamBlue
	for child in blue_team_node.get_children():
		if child.get_class() == "Agent":
			child.agent_id = "blue_%s" % child.name
			blue_team.append({
				"agent": child,
				"id": child.agent_id,
				"position": child.global_position,
				"team": "blue"
			})
			team_blue_contributions[child.agent_id] = {
				"captures": 0,
				"assists": 0,
				"messages_sent": 0
			}
			# Connect agent signals
			child.action_decided.connect(_on_agent_action_decided.bind(child.agent_id))

	# Initialize Red Team
	var red_team_node = $TeamRed
	for child in red_team_node.get_children():
		if child.get_class() == "Agent":
			child.agent_id = "red_%s" % child.name
			red_team.append({
				"agent": child,
				"id": child.agent_id,
				"position": child.global_position,
				"team": "red"
			})
			team_red_contributions[child.agent_id] = {
				"captures": 0,
				"assists": 0,
				"messages_sent": 0
			}
			# Connect agent signals
			child.action_decided.connect(_on_agent_action_decided.bind(child.agent_id))

	# Initialize Capture Points
	var points_node = $CapturePoints
	for child in points_node.get_children():
		if child.has_method("get_state"):
			# This is a CapturePoint scene
			var state = child.get_state()
			capture_points.append(state)

func _process(_delta):
	_update_metrics_ui()

func _input(event):
	if simulation_manager == null:
		return

	if event is InputEventKey and event.pressed:
		if event.keycode == KEY_SPACE:
			if simulation_manager.is_running:
				simulation_manager.stop_simulation()
			else:
				simulation_manager.start_simulation()
		elif event.keycode == KEY_R:
			_reset_scene()
		elif event.keycode == KEY_S:
			simulation_manager.step_simulation()
		elif event.keycode == KEY_M:
			_print_detailed_metrics()

func _on_simulation_started():
	print("✓ Team capture benchmark started!")
	start_time = Time.get_ticks_msec() / 1000.0
	scene_completed = false

func _on_simulation_stopped():
	print("✓ Team capture benchmark stopped!")
	_print_final_metrics()

func _on_tick_advanced(tick: int):
	# Update agent positions
	_update_agent_positions()

	# Update capture point status
	_update_capture_points(1.0 / 60.0)  # Assuming 60 ticks per second

	# Award points for holding objectives
	_award_holding_points()

	# Send perception to all agents
	_send_perception_to_agents()

	# Check win condition
	if blue_score >= MAX_POINTS or red_score >= MAX_POINTS:
		_complete_scene()

func _update_agent_positions():
	"""Update stored agent positions"""
	for agent_data in blue_team:
		agent_data.position = agent_data.agent.global_position

	for agent_data in red_team:
		agent_data.position = agent_data.agent.global_position

func _update_capture_points(delta: float):
	"""Update capture progress for all points"""
	for point in capture_points:
		# Find agents at this point
		point.agents_present.clear()
		var blue_count = 0
		var red_count = 0

		for agent_data in blue_team:
			var dist = agent_data.position.distance_to(point.position)
			if dist <= CAPTURE_RADIUS:
				point.agents_present.append(agent_data)
				blue_count += 1

		for agent_data in red_team:
			var dist = agent_data.position.distance_to(point.position)
			if dist <= CAPTURE_RADIUS:
				point.agents_present.append(agent_data)
				red_count += 1

		# Update agents_present on the node itself for visual feedback
		if point.node:
			point.node.agents_present = point.agents_present

		# Determine capturing team
		var dominant_team = null
		if blue_count > red_count:
			dominant_team = "blue"
		elif red_count > blue_count:
			dominant_team = "red"

		# Update capture progress
		if dominant_team != null and point.owner != dominant_team:
			# Capturing
			if point.capturing_team != dominant_team:
				point.capturing_team = dominant_team
				point.capture_progress = 0.0

			point.capture_progress += delta

			# Update visual feedback on the node
			if point.node:
				point.node.set_capture_progress(point.capture_progress / CAPTURE_TIME, dominant_team)

			if point.capture_progress >= CAPTURE_TIME:
				_capture_point(point, dominant_team)
		else:
			# Reset progress if contested or no one present
			point.capturing_team = null
			point.capture_progress = 0.0

			# Update visual feedback
			if point.node:
				point.node.reset_capture()

func _capture_point(point: Dictionary, team: String):
	"""Capture a point for a team"""
	var previous_owner = point.owner
	point.owner = team
	point.capture_progress = 0.0
	point.capturing_team = null

	# Update visual on the node
	if point.node:
		point.node.set_owner_team(team)
		point.node.reset_capture()

	# Award points
	if team == "blue":
		blue_score += POINTS_PER_CAPTURE
		objectives_captured.blue += 1
	else:
		red_score += POINTS_PER_CAPTURE
		objectives_captured.red += 1

	total_captures += 1

	# Award contributions to agents present
	for agent_data in point.agents_present:
		if agent_data.team == team:
			var contributions = team_blue_contributions if team == "blue" else team_red_contributions
			contributions[agent_data.id].captures += 1

	# Record event
	if event_bus != null:
		event_bus.emit_event({
			"type": "point_captured",
			"point_name": point.name,
			"team": team,
			"previous_owner": previous_owner,
			"tick": simulation_manager.current_tick
		})

	print("✓ %s team captured %s! (Score: Blue %d, Red %d)" %
		[team.capitalize(), point.name, blue_score, red_score])

func _award_holding_points():
	"""Award points for holding capture points"""
	for point in capture_points:
		if point.owner == "blue":
			blue_score += POINTS_PER_HOLD_TICK
		elif point.owner == "red":
			red_score += POINTS_PER_HOLD_TICK

func _send_perception_to_agents():
	"""Send observations to all agents"""
	# Blue team perception
	for agent_data in blue_team:
		var obs = _build_agent_observation(agent_data, blue_team, red_team)
		agent_data.agent.perceive(obs)

	# Red team perception
	for agent_data in red_team:
		var obs = _build_agent_observation(agent_data, red_team, blue_team)
		agent_data.agent.perceive(obs)

func _build_agent_observation(agent_data: Dictionary, allies: Array, enemies: Array) -> Dictionary:
	"""Build observation for an agent"""
	var agent_pos = agent_data.position

	# Find nearby allies
	var nearby_allies = []
	for ally in allies:
		if ally.id == agent_data.id:
			continue
		var dist = agent_pos.distance_to(ally.position)
		if dist <= COMMUNICATION_RADIUS:
			nearby_allies.append({
				"id": ally.id,
				"position": ally.position,
				"distance": dist
			})

	# Find visible enemies (simplified - just distance check)
	var nearby_enemies = []
	for enemy in enemies:
		var dist = agent_pos.distance_to(enemy.position)
		if dist <= 20.0:  # Vision range
			nearby_enemies.append({
				"id": enemy.id,
				"position": enemy.position,
				"distance": dist
			})

	# Capture point status
	var objectives = []
	for point in capture_points:
		var dist = agent_pos.distance_to(point.position)
		objectives.append({
			"name": point.name,
			"position": point.position,
			"owner": point.owner,
			"capturing_team": point.capturing_team,
			"capture_progress": point.capture_progress,
			"distance": dist
		})

	return {
		"agent_id": agent_data.id,
		"team": agent_data.team,
		"position": agent_pos,
		"team_score": blue_score if agent_data.team == "blue" else red_score,
		"enemy_score": red_score if agent_data.team == "blue" else blue_score,
		"nearby_allies": nearby_allies,
		"nearby_enemies": nearby_enemies,
		"objectives": objectives,
		"tick": simulation_manager.current_tick
	}

func _on_agent_action_decided(action, agent_id: String):
	"""Handle agent action decisions"""
	# Actions are handled through the tool system
	# This is just for logging/debugging
	pass

func _complete_scene():
	"""Complete the benchmark"""
	if scene_completed:
		return

	scene_completed = true
	simulation_manager.stop_simulation()

	# Determine winner
	if blue_score > red_score:
		winning_team = "Blue"
	elif red_score > blue_score:
		winning_team = "Red"
	else:
		winning_team = "Draw"

	print("\n" + "=".repeat(50))
	print("✓ TEAM CAPTURE BENCHMARK COMPLETED!")
	print("Winner: %s Team!" % winning_team)
	_print_final_metrics()
	print("=".repeat(50))

func _print_final_metrics():
	"""Print final benchmark metrics"""
	var elapsed_time = (Time.get_ticks_msec() / 1000.0) - start_time

	print("\nFinal Metrics:")
	print("  Final Score: Blue %d - Red %d" % [blue_score, red_score])
	print("  Objectives Captured: Blue %d - Red %d" % [objectives_captured.blue, objectives_captured.red])
	print("  Total Captures: %d" % total_captures)
	print("  Time Elapsed: %.2f seconds" % elapsed_time)
	print("  Winner: %s" % winning_team)
	print("\nTeam Blue Contributions:")
	for agent_id in team_blue_contributions.keys():
		var contrib = team_blue_contributions[agent_id]
		print("  %s - Captures: %d, Assists: %d" % [agent_id, contrib.captures, contrib.assists])
	print("\nTeam Red Contributions:")
	for agent_id in team_red_contributions.keys():
		var contrib = team_red_contributions[agent_id]
		print("  %s - Captures: %d, Assists: %d" % [agent_id, contrib.captures, contrib.assists])
	print("  Team Coordination Score: %.2f" % _calculate_coordination_score())

func _calculate_coordination_score() -> float:
	"""Calculate team coordination metric"""
	# Measure how evenly distributed contributions are
	# Perfect coordination = equal contributions from all agents
	if total_captures == 0:
		return 0.0

	var blue_variance = _calculate_contribution_variance(team_blue_contributions)
	var red_variance = _calculate_contribution_variance(team_red_contributions)

	# Lower variance = better coordination
	var avg_variance = (blue_variance + red_variance) / 2.0
	return max(100.0 - avg_variance * 10.0, 0.0)

func _calculate_contribution_variance(contributions: Dictionary) -> float:
	"""Calculate variance in contributions"""
	if contributions.size() == 0:
		return 0.0

	var values = []
	for agent_id in contributions.keys():
		values.append(contributions[agent_id].captures)

	var mean = 0.0
	for val in values:
		mean += val
	mean /= values.size()

	var variance = 0.0
	for val in values:
		variance += pow(val - mean, 2)
	variance /= values.size()

	return variance

func _print_detailed_metrics():
	"""Print detailed metrics during simulation"""
	print("\n--- Current Status ---")
	print("Score: Blue %d - Red %d" % [blue_score, red_score])
	print("Capture Points:")
	for point in capture_points:
		var status = point.owner
		if point.capturing_team != null:
			status = "%s (capturing: %s %.1f%%)" % [
				point.owner,
				point.capturing_team,
				(point.capture_progress / CAPTURE_TIME) * 100.0
			]
		print("  %s: %s (%d agents)" % [point.name, status, point.agents_present.size()])

func _update_metrics_ui():
	"""Update metrics display"""
	if metrics_label == null:
		return

	var elapsed_time = 0.0
	if simulation_manager.is_running:
		elapsed_time = (Time.get_ticks_msec() / 1000.0) - start_time

	var status = "RUNNING" if simulation_manager.is_running else "STOPPED"
	if scene_completed:
		status = "COMPLETED - %s WINS!" % winning_team.to_upper()

	# Count controlled objectives
	var blue_controlled = 0
	var red_controlled = 0
	for point in capture_points:
		if point.owner == "blue":
			blue_controlled += 1
		elif point.owner == "red":
			red_controlled += 1

	metrics_label.text = "Team Capture Benchmark [%s]
Tick: %d

SCORE:
  Blue Team: %d
  Red Team: %d

OBJECTIVES:
  Blue Controlled: %d
  Red Controlled: %d
  Total Captures: Blue %d, Red %d

TIME: %.2f s

Press SPACE to start/stop
Press R to reset
Press M for detailed metrics" % [
		status,
		simulation_manager.current_tick,
		blue_score,
		red_score,
		blue_controlled,
		red_controlled,
		objectives_captured.blue,
		objectives_captured.red,
		elapsed_time
	]

func _reset_scene():
	"""Reset the scene"""
	print("Resetting team capture scene...")

	simulation_manager.reset_simulation()

	# Reset metrics
	blue_score = 0
	red_score = 0
	objectives_captured = {"blue": 0, "red": 0}
	total_captures = 0
	start_time = 0.0
	scene_completed = false
	winning_team = ""

	# Reset contributions
	for agent_id in team_blue_contributions.keys():
		team_blue_contributions[agent_id] = {
			"captures": 0,
			"assists": 0,
			"messages_sent": 0
		}
	for agent_id in team_red_contributions.keys():
		team_red_contributions[agent_id] = {
			"captures": 0,
			"assists": 0,
			"messages_sent": 0
		}

	# Reset capture points
	for point in capture_points:
		point.owner = "neutral"
		point.capture_progress = 0.0
		point.capturing_team = null
		point.agents_present.clear()

		# Update visual on the node
		if point.node:
			point.node.set_owner_team("neutral")
			point.node.reset_capture()

	# Reset agent positions
	var blue_spawn_positions = [Vector3(-20, 1, -20), Vector3(-22, 1, -18), Vector3(-18, 1, -22)]
	for i in range(blue_team.size()):
		if i < blue_spawn_positions.size():
			blue_team[i].agent.global_position = blue_spawn_positions[i]

	var red_spawn_positions = [Vector3(20, 1, 20), Vector3(22, 1, 18), Vector3(18, 1, 22)]
	for i in range(red_team.size()):
		if i < red_spawn_positions.size():
			red_team[i].agent.global_position = red_spawn_positions[i]

	print("✓ Scene reset!")
