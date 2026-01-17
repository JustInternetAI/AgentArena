# Mixamo Character Quickstart

Get Mixamo characters working in Agent Arena in 5 minutes!

## Step 1: Test the Fixed Version

1. Open Godot
2. Open scene: `scenes/tests/test_mixamo_fixed.tscn`
3. Press **F6** to run
4. Press **1** to load Idle animation
5. Character should animate!

**If it works**: You're ready to integrate into Agent Arena!
**If not**: See troubleshooting section below.

## Step 2: Integrate Into Agent

The simple humanoid is currently in use, but to switch to Mixamo:

### Option A: Replace Agent Visual (Recommended for later)

1. Create a new `MixamoAgentVisual.tscn` scene
2. Instance Y Bot character
3. Attach animation controller script
4. Update foraging scene to use new visual

### Option B: Use Side-by-Side (For testing)

1. Keep simple humanoid
2. Add Mixamo character as child
3. Test movement with both visuals
4. Choose which works better

## Step 3: Add Animations

The retargeting code in `test_mixamo_fixed.gd` can be copied to your character controller:

```gdscript
# Copy these functions to your script:
# - _retarget_animation()
# - _get_node_path_from_root()
# - _load_and_play_animation()

# Then load animations:
_load_and_play_animation("res://assets/characters/mixamo/Walking.fbx", "walk")
```

## Quick Files Reference

| File | Purpose |
|------|---------|
| `scenes/tests/test_mixamo_fixed.tscn` | Test scene with working animations |
| `scripts/tests/test_mixamo_fixed.gd` | Retargeting implementation |
| `docs/MIXAMO_ANIMATION_FIX.md` | Detailed technical explanation |
| `assets/characters/mixamo/Y Bot.fbx` | Character mesh and skeleton |
| `assets/characters/mixamo/Idle.fbx` | Idle animation |
| `assets/characters/mixamo/Walking.fbx` | Walking animation |
| `assets/characters/mixamo/Running.fbx` | Running animation |

## Key Concepts

### The Problem
Animations from separate FBX files have wrong skeleton paths and don't play visually.

### The Solution
**Animation Retargeting** - Rebuild animation tracks to match your character's skeleton structure.

### The Code
The magic happens in `_retarget_animation()` which:
1. Extracts bone names from source animation
2. Rebuilds track paths for target skeleton
3. Copies all keyframe data

## Next Steps

1. ✅ Test `test_mixamo_fixed.tscn` - Verify animations work
2. 📝 Decide on integration approach (replace simple humanoid or keep both)
3. 🎮 Create character controller with movement + animation
4. 🏃 Integrate into foraging scene

## Troubleshooting

**No visual movement?**
- Check console for "Retargeted X tracks" message
- Should be > 0 tracks retargeted
- Press `D` in test scene for debug info

**Character not visible?**
- Check camera position (use Q/E to zoom out)
- Verify Y Bot.fbx imported correctly in Godot

**Animations have wrong names?**
- This is expected (they import as "Take 001")
- Retargeting renames them (Idle, Walking, Running)

**Getting errors?**
- Check file paths are correct
- Ensure all FBX files are in `assets/characters/mixamo/`
- Verify FBX files were downloaded WITH skin

## Want More Details?

See [docs/MIXAMO_ANIMATION_FIX.md](docs/MIXAMO_ANIMATION_FIX.md) for:
- Technical deep dive
- Code walkthrough
- Alternative approaches
- Advanced troubleshooting

## Ready to Go?

Open `test_mixamo_fixed.tscn` and press F6! 🎮

Your Mixamo character should now walk, run, and idle properly!
