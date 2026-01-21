extends Node

var log_file: FileAccess

func write_log(message: String):
	if log_file:
		log_file.store_line(message)
		log_file.flush()
	print(message)

func _ready():
	log_file = FileAccess.open("user://test_timer_minimal.log", FileAccess.WRITE)
	write_log("=== Minimal Timer Test - " + Time.get_datetime_string_from_system() + " ===")
	write_log("Creating timer...")

	var timer = Timer.new()
	timer.wait_time = 5.0
	timer.one_shot = true
	timer.timeout.connect(_on_timeout)
	add_child(timer)
	timer.start()

	write_log("Timer started for 5 seconds")

func _process(delta):
	write_log("_process called, delta=" + str(delta))

func _on_timeout():
	write_log("TIMER TIMEOUT - 5 seconds elapsed!")
	if log_file:
		log_file.close()
	get_tree().quit()
