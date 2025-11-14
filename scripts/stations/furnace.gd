extends CraftingStation

## Furnace-specific implementation

func _ready():
	super._ready()

	station_type = "furnace"
	station_name = "Furnace"

	# Set orange/red color for furnace
	var mesh_instance = $MeshInstance3D
	if mesh_instance:
		var material = StandardMaterial3D.new()
		material.albedo_color = Color(1.0, 0.4, 0.0)  # Orange color (RGB)
		mesh_instance.material_override = material
