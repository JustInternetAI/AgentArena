# Mixamo Animation Fix - Animation Retargeting

## The Problem

When importing Mixamo animations as separate FBX files (character.fbx + idle.fbx + walk.fbx, etc.), the animations would load successfully but wouldn't play visually in Godot 4.x.

### Why This Happened

**Root Cause**: Animation track paths didn't match between source and target skeletons.

When you export animations separately from Mixamo:
1. Each FBX file contains its own `Skeleton3D` node
2. Animation tracks reference bones using paths like `"Skeleton3D:Hips"`
3. When you try to copy an animation from Idle.fbx to Y Bot.fbx, the paths don't match
4. The AnimationPlayer reports the animation as "playing" but no bones move

**Example of the mismatch:**
```
Source animation track path:  "Skeleton3D:Hips"
Target skeleton path:         "RootNode/GeneralSkeleton:Hips"
                              ^^^^^^^^^^^^^^^^^^^^^^^^
                              Different path!
```

## The Solution: Animation Retargeting

The fix involves **retargeting** animations by rebuilding track paths to match the target skeleton.

### How Retargeting Works

The `_retarget_animation()` function in [test_mixamo_fixed.gd](../scripts/tests/test_mixamo_fixed.gd):

1. **Find target skeleton path** in the character hierarchy
   ```gdscript
   var target_skeleton_path = _get_node_path_from_root(skeleton)
   # Example: "RootNode/GeneralSkeleton"
   ```

2. **For each track in source animation:**
   - Extract the bone name (e.g., "Hips" from "Skeleton3D:Hips")
   - Check if bone exists in target skeleton
   - Build new track path: `target_skeleton_path + ":" + bone_name`
   - Copy all keyframe data to new track

3. **Result:** New animation with correct paths
   ```gdscript
   # Source track:  "Skeleton3D:Hips"
   # New track:     "RootNode/GeneralSkeleton:Hips"
   ```

### Code Walkthrough

```gdscript
func _retarget_animation(source_anim: Animation, source_skeleton: Skeleton3D) -> Animation:
    var new_anim = Animation.new()
    new_anim.length = source_anim.length
    new_anim.loop_mode = source_anim.loop_mode

    # Get target skeleton's path in the character node tree
    var target_skeleton_path = _get_node_path_from_root(skeleton)

    # Process each animation track
    for i in range(source_anim.get_track_count()):
        var track_path = source_anim.track_get_path(i)

        # Extract bone name (e.g., "Hips" from "Skeleton3D:Hips")
        var bone_name = str(track_path).split(":")[1]

        # Verify bone exists in target
        if skeleton.find_bone(bone_name) == -1:
            continue  # Skip this track

        # Build new path with correct skeleton reference
        var new_track_path = String(target_skeleton_path) + ":" + bone_name

        # Create track and copy keyframes
        var new_track_idx = new_anim.add_track(track_type)
        new_anim.track_set_path(new_track_idx, new_track_path)

        # Copy all keyframe data...

    return new_anim
```

## Testing the Fix

### Test Scene: test_mixamo_fixed.tscn

Location: [scenes/tests/test_mixamo_fixed.tscn](../scenes/tests/test_mixamo_fixed.tscn)

**Controls:**
- `WASD` - Rotate camera
- `Q/E` - Zoom in/out
- `1` - Load and play Idle animation
- `2` - Load and play Walking animation
- `3` - Load and play Running animation
- `D` - Print debug info (see retargeting output)
- `T` - Stop animation (T-pose)

### Expected Output

When pressing `1` (Idle), you should see console output like:
```
[KEY 1] Loading Idle animation
  Loading: res://assets/characters/mixamo/Idle.fbx
  ✓ Found animation (length: 2.33s, 67 tracks)
    Target skeleton path: RootNode/GeneralSkeleton
    ✓ Retargeted 67/67 tracks
  ✓ Animation imported successfully
  ▶ Playing: imported/Idle
```

And the character should **visually animate** in the viewport.

## Comparison: Before vs After

### Before (test_mixamo_character.gd)
```gdscript
# Simply copied animation directly
var source_anim = source_anim_player.get_animation("Take 001")
anim_lib.add_animation("Idle", source_anim)
animation_player.play("imported/Idle")

# Result: Plays but no visual movement
# Track paths don't match skeleton
```

### After (test_mixamo_fixed.gd)
```gdscript
# Retarget animation tracks
var retargeted_anim = _retarget_animation(source_anim, source_skeleton)
anim_lib.add_animation("Idle", retargeted_anim)
animation_player.play("imported/Idle")

# Result: Plays with visual movement!
# Track paths match skeleton structure
```

