# Physics-Based Agent Movement Design

**Status**: Proposed
**Author**: Agent Arena Team
**Date**: 2026-01-31
**Related Issues**: B-36a, B-36b, B-36c

## Overview

This document describes the design for implementing physics-based movement with collision detection, experience-based learning, and optional pathfinding for agents in Agent Arena.

## Problem Statement

Currently, agents move by directly setting `global_position` in GDScript:

```gdscript
# Current implementation (simple_agent.gd:162)
global_position += direction * move_distance
```

This means agents pass through all obstacles (trees, walls, hazards), which:
- Creates unrealistic behavior
- Removes spatial navigation challenges
- Prevents agents from learning obstacle avoidance
- Reduces the value of spatial memory

## Goals

1. **Collision Detection**: Agents cannot pass through solid obstacles (trees, walls, rocks)
2. **Hazard Interaction**: Different hazards have different effects (damage, trapping)
3. **Experience Learning**: Agents remember collisions and damage to inform future decisions
4. **Optional Pathfinding**: Automated navigation as fallback or comparison baseline

## Non-Goals (This Design)

- Multiplayer agent collision (agents passing through each other is acceptable for now)
- Complex physics (pushing objects, physics puzzles)
- 3D vertical navigation (climbing, jumping)

---

## Architecture

### Current State

```
┌─────────────────┐
│  SimpleAgent    │
│  extends Node3D │
└────────┬────────┘
         │ _process(delta)
         ▼
┌─────────────────────────────┐
│ global_position += dir * d  │  ← Direct position update
│ (passes through everything) │
└─────────────────────────────┘
```

### Target State

```
┌──────────────────────────┐
│     SimpleAgent          │
│ extends CharacterBody3D  │
└───────────┬──────────────┘
            │ _physics_process(delta)
            ▼
┌────────────────────────────────┐
│ velocity = direction * speed   │
│ move_and_slide()               │  ← Physics-based movement
│ collision = get_last_slide_... │
└───────────┬────────────────────┘
            │ if collision detected
            ▼
┌─────────────────────────────────┐
│ Report to Python via IPC        │
│ Store in SpatialMemory          │
│ Include in next observation     │
└─────────────────────────────────┘
```

---

## Phase 1: Collision Detection

### Godot Changes

#### 1.1 BaseAgent Node Type

**File**: `scripts/base_agent.gd`

```gdscript
# Before
extends Node3D
class_name BaseAgent

# After
extends CharacterBody3D
class_name BaseAgent
```

#### 1.2 SimpleAgent Movement

**File**: `scripts/simple_agent.gd`

```gdscript
# Before (in _process)
global_position += direction * move_distance

# After (in _physics_process)
func _physics_process(delta):
    if _is_moving:
        var direction = (_target_position - global_position).normalized()
        velocity = direction * move_speed * _movement_speed

        move_and_slide()

        # Check if we hit something
        if get_slide_collision_count() > 0:
            var collision = get_slide_collision(0)
            _on_collision(collision)

        # Check if reached target
        if global_position.distance_to(_target_position) < 0.5:
            _is_moving = false
            velocity = Vector3.ZERO

func _on_collision(collision: KinematicCollision3D):
    var collider = collision.get_collider()
    print("Collision with: ", collider.name)
    # Will be extended in Phase 2 to report to Python
```

#### 1.3 Agent Collision Shape

Add as child of agent scene:

```
SimpleAgent (CharacterBody3D)
├── CollisionShape3D
│   └── CapsuleShape3D (radius: 0.4, height: 1.8)
├── MeshInstance3D (visual)
└── ...
```

#### 1.4 Obstacle Collision Setup

Trees, rocks, and walls need collision:

```
Tree (Node3D)
├── MeshInstance3D (visual)
└── StaticBody3D
    └── CollisionShape3D
        └── CylinderShape3D (matches trunk)
```

#### 1.5 Collision Layers

| Layer | Name | Used By |
|-------|------|---------|
| 1 | Default | Ground, general |
| 2 | Obstacles | Trees, walls, rocks (blocks movement) |
| 3 | Hazards | Fire, pits (triggers effects, may not block) |
| 4 | Agents | Player, AI agents |
| 5 | Resources | Collectible items |

Agent collision mask: Layers 1, 2 (collides with ground and obstacles)

### Hazard Types

| Hazard | Collision | Layer | Effect |
|--------|-----------|-------|--------|
| Fire | Area3D (no block) | 3 | Damage while overlapping |
| Pit | Area3D + trap | 3 | Traps agent, continuous damage |
| Wall | StaticBody3D | 2 | Blocks movement |
| Tree | StaticBody3D | 2 | Blocks movement |

