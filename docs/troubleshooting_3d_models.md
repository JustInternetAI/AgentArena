# Troubleshooting 3D Models in Godot

## Problem: GLB Imports as Empty Node3D (No Mesh)

If your GLB file imports into Godot as just a Node3D without any MeshInstance3D children:

### Causes:
1. **Empty GLB file** - The file doesn't actually contain mesh data
2. **Corrupted file** - Download was incomplete or file is damaged
3. **Incompatible format** - GLB uses features Godot doesn't support
4. **Export settings** - The 3D software exported incorrectly

### Solutions:

#### 1. Verify the GLB File
- Open the GLB in a 3D viewer like [gltf-viewer.donmccurdy.com](https://gltf-viewer.donmccurdy.com/)
- Or use Blender: File → Import → glTF 2.0 (.glb/.gltf)
- Check if you can actually see the mesh

#### 2. Get a Known-Good Model
Download from trusted sources that work well with Godot:

**Kenney Assets (Recommended):**
- Visit [kenney.nl/assets](https://kenney.nl/assets)
- Download "Food Kit" or "Nature Kit"
- Use the GLB files directly - they're pre-configured for game engines

**Example: Getting an Apple Model from Kenney**
1. Go to https://kenney.nl/assets/food-kit
2. Download the kit (free, CC0 license)
3. Extract and find `apple.glb` in the models folder
4. Copy to `assets/models/resources/apple.glb`
5. Godot will auto-import it correctly

#### 3. Re-export from Blender
If you have a model in another format:

1. Open in Blender
2. File → Export → glTF 2.0 (.glb)
3. Export settings:
   - Format: **GLB**
   - Include: ✓ Selected Objects (or All if you want everything)
   - Transform: ✓ +Y Up
   - Geometry: ✓ Apply Modifiers, ✓ UVs, ✓ Normals
   - Materials: ✓ Export Materials
   - Compression: None (or Draco if you know what you're doing)
4. Export and replace the GLB file

#### 4. Use Procedural Meshes as Fallback
If you can't get a good GLB immediately, use Godot's built-in meshes:

```gdscript
# In your .tscn file:
[sub_resource type="SphereMesh" id="SphereMesh_apple"]
radius = 0.15
height = 0.3

[node name="Visual" type="MeshInstance3D" parent="."]
mesh = SubResource("SphereMesh_apple")
```

This is what we're currently using for the berry - it works perfectly fine for prototyping!

## Godot Import Settings

For GLB files, these settings usually work:

```
[params]
meshes/ensure_tangents=true
meshes/generate_lods=false
meshes/create_shadow_meshes=false
materials/extract=1
materials/extract_path="res://assets/models/resources/"
gltf/embedded_image_handling=0
```

## Testing a GLB File

Quick test in Godot:
1. Drag the GLB file directly into a 3D scene
2. Look in the Scene tree - you should see:
   - Node3D (root)
     - MeshInstance3D (the actual geometry)
3. If you only see Node3D with no children, the GLB is empty/invalid

## Recommended Workflow

1. **Use Kenney assets** for prototyping (they always work)
2. **Verify GLB in web viewer** before using in Godot
3. **Keep textures next to GLB files** (industry standard)
4. **Test import** by dragging into a scene first
5. **Use procedural meshes** for placeholders if needed

## Current Status: Apple Scene

The apple scene is now using the **proper Kenney apple.glb model** with textures!

Location: `scenes/resources/apple.tscn` instances `assets/models/kenney_food_kit/Models/apple.glb`

The Kenney Food Kit provides 200+ food models, all properly textured and ready to use. See `assets/models/kenney_food_kit/README.md` for the complete list.

---

**Bottom line:** Kenney assets work great when you preserve their original folder structure!
