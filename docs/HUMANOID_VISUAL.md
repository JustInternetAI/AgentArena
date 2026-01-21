# Agent Humanoid Visual

## Overview

Agents in Agent Arena now use a simple humanoid visual representation to make them look more like people while maintaining performance and simplicity.

## Visual Structure

The agent visual consists of:
- **Body**: Capsule mesh (torso)
- **Head**: Sphere mesh
- **Arms**: Box mesh (horizontal bar)
- **Legs**: Two box meshes (left and right)
- **Direction Indicator**: Small box pointing forward
- **Label**: 3D text displaying agent name

## Files

- **Scene**: [scenes/agent_visual.tscn](../scenes/agent_visual.tscn)
- **Script**: [scripts/agent_visual.gd](../scripts/agent_visual.gd)
- **Simple Humanoid Reference**: [scenes/simple_humanoid.tscn](../scenes/simple_humanoid.tscn)

## Features

### Team Colors
All body parts (body, head, arms, legs) are colored based on the agent's team:
- Body: Base team color
- Head: Lightened team color (20% lighter)
- Limbs: Slightly darkened team color (10% darker)
- Direction indicator: Very light team color (40% lighter)

### Customization
The visual supports:
- `set_team_color(color)` - Change team color
- `set_agent_name(name)` - Change display name
- `set_highlight(enabled)` - Highlight agent with emission

### Usage in Scenes

Agent visuals are automatically created by the `SceneController` base class:

```gdscript
# In your scene, add SimpleAgent node with child AgentVisual
[node name="Agent1" type="Node3D"]
script = ExtResource("simple_agent.gd")

[node name="AgentVisual" parent="Agent1" instance=ExtResource("agent_visual.tscn")]
```

The SceneController will:
1. Discover the agent node
2. Find the AgentVisual child
3. Apply team colors automatically
4. Set the agent's display name

## Dimensions

- Total height: ~2.0 units (ground to top of head)
- Body height: 1.0 unit
- Head radius: 0.2 units
- Arms width: 0.6 units
- Legs height: 0.6 units each
- Collision capsule: 0.3 radius × 1.6 height

## Future Improvements

While Mixamo character integration was explored, it proved complex for the current needs. Future enhancements could include:

1. **Animation System**: Add simple procedural animations for walking/running
2. **Mixamo Integration**: Complete the animation retargeting workflow
3. **Custom Models**: Support for importing custom 3D character models
4. **Procedural Poses**: Rotate limbs based on movement direction

For now, the simple humanoid provides a clear, performant visual that's easy to distinguish from environment objects.

## Related

- **Mixamo Test Scene**: [scenes/tests/test_mixamo_character.tscn](../scenes/tests/test_mixamo_character.tscn) (experimental)
- **Test README**: [scenes/tests/README.md](../scenes/tests/README.md)
