# Getting 3D Assets for Agent Arena

Guide for obtaining 3D meshes for benchmark scene objects.

## Quick Start (5 minutes)

1. **Visit Kenney.nl**
   - Go to https://kenney.nl/assets
   - Download these free packs:
     - Nature Kit (rocks, trees, wood)
     - Food Kit (berries, fruits)
     - Furniture Kit (workbenches, tables)

2. **Import to Godot**
   ```
   - Download ZIP
   - Extract GLB files
   - Drag GLB files into Godot's FileSystem (res://assets/models/)
   - Godot auto-imports them
   ```

3. **Use in Scenes**
   ```
   - Open your scene (e.g., foraging.tscn)
   - Drag GLB from FileSystem into scene tree
   - Position and scale as needed
   ```

## Asset Sources by Item Type

### Resources
| Item | Recommended Source | Search Term |
|------|-------------------|-------------|
| Berries | Kenney Food Kit | "berry", "fruit" |
| Wood | Kenney Nature Kit | "log", "wood" |
| Stone/Rocks | Kenney Nature Kit | "rock", "stone" |
| Iron Ore | Poly Pizza | "ore", "crystal", "metal" |
| Coal | Quaternius | "coal", "rock dark" |

### Crafting Stations
| Station | Recommended Source | Alternative |
|---------|-------------------|-------------|
| Workbench | Kenney Furniture Kit | Poly Pizza "workbench" |
| Anvil | Poly Pizza | Search "anvil" or "blacksmith" |
| Furnace | Quaternius RPG Kit | Poly Pizza "furnace" |

### Agents/Characters
| Type | Source | Notes |
|------|--------|-------|
| Humanoid | Kenney Character Kit | Simple, low-poly |
| Robot | Quaternius | Sci-fi style available |
| Custom | Current capsule mesh | Already working! |

## Step-by-Step: Adding a Berry Mesh

1. **Download Kenney Food Kit**
   - URL: https://kenney.nl/assets/food-kit
   - Click "Download" (free, no account needed)
   - Extract ZIP

2. **Import to Godot**
   ```
   - Create folder: res://assets/models/food/
   - Copy berry.glb to that folder
   - Godot imports automatically
   ```

3. **Update Berry Scene**
   ```
   - Open scenes/resources/berry.tscn
   - Add MeshInstance3D node
   - In Inspector → Mesh → Load berry.glb
   - Adjust transform/scale
   ```

4. **Test**
   - Run foraging scene
   - Berries now use real 3D model!

## File Formats for Godot

### Recommended
- **GLB/GLTF** ✅ Best choice
  - Modern, efficient
  - Godot's preferred format
  - Includes materials & animations

### Also Supported
- **OBJ** - Simple, but no materials
- **FBX** - Requires FBX2glTF converter
- **DAE (Collada)** - Works, but older

## Batch Import Script

If downloading many assets:

```bash
# Create asset directories
mkdir -p assets/models/resources
mkdir -p assets/models/stations
mkdir -p assets/models/characters

# Organize downloads
# resources/ → berries, wood, stone, ore
# stations/ → anvil, furnace, workbench
# characters/ → agent models (optional)
```

## Licenses Explained

### CC0 (Public Domain)
- Use anywhere, no attribution needed
- Commercial use OK
- Modify freely
- **Sources**: Kenney, Quaternius, Poly Pizza

### CC-BY
- Use anywhere WITH attribution
- Give credit to creator
- Commercial use OK

### Asset Store Licenses
- Read specific license
- Usually OK for games
- May restrict redistribution

## Pro Tips

1. **Consistent Style**: Stick to one art style (recommend low-poly)
2. **Scale**: Import at consistent scale (Godot units = meters)
3. **Optimization**: Low-poly models (< 5000 triangles) for performance
4. **Materials**: Use simple materials for benchmark scenes
5. **Collisions**: Add collision shapes separately (Box, Sphere, Capsule)

## Next Steps

After adding meshes:
1. Update collision shapes to match visual bounds
2. Add materials/colors for team differentiation
3. Consider adding simple animations (rotate, bob)
4. Test performance with multiple instances

## Resources

- Kenney: https://kenney.nl/assets
- Quaternius: https://quaternius.com
- Poly Pizza: https://poly.pizza
- Godot Docs (Importing): https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/importing_3d_scenes/index.html
- Blender (if making custom): https://blender.org

## Quick Reference: Common Godot Import Settings

When importing GLB files, check these in Import dock:

```
Materials:
  ✓ Use default material
  ✓ Keep on reimport

Meshes:
  ✓ Generate LODs (optional)
  ✓ Create shadow meshes

Physics:
  □ Generate collision (do manually for control)
```

---

**Recommendation**: Start with Kenney.nl Nature Kit and Food Kit. You'll have all your resource meshes in under 10 minutes!
