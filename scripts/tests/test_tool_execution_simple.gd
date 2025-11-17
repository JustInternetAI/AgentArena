extends Node
## Simple HTTP-based tool execution test
## Tests the Python IPC server's /tools/execute endpoint directly

var test_count = 0
var tests_passed = 0

func _ready():
	print("=== Simple Tool Execution Test ===")
	print("This test calls the Python IPC server directly using HTTP\n")

	# Wait a moment then start tests
	await get_tree().create_timer(1.0).timeout
	run_tests()

func run_tests():
	print("Starting tool execution tests...")
	print("Make sure Python IPC server is running on http://127.0.0.1:5000\n")

	# Test 1: move_to
	await execute_tool_test("move_to", {
		"target_position": [10.0, 0.0, 5.0],
		"speed": 1.5
	})

	# Test 2: pickup_item
	await execute_tool_test("pickup_item", {
		"item_id": "sword_001"
	})

	# Test 3: stop_movement
	await execute_tool_test("stop_movement", {})

	# Test 4: get_inventory
	await execute_tool_test("get_inventory", {})

	# Test 5: navigate_to
	await execute_tool_test("navigate_to", {
		"target_position": [20.0, 0.0, 10.0]
	})

	print("\n==================================================")
	print("Test Results: %d/%d passed" % [tests_passed, test_count])
	print("==================================================")

	if tests_passed == test_count:
		print("\n✓ All tests PASSED! Tool execution system is working!")
	else:
		print("\n✗ Some tests failed. Check Python server logs.")

func execute_tool_test(tool_name: String, params: Dictionary):
	test_count += 1
	print("\n[Test %d] Executing tool: %s" % [test_count, tool_name])
	print("  Parameters: %s" % [params])

	# Create a new HTTPRequest for this test
	var http_request = HTTPRequest.new()
	add_child(http_request)

	# Build request JSON
	var request_body = {
		"tool_name": tool_name,
		"params": params,
		"agent_id": "test_agent",
		"tick": 0
	}

	var json = JSON.stringify(request_body)
	var headers = ["Content-Type: application/json"]

	# Send request
	var error = http_request.request(
		"http://127.0.0.1:5000/tools/execute",
		headers,
		HTTPClient.METHOD_POST,
		json
	)

	if error != OK:
		print("  ✗ FAILED: HTTP request error: %d" % error)
		http_request.queue_free()
		return

	# Wait for response
	var response = await http_request.request_completed

	var result = response[0]  # HTTPRequest result
	var response_code = response[1]  # HTTP status code
	var response_headers = response[2]
	var body = response[3]

	if result != HTTPRequest.RESULT_SUCCESS:
		print("  ✗ FAILED: Request failed with code: %d" % result)
		http_request.queue_free()
		return

	if response_code != 200:
		print("  ✗ FAILED: HTTP %d" % response_code)
		http_request.queue_free()
		return

	# Parse JSON response
	var body_string = body.get_string_from_utf8()
	var json_parser = JSON.new()
	var parse_error = json_parser.parse(body_string)

	if parse_error != OK:
		print("  ✗ FAILED: JSON parse error")
		print("    Response body: %s" % body_string)
		http_request.queue_free()
		return

	var response_data = json_parser.get_data()

	# Check if tool executed successfully
	if response_data.has("success") and response_data["success"]:
		print("  ✓ PASSED")
		print("    Result: %s" % [response_data.get("result", "none")])
		tests_passed += 1
	else:
		print("  ✗ FAILED: %s" % [response_data.get("error", "Unknown error")])

	# Cleanup
	http_request.queue_free()

func _input(event):
	if event is InputEventKey and event.pressed:
		if event.keycode == KEY_T:
			tests_passed = 0
			test_count = 0
			run_tests()
		elif event.keycode == KEY_Q:
			get_tree().quit()
