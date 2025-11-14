extends BaseResource

## Wood resource

func _ready():
	super._ready()

	resource_type = "wood"
	resource_value = 1

	# Set brown color for wood
	var mesh_instance = $MeshInstance3D
	if mesh_instance:
		var material = StandardMaterial3D.new()
		material.albedo_color = Color(0.6, 0.4, 0.2)  # Brown
		mesh_instance.material_override = material
