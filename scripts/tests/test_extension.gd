extends Node

# Simple test to verify GDExtension classes are available

func _ready():
	print("=== Testing GDExtension Classes ===")

	# Test each class
	var tests = [
		["SimulationManager", SimulationManager],
		["EventBus", EventBus],
		["Agent", Agent],
		["ToolRegistry", ToolRegistry],
		["IPCClient", IPCClient]
	]

	var all_passed = true
	for test_item in tests:
		var test_name = test_item[0]
		var type = test_item[1]

		var instance = type.new()
		if instance:
			print("  ✓ ", test_name, " - OK")
			# RefCounted objects are automatically freed, don't call free()
		else:
			print("  ✗ ", test_name, " - FAILED")
			all_passed = false

	print("=== Test Complete ===")
	if all_passed:
		print("All classes loaded successfully!")
	else:
		print("Some classes failed to load - rebuild may be needed")

	get_tree().quit()