## Using in Agent Arena

### Option 1: Use MixamoAgentVisual (Recommended)

The `MixamoAgentVisual` scene is ready to use with full animation support:

```gdscript
# Instance the Mixamo agent visual
var agent_visual = preload("res://scenes/mixamo_agent_visual.tscn").instantiate()
add_child(agent_visual)

# Set properties (same API as AgentVisual)
agent_visual.set_agent_name("Agent 1")
agent_visual.set_team_color(Color.RED)

# Update animation based on movement
agent_visual.set_movement_velocity(velocity)  # Auto-selects idle/walk/run

# Or play specific animations
agent_visual.play_animation("idle")
agent_visual.play_animation("walk")
agent_visual.play_animation("run")
```

**Files:**
- Scene: `scenes/mixamo_agent_visual.tscn`
- Script: `scripts/mixamo_agent_visual.gd`

### Option 2: Manual Integration

1. **Download from Mixamo:**
   - Character: Y Bot (or any character) WITH skin
   - Animations: Idle, Walking, Running WITH skin
   - Format: FBX for Unity (.fbx)

2. **Import to Godot:**
   - Place files in `assets/characters/mixamo/`
   - Godot will auto-import

3. **Use the retargeting code:**
   ```gdscript
   # In your agent visual script
   var retargeted = _retarget_animation(source_animation, target_skeleton)
   animation_library.add_animation("walk", retargeted)
   ```

4. **Or use the helper function:**
   - Copy `_retarget_animation()` and `_get_skeleton_path_for_animation()` from mixamo_agent_visual.gd
   - Integrate into your character controller

## Alternative Approaches

If you don't want to retarget at runtime:

### Option A: Import Character with All Animations
- Download Y Bot
- In Mixamo, select Y Bot, download with Idle animation baked in
- Download Y Bot again with Walking animation baked in
- Import each as separate scenes
- Swap scenes based on state

### Option B: Use Godot's Animation Library
- Import all animations into one character FBX
- Use Blender to combine multiple FBX files
- Import to Godot as single file

### Option C: Manual Retargeting in Godot
- Import animations
- Use Godot's animation retargeting tools (if available in 4.x)

## Technical Details

### Godot 4.x Animation System

Godot 4.x uses:
- **AnimationLibrary**: Groups of animations
- **Animation**: Individual animation clips
- **Tracks**: Bone transformations over time
- **Track Paths**: NodePath to specific bones (e.g., "Skeleton3D:Hips")

### Common Track Path Formats

```
"Skeleton3D:BoneName"                    # Direct child
"RootNode/Skeleton3D:BoneName"          # Nested
".:BoneName"                             # Relative path
"../Skeleton:BoneName"                   # Parent reference
```

### Bone Matching

The retargeting assumes:
- Source and target skeletons have same bone names
- Mixamo guarantees this for Mixamo characters
- Custom characters need matching bone naming conventions

## Troubleshooting

### Animation loads but still doesn't play

1. **Check skeleton path:**
   ```gdscript
   var skel_path = _get_node_path_from_root(skeleton)
   print("Skeleton path: ", skel_path)
   ```

2. **Verify bone names match:**
   ```gdscript
   # In source FBX
   print("Source bones: ", source_skeleton.get_bone_count())

   # In target
   print("Target bones: ", skeleton.get_bone_count())
   ```

3. **Check retargeted track count:**
   ```gdscript
   print("Retargeted %d tracks" % retargeted_anim.get_track_count())
   # Should be > 0
   ```

### No bones found in target

- Ensure you're finding the right Skeleton3D node
- Check that character FBX imported with skeleton
- Verify in Godot scene tree that Skeleton3D exists

### Some bones don't animate

- Source and target might have different bone hierarchies
- Some animations might have extra bones
- This is normal - retargeting skips unmapped bones

## References

- **Test Scene**: [scenes/tests/test_mixamo_fixed.tscn](../scenes/tests/test_mixamo_fixed.tscn)
- **Implementation**: [scripts/tests/test_mixamo_fixed.gd](../scripts/tests/test_mixamo_fixed.gd)
- **Diagnostic Tool**: [scripts/tests/diagnose_mixamo.gd](../scripts/tests/diagnose_mixamo.gd)
- **Mixamo**: https://www.mixamo.com/
- **Godot Animation Docs**: https://docs.godotengine.org/en/stable/classes/class_animation.html
