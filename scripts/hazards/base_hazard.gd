extends Area3D
class_name BaseHazard
## Base class for hazards that damage agents on contact
##
## Hazards use Area3D so agents pass through them while taking damage.
## Subclasses should set hazard_type and damage_per_tick in _ready().

signal agent_entered(agent: BaseAgent)
signal agent_exited(agent: BaseAgent)
signal damage_applied(agent: BaseAgent, amount: float)

@export var hazard_type: String = "unknown"
@export var damage_per_tick: float = 10.0  # Damage per second while overlapping

# Agents currently inside this hazard
var _overlapping_agents: Array[BaseAgent] = []

# Damage reporting throttling (avoid flooding Python backend)
var _last_damage_report_tick: int = -1
const DAMAGE_REPORT_INTERVAL: int = 10  # Report damage every N ticks

func _ready():
	# Configure collision
	# Layer 3 = Hazards (bit value 4)
	# Mask = Agents layer 4 (bit value 8)
	collision_layer = 4  # Hazard layer
	collision_mask = 8   # Detect agents

	# Connect signals
	body_entered.connect(_on_body_entered)
	body_exited.connect(_on_body_exited)

	print("BaseHazard '%s' ready (type: %s, dps: %.1f)" % [name, hazard_type, damage_per_tick])

func _physics_process(delta):
	"""Apply damage to all overlapping agents each physics tick"""
	for agent in _overlapping_agents:
		if agent and is_instance_valid(agent) and agent.is_alive():
			var tick_damage = damage_per_tick * delta
			agent.take_damage(tick_damage, self, hazard_type)
			damage_applied.emit(agent, tick_damage)

			# Report to Python (throttled to avoid flooding)
			var current_tick = _get_current_tick()
			if current_tick - _last_damage_report_tick >= DAMAGE_REPORT_INTERVAL:
				_report_damage_to_backend(agent, tick_damage, current_tick)
				_last_damage_report_tick = current_tick

func _on_body_entered(body: Node):
	"""Called when a body enters the hazard area"""
	if body is BaseAgent:
		var agent = body as BaseAgent
		if agent not in _overlapping_agents:
			_overlapping_agents.append(agent)
			agent_entered.emit(agent)
			print("Hazard '%s': Agent '%s' entered" % [name, agent.agent_id])

func _on_body_exited(body: Node):
	"""Called when a body exits the hazard area"""
	if body is BaseAgent:
		var agent = body as BaseAgent
		_overlapping_agents.erase(agent)
		agent_exited.emit(agent)
		print("Hazard '%s': Agent '%s' exited" % [name, agent.agent_id])

func _report_damage_to_backend(agent: BaseAgent, damage: float, tick: int):
	"""Send damage event to Python backend."""
	var data = {
		"agent_id": agent.agent_id,
		"tick": tick,
		"event_type": "damage",
		"description": "Took damage from " + hazard_type,
		"position": [agent.global_position.x, agent.global_position.y, agent.global_position.z],
		"object_name": name,
		"damage_taken": damage,
		"metadata": {"hazard_type": hazard_type, "agent_health": agent.current_health}
	}

	var http = HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(_on_damage_reported.bind(http))

	var json = JSON.stringify(data)
	var headers = ["Content-Type: application/json"]
	var error = http.request("http://127.0.0.1:5000/experience", headers, HTTPClient.METHOD_POST, json)
	if error != OK:
		print("[BaseHazard] Failed to send damage to backend: ", error)
		http.queue_free()

func _on_damage_reported(_result, _response_code, _headers, _body, http: HTTPRequest):
	"""Clean up HTTP request after damage is reported"""
	http.queue_free()

func _get_current_tick() -> int:
	"""Get current simulation tick from SimulationManager"""
	var node = get_parent()
	while node:
		var sim = node.get_node_or_null("SimulationManager")
		if sim and "current_tick" in sim:
			return sim.current_tick
		node = node.get_parent()
	return 0
