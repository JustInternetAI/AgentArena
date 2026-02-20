extends CraftingStation

## Anvil-specific implementation

func _ready():
	super._ready()

	station_type = "anvil"
	station_name = "Anvil"

	# Set dark gray/metallic color for anvil
	var mesh_instance = $AnvilModel
	if mesh_instance:
		var material = StandardMaterial3D.new()
		material.albedo_color = Color(0.25, 0.25, 0.25)  # Dark gray
		material.metallic = 0.8  # Make it look metallic
		material.roughness = 0.3
		mesh_instance.material_override = material
