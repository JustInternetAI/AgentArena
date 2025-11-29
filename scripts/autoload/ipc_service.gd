extends Node
## Global IPC Service - Singleton for communicating with Python backend
##
## This autoload singleton manages the persistent connection to the Python IPC server.
## It wraps the IPCClient C++ node and provides a clean signal-based API.
##
## Usage:
##   IPCService.execute_tool(agent_id, "move_to", {"target": [1, 2, 3]})
##   IPCService.tool_response.connect(_on_tool_response)

signal connected_to_server
signal connection_failed(error: String)
signal tool_response(agent_id: String, tool_name: String, response: Dictionary)
signal tick_response(agent_id: String, response: Dictionary)

var ipc_client: IPCClient
var server_url := "http://127.0.0.1:5000"
var is_ready := false

func _ready():
	print("=== IPCService Initializing ===")

	# Create the C++ IPCClient node
	ipc_client = IPCClient.new()
	ipc_client.name = "IPCClient"
	ipc_client.server_url = server_url
	add_child(ipc_client)

	# Connect signals from IPCClient
	ipc_client.response_received.connect(_on_ipc_response_received)
	ipc_client.connection_failed.connect(_on_ipc_connection_failed)

	print("IPCService: IPCClient created")

	is_ready = true
	print("=== IPCService Ready ===")

	# Auto-connect to backend using a short timer to ensure everything is fully initialized
	print("IPCService: Will auto-connect to backend in 0.5 seconds...")
	var connect_timer = Timer.new()
	connect_timer.wait_time = 0.5
	connect_timer.one_shot = true
	connect_timer.timeout.connect(_connect_to_backend)
	add_child(connect_timer)
	connect_timer.start()

func _connect_to_backend():
	"""Internal function to connect to backend (called after short delay)"""
	if not ipc_client:
		push_error("IPCClient not initialized!")
		return

	print("IPCService: Connecting to backend now...")
	ipc_client.connect_to_server(server_url)

func execute_tool(agent_id: String, tool_name: String, parameters: Dictionary) -> Dictionary:
	"""Execute a tool for a specific agent"""
	if not is_ready:
		push_error("IPCService not ready yet!")
		return {"success": false, "error": "Service not ready"}

	if not ipc_client:
		push_error("IPCClient not initialized!")
		return {"success": false, "error": "Client not initialized"}

	# Add agent_id to parameters
	var params_with_agent = parameters.duplicate()
	params_with_agent["agent_id"] = agent_id

	# Execute through IPCClient
	return ipc_client.execute_tool(tool_name, params_with_agent)

func send_tick(agent_id: String, tick: int, perceptions: Array) -> void:
	"""Send a tick update for a specific agent"""
	if not is_ready:
		push_error("IPCService not ready yet!")
		return

	if not ipc_client:
		push_error("IPCClient not initialized!")
		return

	ipc_client.send_tick_request(tick, perceptions)

func is_backend_connected() -> bool:
	"""Check if connected to Python backend"""
	if not ipc_client:
		return false
	return ipc_client.is_server_connected()

func _on_ipc_response_received(response: Dictionary):
	"""Handle response from IPCClient"""
	print("[IPCService] Response received: ", response)

	# Check if this is a connection success response (health check)
	if response.has("status") and (response["status"] == "healthy" or response["status"] == "ok"):
		print("[IPCService] Connected to Python backend successfully!")
		connected_to_server.emit()
		return

	# Parse response and emit appropriate signal
	if response.has("tool_name"):
		# Tool execution response
		var agent_id = response.get("agent_id", "unknown")
		var tool_name = response.get("tool_name", "unknown")
		tool_response.emit(agent_id, tool_name, response)
	elif response.has("tick"):
		# Tick response
		var agent_id = response.get("agent_id", "unknown")
		tick_response.emit(agent_id, response)
	else:
		# Generic response
		print("[IPCService] Unknown response type: ", response)

func _on_ipc_connection_failed(error: String):
	"""Handle connection failure"""
	push_error("[IPCService] Connection failed: " + error)
	connection_failed.emit(error)

func _notification(what):
	if what == NOTIFICATION_PREDELETE:
		print("IPCService shutting down...")
		if ipc_client:
			ipc_client.disconnect_from_server()
