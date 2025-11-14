# Capture Point Scene Usage

## Overview
The capture point is a reusable scene component for creating territorial control objectives in team-based benchmarks.

## Files
- **Scene**: `scenes/capture_point.tscn`
- **Script**: `scripts/capture_point.gd`

## Features

### Visual Feedback
- **Color coding** based on ownership:
  - Gray: Neutral
  - Blue: Blue team controlled
  - Red: Red team controlled
- **Progress bar** appears during capture attempts
- **3D label** shows status and agent count
- **Emission effects** on controlled points

### Exported Properties
- `point_name` (String): Display name for the capture point
- `capture_radius` (float): Detection radius for agents (default: 3.0)

## How to Use

### Adding to a Scene
1. In Godot editor, navigate to `scenes/capture_point.tscn`
2. Drag and drop into your scene
3. Position using the Transform tool
4. Set the `point_name` in the Inspector

### Example Scene Structure
```
TeamCaptureScene (Node3D)
├── CapturePoints (Node3D)
│   ├── PointA (CapturePoint) - transform: (-15, 0.5, -15)
│   ├── PointB (CapturePoint) - transform: (15, 0.5, -15)
│   └── PointC (CapturePoint) - transform: (0, 0.5, 0)
```

### Scripting with Capture Points

#### Getting Capture Point State
```gdscript
# Initialize capture points
var capture_points = []
var points_node = $CapturePoints

for child in points_node.get_children():
    if child.has_method("get_state"):
        var state = child.get_state()
        capture_points.append(state)
```

#### State Dictionary Structure
```gdscript
{
    "name": "Point A",
    "position": Vector3(-15, 0.5, -15),
    "owner": "neutral",  # or "blue", "red"
    "capture_progress": 0.0,
    "capturing_team": "",
    "agents_present": [],
    "node": <CapturePoint instance>
}
```

#### Updating Visual Feedback
```gdscript
# Update capture progress (0.0 to 1.0)
point.node.set_capture_progress(0.75, "blue")

# Set ownership
point.node.set_owner_team("blue")

# Reset capture state
point.node.reset_capture()
```

## API Reference

### Methods

#### `get_state() -> Dictionary`
Returns the current state of the capture point including position, ownership, and capture progress.

#### `set_owner_team(team: String)`
Sets the owning team. Valid values: "neutral", "blue", "red"
Updates visual appearance automatically.

#### `set_capture_progress(progress: float, team: String)`
Updates capture progress (0.0 - 1.0) and shows progress bar.
- `progress`: Float between 0.0 and 1.0
- `team`: Team attempting capture ("blue" or "red")

#### `reset_capture()`
Resets capture progress and hides progress bar.

## Customization

### Adjusting Size
Modify in the scene file or script:
- Platform radius: Edit CylinderMesh in `$Platform`
- Detection radius: Change `capture_radius` export variable
- Collision shape: Edit CylinderShape3D in `$CollisionShape3D`

### Changing Colors
Edit materials in `_ready()` function:
```gdscript
blue_material.albedo_color = Color(0.2, 0.4, 0.9, 1.0)
blue_material.emission = Color(0.1, 0.2, 0.5, 1.0)
```

### Label Customization
Modify `$StatusLabel` properties:
- Font size: `font_size = 24`
- Outline: `outline_size = 8`
- Billboard mode: `billboard = 1` (always face camera)

## Integration with Team Capture Benchmark

The capture point scenes are designed to work seamlessly with the team capture benchmark:

1. **Automatic Detection**: The benchmark automatically finds all CapturePoint instances
2. **Visual Updates**: Progress and ownership are updated automatically
3. **Agent Tracking**: Agents within radius are tracked and displayed
4. **Event Recording**: Captures are logged through the EventBus system

## Tips

- Place capture points at strategic locations to encourage team tactics
- Use odd numbers of points (3, 5, 7) to avoid stalemates
- Position points 10-15 units apart for balanced gameplay
- Consider spawn distances when placing points (teams spawn at ±20 units)
- Center point should be hotly contested - place it equidistant from both spawns
