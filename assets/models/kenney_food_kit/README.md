# Kenney Food Kit

Complete Kenney Food Kit with 200+ food-related 3D models.

## Folder Structure

```
kenney_food_kit/
├── Models/
│   ├── Textures/
│   │   └── colormap.png     # Shared texture atlas for all models
│   ├── apple.glb
│   ├── apple-half.glb
│   └── ... (200+ food models)
└── Previews/                 # Preview images (not used by Godot)
```

## Important: How Kenney Models Work

1. **All models share ONE texture file**: `Models/Textures/colormap.png`
2. **GLB files have hardcoded relative paths**: Each GLB looks for `Textures/colormap.png` relative to its location
3. **DO NOT move GLB files** out of the Models folder or they will appear white/untextured
4. **DO NOT move or rename** the Textures folder

## Using Food Kit Models in Your Scenes

Simply reference models with their full path:

```gdscript
# In .tscn file:
[ext_resource type="PackedScene" path="res://assets/models/kenney_food_kit/Models/apple.glb" id="1"]

[node name="Apple" parent="." instance=ExtResource("1")]
```

The texture will be automatically loaded from the Textures subfolder.

## Available Model Categories

- **Fruits**: apple, banana, orange, lemon, pear, pineapple, grapes, etc.
- **Vegetables**: carrot, corn, onion, mushroom, paprika, eggplant, etc.
- **Meats**: bacon, sausage, fish, ribs, patty, etc.
- **Prepared Foods**: burger, pizza, hot-dog, sushi, donuts, etc.
- **Beverages**: coffee, tea, juice, soda, cocktail, etc.
- **Kitchenware**: plates, bowls, cups, pans, knives, cutting boards, etc.
- **Packaged Foods**: cans, cartons, bags, boxes, bottles, etc.

## Example Usage

Current project usage:
- **Berry scene** ([scenes/resources/berry.tscn](../../../scenes/resources/berry.tscn)) uses `apple.glb`

## Source & License

- **Source**: https://kenney.nl/assets/food-kit
- **Author**: Kenney (kenney.nl)
- **License**: CC0 1.0 Universal (Public Domain)
- **Attribution**: Not required, but appreciated!

## Technical Details

- **Format**: GLB (binary GLTF)
- **Texture**: Single 1024x1024 atlas (colormap.png)
- **UV Mapping**: All models use shared UV atlas
- **Poly Count**: Low-poly (optimized for games)
- **Import Settings**: Use default Godot GLB import settings

## Troubleshooting

**Problem**: Models appear white/untextured

**Solution**: Verify folder structure is intact:
- GLB files must be in `Models/` folder
- Texture must be at `Models/Textures/colormap.png`
- Do not reorganize Kenney's original structure

See [docs/troubleshooting_3d_models.md](../../../docs/troubleshooting_3d_models.md) for more help.
