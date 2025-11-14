extends BaseResource

## Iron Ore resource

func _ready():
	super._ready()

	resource_type = "iron_ore"
	resource_value = 1

	# Set gray/metallic color for iron ore
	var mesh_instance = $MeshInstance3D
	if mesh_instance:
		var material = StandardMaterial3D.new()
		material.albedo_color = Color(0.5, 0.5, 0.5)  # Gray
		material.metallic = 0.6
		material.roughness = 0.4
		mesh_instance.material_override = material
