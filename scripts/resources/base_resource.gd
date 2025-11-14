extends Area3D
class_name BaseResource

## Base class for collectible resources

@export var resource_type: String = "unknown"
@export var resource_value: int = 1
@export var auto_collect: bool = false

signal collected(collector: Node)

var is_collected: bool = false

func _ready():
	# Connect to body entered if auto-collect is enabled
	if auto_collect:
		body_entered.connect(_on_body_entered)

func collect(collector: Node) -> bool:
	if is_collected:
		return false

	is_collected = true
	collected.emit(collector)

	# Hide the resource
	visible = false

	# Disable collision
	monitoring = false
	monitorable = false

	return true

func reset():
	is_collected = false
	visible = true
	monitoring = true
	monitorable = true

func _on_body_entered(body: Node):
	if auto_collect and not is_collected:
		collect(body)
