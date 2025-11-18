# Assets Directory

Organized storage for all game assets (3D models, textures, audio).

## Directory Structure

```
assets/
├── models/           # 3D models (.glb, .gltf, .obj)
│   ├── characters/   # Agent/character models
│   ├── resources/    # Collectible resources (berries, wood, stone, ore)
│   │   ├── apple.glb          # Model file
│   │   └── colormap.png       # Texture for apple (kept with model)
│   ├── stations/     # Crafting stations (anvil, furnace, workbench)
│   ├── hazards/      # Dangerous objects (fire, pits)
│   └── environment/  # Terrain and environment props
├── textures/         # Image files (.png, .jpg)
│   ├── materials/    # Shared/generic material textures
│   └── ui/           # UI graphics
└── audio/            # Sound files (.wav, .ogg)
    ├── sfx/          # Sound effects
    └── music/        # Background music
```

**Note**: Model textures are kept next to their GLB files (industry standard).
Only shared/generic textures go in `textures/materials/`.


## Adding New Assets

### 3D Models

1. **Download** your model (from Kenney, Quaternius, etc.)
2. **Place** the `.glb` file in the appropriate subfolder:
   - `models/resources/` for berries, wood, stone, ore
   - `models/stations/` for anvil, furnace, workbench
   - `models/hazards/` for fire, pits
3. **Godot auto-imports** the file
4. **Drag & drop** into your scene

Example:
```
Download: berry.glb
Place in: assets/models/resources/berry.glb
Godot path: res://assets/models/resources/berry.glb
```

### Textures

**For model-specific textures:**
- Keep them next to the GLB file (e.g., `apple.glb` + `colormap.png` in same folder)
- This is standard practice and Godot handles it automatically

**For shared textures:**
- Place in `textures/materials/` for generic materials (grass, dirt, etc.)
- Place in `textures/ui/` for UI graphics

### Audio

Place `.wav` or `.ogg` files in `audio/sfx/` or `audio/music/`

## Naming Conventions

- Use **lowercase** with underscores: `iron_ore.glb`, not `IronOre.glb`
- Be **descriptive**: `workbench_wooden.glb` vs `wb1.glb`
- Version numbers if needed: `berry_v2.glb`

## Recommended Sources

- **Kenney.nl** - Free, CC0, high quality
- **Quaternius** - Low-poly, CC0
- **Poly Pizza** - Community assets, CC0

See `docs/getting_3d_assets.md` for detailed guide.

## Current Assets

### Resources
- [ ] berry.glb (TODO: Download from Kenney Food Kit)
- [ ] wood.glb (TODO: Download from Kenney Nature Kit)
- [ ] stone.glb (TODO: Download from Kenney Nature Kit)
- [ ] iron_ore.glb (TODO: Download from Poly Pizza)
- [ ] coal.glb (TODO: Download from Quaternius)

### Stations
- [ ] anvil.glb (TODO: Download from Poly Pizza)
- [ ] furnace.glb (TODO: Download from Quaternius)
- [ ] workbench.glb (TODO: Download from Kenney Furniture Kit)

### Hazards
- [ ] fire.glb (TODO: Download from Kenney)
- [ ] pit.glb (Can use simple cylinder mesh)

### Characters
- Currently using procedural capsule meshes (see `scenes/agent_visual.tscn`)
- [ ] Optional: humanoid.glb for future enhancement

## File Size Guidelines

- Keep models **< 1MB** each for performance
- Use **low-poly** meshes (< 5000 triangles)
- Compress textures when possible

## Godot Import Settings

When importing GLB files:
- Materials: ✓ Use default material
- Meshes: ✓ Generate LODs (optional)
- Physics: □ Don't auto-generate (we do this manually)

## License Tracking

All assets in this directory should be:
- **CC0 (Public Domain)** - No attribution required
- **CC-BY** - Attribution required (note source in this file)
- **Licensed for use** - Check license file

### Attribution
(Add here if using CC-BY assets)

---

**Quick Start**: Download Kenney Nature Kit and Food Kit, extract GLB files here, and you're ready to go!