**Fire Implementation**:
```gdscript
# Fire uses Area3D - agent can walk through but takes damage
func _on_body_entered(body):
    if body is BaseAgent:
        _burning_agents.append(body)

func _on_body_exited(body):
    _burning_agents.erase(body)

func _process(delta):
    for agent in _burning_agents:
        agent.take_damage(FIRE_DPS * delta)
```

**Pit Implementation**:
```gdscript
# Pit traps the agent
func _on_body_entered(body):
    if body is BaseAgent:
        body.set_trapped(true, self)
        body.take_damage(PIT_INITIAL_DAMAGE)

# Agent must wait or call "escape" to get out
```

---

## Phase 2: Experience Memory

### Goal

When the agent experiences something (collision, damage, trap), store it in memory so the LLM can learn from it.

### New Data Structures

**File**: `python/agent_runtime/schemas.py`

```python
@dataclass
class ExperienceEvent:
    """A significant event the agent experienced."""

    tick: int
    event_type: str  # "collision", "damage", "trapped", "collected"
    description: str
    position: tuple[float, float, float]
    object_name: str | None = None
    damage_taken: float = 0.0
    metadata: dict = field(default_factory=dict)
```

### SpatialMemory Extension

**File**: `python/agent_runtime/memory/spatial.py`

Add experience storage:

```python
class SpatialMemory:
    def __init__(self, ...):
        # Existing
        self._objects: dict[str, WorldObject] = {}
        self._spatial_grid: dict[tuple, set[str]] = {}

        # New: Experience log
        self._experiences: list[ExperienceEvent] = []
        self._max_experiences: int = 50  # Keep last N

    def record_experience(self, event: ExperienceEvent) -> None:
        """Record a significant experience."""
        self._experiences.append(event)
        if len(self._experiences) > self._max_experiences:
            self._experiences.pop(0)

        # Also mark location as obstacle if collision
        if event.event_type == "collision" and event.object_name:
            self._store_or_update(WorldObject(
                name=event.object_name,
                object_type="obstacle",
                subtype="collision",
                position=event.position,
                last_seen_tick=event.tick,
            ))

    def get_recent_experiences(self, limit: int = 10) -> list[ExperienceEvent]:
        """Get recent experiences for LLM context."""
        return self._experiences[-limit:]
```

### IPC Protocol Extension

**File**: Tool result includes experience events

```python
# When move_to is blocked
{
    "success": false,
    "tool": "move_to",
    "result": {
        "blocked": true,
        "blocked_by": "Tree_003",
        "blocked_at": [5.2, 0, 3.1],
        "distance_moved": 2.3
    }
}

# When agent takes damage
{
    "event": "damage",
    "source": "Fire_001",
    "damage": 10.0,
    "agent_health": 90.0,
    "position": [3.0, 0, 5.0]
}
```

### Prompt Integration

**File**: `python/agent_runtime/local_llm_behavior.py`

Add experiences to prompt:

```python
def _build_prompt(self, observation, tools):
    sections = [...]

    # Add recent experiences
    experiences = self.world_map.get_recent_experiences(limit=5)
    if experiences:
        sections.append("\n## Recent Experiences")
        for exp in experiences:
            if exp.event_type == "collision":
                sections.append(
                    f"- Tick {exp.tick}: Movement blocked by {exp.object_name} "
                    f"at position {exp.position}"
                )
            elif exp.event_type == "damage":
                sections.append(
                    f"- Tick {exp.tick}: Took {exp.damage_taken} damage from "
                    f"{exp.object_name} at {exp.position}"
                )
            elif exp.event_type == "trapped":
                sections.append(
                    f"- Tick {exp.tick}: TRAPPED by {exp.object_name}! "
                    f"Lost {exp.metadata.get('ticks_trapped', '?')} ticks"
                )
```

### Example Prompt Output

```
## Recent Experiences
- Tick 5: Movement blocked by Tree_003 at position (5.2, 0, 3.1)
- Tick 8: Took 10.0 damage from Fire_001 at (3.0, 0, 5.0)
- Tick 12: TRAPPED by Pit_002! Lost 3 ticks

## Known Obstacles (from collisions)
- Tree_003 at (5.2, 0, 3.1) - blocked movement
```

---

## Phase 3: Pathfinding (Optional)

### Goal

Add automated pathfinding as:
1. A separate `navigate_to` tool that finds paths automatically
2. A fallback when agent gets stuck repeatedly

### Godot Setup

#### 3.1 Navigation Region

Add to scene:

```
ForagingScene
├── NavigationRegion3D
│   └── NavigationMesh (baked, excludes obstacles)
├── Agents
│   └── SimpleAgent
│       └── NavigationAgent3D
└── ...
```

