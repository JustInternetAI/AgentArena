extends Node

@onready var simulation_manager = $SimulationManager
@onready var agent = $Agent
@onready var label = $UI/Label

var tick_count = 0

func _ready():
	print("Test Arena Ready!")

	# Connect simulation signals
	simulation_manager.simulation_started.connect(_on_simulation_started)
	simulation_manager.simulation_stopped.connect(_on_simulation_stopped)
	simulation_manager.tick_advanced.connect(_on_tick_advanced)

	# Connect agent signals
	agent.action_decided.connect(_on_agent_action_decided)
	agent.perception_received.connect(_on_agent_perception_received)

	# Set up agent
	agent.agent_id = "test_agent_001"

	print("SimulationManager: ", simulation_manager)
	print("Agent: ", agent)
	print("Agent ID: ", agent.agent_id)

func _input(event):
	if event is InputEventKey and event.pressed:
		if event.keycode == KEY_SPACE:
			if simulation_manager.is_running:
				simulation_manager.stop_simulation()
			else:
				simulation_manager.start_simulation()
		elif event.keycode == KEY_R:
			simulation_manager.reset_simulation()
		elif event.keycode == KEY_S:
			simulation_manager.step_simulation()
		elif event.keycode == KEY_T:
			test_agent()

func _process(_delta):
	if simulation_manager.is_running:
		label.text = "Agent Arena Test Scene (RUNNING)
Tick: %d
Agent ID: %s
Press SPACE to stop
Press S to step
Press R to reset
Press T to test agent" % [simulation_manager.current_tick, agent.agent_id]
	else:
		label.text = "Agent Arena Test Scene (STOPPED)
Tick: %d
Agent ID: %s
Press SPACE to start
Press S to step
Press R to reset
Press T to test agent" % [simulation_manager.current_tick, agent.agent_id]

func test_agent():
	print("Testing agent functions...")

	# Test perception
	var obs = {
		"position": Vector3(10, 0, 5),
		"health": 100,
		"nearby_objects": ["tree", "rock", "water"]
	}
	agent.perceive(obs)

	# Test decision
	var action = agent.decide_action()
	print("Agent decided action: ", action)

	# Test memory
	agent.store_memory("test_key", "test_value")
	var retrieved = agent.retrieve_memory("test_key")
	print("Retrieved memory: ", retrieved)

	# Test tool call
	var tool_result = agent.call_tool("move", {"direction": "north", "distance": 5})
	print("Tool result: ", tool_result)

func _on_simulation_started():
	print("✓ Simulation started!")

func _on_simulation_stopped():
	print("✓ Simulation stopped!")

func _on_tick_advanced(tick):
	tick_count += 1
	if tick_count % 60 == 0:  # Print every 60 ticks (1 second)
		print("Tick: ", tick)

func _on_agent_action_decided(action):
	print("Agent action: ", action)

func _on_agent_perception_received(observations):
	print("Agent perceived: ", observations)
