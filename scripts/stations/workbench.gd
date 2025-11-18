extends CraftingStation

## Workbench-specific implementation

func _ready():
	super._ready()

	station_type = "workbench"
	station_name = "Workbench"

	# Set brown/wood color for workbench
	var mesh_instance = $MeshInstance3D
	if mesh_instance:
		var material = StandardMaterial3D.new()
		material.albedo_color = Color(0.55, 0.27, 0.07)  # Brown color
		mesh_instance.material_override = material
