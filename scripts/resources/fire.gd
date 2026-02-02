extends BaseHazard
## Fire hazard - agents pass through but take continuous damage
##
## Fire deals 10 damage per second while agent is overlapping.

func _ready():
	hazard_type = "fire"
	damage_per_tick = 10.0  # 10 DPS
	super._ready()
