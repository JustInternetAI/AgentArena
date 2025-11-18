# Kenney Food Kit Assets

This folder contains assets from Kenney's Food Kit.

## Important: Folder Structure

Kenney's GLB files have **hardcoded relative paths** to textures. The folder structure must be:

```
kenney_food_kit/
├── Models/           # GLB model files
│   ├── apple.glb
│   ├── apple-half.glb
│   └── ... (other food models)
└── Textures/         # Shared texture atlas
    └── colormap.png  # Single texture used by all models
```

**DO NOT move GLB files out of the Models folder** or they won't find their textures!

## How Kenney Assets Work

1. **All models share ONE texture** (`Textures/colormap.png`)
2. **GLB files reference the texture with a relative path**: `../Textures/colormap.png`
3. **If you break this structure**, models will appear white/untextured

## Using Kenney Models in Scenes

Simply instance the GLB file from the Models folder:

```gdscript
# In your .tscn file:
[ext_resource type="PackedScene" path="res://assets/kenney_food_kit/Models/apple.glb" id="1"]

[node name="Apple" parent="." instance=ExtResource("1")]
```

The texture will be automatically loaded from the Textures folder.

## Download Source

- **Source**: https://kenney.nl/assets/food-kit
- **License**: CC0 (Public Domain)
- **Attribution**: Not required, but appreciated

## Adding More Food Kit Models

1. Download the full Food Kit from Kenney
2. Copy additional GLB files from the download into `Models/`
3. Make sure `Textures/colormap.png` matches the one from the kit
4. Instance in your scenes

## Why This Folder Structure?

Kenney distributes assets in a specific structure, and the GLB files have baked-in relative paths to find textures. Godot respects these paths, so we keep the original structure.

Alternative: You could extract materials and manually apply them, but that's more work!