#### 3.2 NavigationAgent3D on Agent

```gdscript
@onready var nav_agent: NavigationAgent3D = $NavigationAgent3D

func navigate_to(target: Vector3):
    nav_agent.target_position = target
    _using_navigation = true

func _physics_process(delta):
    if _using_navigation:
        if nav_agent.is_navigation_finished():
            _using_navigation = false
            return

        var next_pos = nav_agent.get_next_path_position()
        var direction = (next_pos - global_position).normalized()
        velocity = direction * move_speed
        move_and_slide()
```

### New Tool: navigate_to

```python
# Tool schema
{
    "name": "navigate_to",
    "description": "Navigate to a position using pathfinding (goes around obstacles)",
    "parameters": {
        "target_position": {"type": "array", "items": {"type": "number"}}
    }
}
```

### Stuck Detection

If agent fails to move for N ticks, suggest using navigation:

```python
def _check_stuck(self, observation):
    if len(self._position_history) >= 5:
        positions = self._position_history[-5:]
        total_movement = sum(
            dist(positions[i], positions[i+1])
            for i in range(len(positions)-1)
        )
        if total_movement < 0.5:  # Barely moved in 5 ticks
            return True
    return False
```

---

## File Changes Summary

### Phase 1

| File | Changes |
|------|---------|
| `scripts/base_agent.gd` | `extends Node3D` → `extends CharacterBody3D` |
| `scripts/simple_agent.gd` | `_process` → `_physics_process`, `move_and_slide()` |
| `scenes/agents/simple_agent.tscn` | Add `CollisionShape3D` child |
| `scenes/foraging.tscn` | Add collision to obstacles |
| `scenes/prefabs/*.tscn` | Add `StaticBody3D` + collision to trees/rocks |

### Phase 2

| File | Changes |
|------|---------|
| `python/agent_runtime/schemas.py` | Add `ExperienceEvent` dataclass |
| `python/agent_runtime/memory/spatial.py` | Add experience recording |
| `python/agent_runtime/local_llm_behavior.py` | Include experiences in prompt |
| `python/ipc/server.py` | Handle experience events from Godot |
| `scripts/simple_agent.gd` | Report collisions/damage via IPC |
| `scripts/hazards/fire.gd` | Report damage events |
| `scripts/hazards/pit.gd` | Report trap events |

### Phase 3

| File | Changes |
|------|---------|
| `scenes/foraging.tscn` | Add `NavigationRegion3D` with navmesh |
| `scripts/simple_agent.gd` | Add `NavigationAgent3D` support |
| `python/tools/navigation.py` | Add `navigate_to` tool |

---

## Testing Plan

### Phase 1 Tests

- [ ] Agent stops when hitting a tree
- [ ] Agent slides along walls (doesn't stick)
- [ ] Agent can walk through fire (takes damage)
- [ ] Agent gets trapped in pit
- [ ] Existing scenes still load and run

### Phase 2 Tests

- [ ] Collision events appear in Python logs
- [ ] Experiences stored in SpatialMemory
- [ ] LLM prompt includes recent experiences
- [ ] Agent avoids previously-collided obstacles

### Phase 3 Tests

- [ ] `navigate_to` finds path around obstacles
- [ ] Stuck detection triggers after N failed moves
- [ ] Navigation falls back gracefully if no path

---

## Migration Guide

### For Existing Scenes

1. Open scene in Godot
2. Select agent node
3. Change type: Node3D → CharacterBody3D
4. Add CollisionShape3D child with CapsuleShape3D
5. Set collision layer to 4 (Agents)
6. Set collision mask to 1, 2 (Ground, Obstacles)

### For Existing Obstacles

1. Add StaticBody3D child to obstacle
2. Add CollisionShape3D matching visual bounds
3. Set collision layer to 2 (Obstacles)

---

## Open Questions

1. **Agent-agent collision**: Should agents collide with each other or pass through?
   - Recommendation: Pass through for now, simplifies multi-agent scenarios

2. **Damage application**: Should damage reduce a health value, or just be logged?
   - Recommendation: Both - track health AND log for learning

3. **Pit escape**: How does agent escape a pit?
   - Option A: Automatic after N ticks
   - Option B: New `escape` tool
   - Recommendation: Automatic with configurable duration

---

## References

- [Godot CharacterBody3D docs](https://docs.godotengine.org/en/stable/classes/class_characterbody3d.html)
- [Godot Navigation overview](https://docs.godotengine.org/en/stable/tutorials/navigation/navigation_introduction_3d.html)
- Current implementation: `scripts/simple_agent.gd`
- SpatialMemory: `python/agent_runtime/memory/spatial.py`
