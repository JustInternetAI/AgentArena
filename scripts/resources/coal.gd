extends BaseResource

## Coal resource

func _ready():
	super._ready()

	resource_type = "coal"
	resource_value = 1

	# Set black color for coal
	var mesh_instance = $MeshInstance3D
	if mesh_instance:
		var material = StandardMaterial3D.new()
		material.albedo_color = Color(0.1, 0.1, 0.1)  # Almost black
		material.roughness = 0.9  # Very rough surface
		mesh_instance.material_override = material
