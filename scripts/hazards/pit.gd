extends BaseHazard
## Pit hazard - traps agents for N ticks with continuous damage
##
## When an agent falls into a pit:
## 1. Takes initial fall damage (25.0)
## 2. Gets trapped for trap_duration_ticks
## 3. Takes continuous damage while trapped (5 DPS)

signal agent_trapped(agent: BaseAgent, duration: int)
signal agent_escaped(agent: BaseAgent)

@export var trap_duration_ticks: int = 5  # How long agent is trapped
@export var initial_damage: float = 25.0  # Damage on falling in

# Track trapped agents: agent -> remaining ticks
var _trapped_agents: Dictionary = {}

func _ready():
	hazard_type = "pit"
	damage_per_tick = 5.0  # Lower continuous damage than fire
	super._ready()

func _physics_process(delta):
	# Apply continuous damage (from parent)
	super._physics_process(delta)

	# Update trap timers
	var escaped_agents = []
	for agent in _trapped_agents.keys():
		if is_instance_valid(agent):
			_trapped_agents[agent] -= delta
			if _trapped_agents[agent] <= 0:
				escaped_agents.append(agent)

	# Release escaped agents
	for agent in escaped_agents:
		_release_agent(agent)

func _on_body_entered(body: Node):
	super._on_body_entered(body)

	if body is BaseAgent:
		var agent = body as BaseAgent
		# Apply initial fall damage
		agent.take_damage(initial_damage, self, "pit_fall")

		# Trap the agent
		_trapped_agents[agent] = float(trap_duration_ticks)
		agent_trapped.emit(agent, trap_duration_ticks)
		print("Pit '%s': Agent '%s' fell in! Trapped for %d ticks" % [
			name, agent.agent_id, trap_duration_ticks
		])

		# Report trap event to Python backend
		_report_trap_to_backend(agent, _get_current_tick())

func _on_body_exited(body: Node):
	super._on_body_exited(body)

	# If agent exits before trap timer expires, release them
	if body is BaseAgent:
		var agent = body as BaseAgent
		if agent in _trapped_agents:
			_release_agent(agent)

func _release_agent(agent: BaseAgent):
	"""Release an agent from the pit trap"""
	_trapped_agents.erase(agent)
	agent_escaped.emit(agent)
	print("Pit '%s': Agent '%s' escaped!" % [name, agent.agent_id])

func _report_trap_to_backend(agent: BaseAgent, tick: int):
	"""Send trap event to Python backend."""
	var data = {
		"agent_id": agent.agent_id,
		"tick": tick,
		"event_type": "trapped",
		"description": "Fell into pit and trapped",
		"position": [global_position.x, global_position.y, global_position.z],
		"object_name": name,
		"damage_taken": initial_damage,
		"metadata": {"trap_duration": trap_duration_ticks, "hazard_type": "pit"}
	}

	var http = HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(_on_trap_reported.bind(http))

	var json = JSON.stringify(data)
	var headers = ["Content-Type: application/json"]
	var error = http.request("http://127.0.0.1:5000/experience", headers, HTTPClient.METHOD_POST, json)
	if error != OK:
		print("[Pit] Failed to send trap event to backend: ", error)
		http.queue_free()

func _on_trap_reported(_result, _response_code, _headers, _body, http: HTTPRequest):
	"""Clean up HTTP request after trap event is reported"""
	http.queue_free()
