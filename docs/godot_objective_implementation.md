# Godot Objective System Implementation

**Related to:** Issue #58 (Implement objective system in Godot), Issue #60 (LDX Refactor)
**Status:** Python schemas ready, Godot implementation needed
**Priority:** HIGH (blocks Phase 3 starter templates)

---

## Overview

The Python side is now ready to receive objective data from Godot. This document describes what needs to be implemented in Godot to send objectives to agents.

---

## What's Already Done (Python Side)

✅ **Schemas Created:**
- `MetricDefinition` class in `agent_runtime/schemas.py`
- `Objective` class in `agent_runtime/schemas.py`
- `Observation` class extended with:
  - `scenario_name: str`
  - `objective: Objective | None`
  - `current_progress: dict[str, float]`

✅ **SDK Updated:**
- Minimal SDK in `python/sdk/agent_arena_sdk/` includes objective schemas
- IPC protocol documented in `docs/ipc_protocol.md`

✅ **Parsing:**
- `Observation.from_dict()` parses objective fields
- `Observation.to_dict()` serializes objective fields

---

## What Needs to Be Done (Godot Side)

### 1. Scene Controller Base Class

Update `base_scene_controller.gd` to define objective interface:

```gdscript
# base_scene_controller.gd
class_name BaseSceneController

# Override in subclasses
func get_scenario_name() -> String:
    return "unknown"

# Override in subclasses
func get_objective() -> Dictionary:
    """
    Return objective definition:
    {
        "description": "Human-readable goal",
        "success_metrics": {
            "metric_name": {
                "target": 10.0,
                "weight": 1.0,
                "lower_is_better": false,
                "required": false
            }
        },
        "time_limit": 600  # 0 = unlimited
    }
    """
    return {}

# Override in subclasses
func get_current_progress() -> Dictionary:
    """
    Return current metric values:
    {
        "metric_name": current_value
    }
    """
    return {}
```

### 2. Update Foraging Scene

Implement objectives in `scripts/foraging.gd`:

```gdscript
# foraging.gd
extends BaseSceneController

var _resources_collected: int = 0
var _initial_health: float = 100.0
var _start_tick: int = 0

func get_scenario_name() -> String:
    return "foraging"

func get_objective() -> Dictionary:
    return {
        "description": "Collect resources while avoiding hazards and staying healthy.",
        "success_metrics": {
            "resources_collected": {
                "target": 10.0,
                "weight": 1.0,
                "lower_is_better": false,
                "required": false
            },
            "health_remaining": {
                "target": 50.0,
                "weight": 0.5,
                "lower_is_better": false,
                "required": false
            },
            "time_taken": {
                "target": 300.0,
                "weight": 0.2,
                "lower_is_better": true,
                "required": false
            }
        },
        "time_limit": 600
    }

func get_current_progress() -> Dictionary:
    return {
        "resources_collected": float(_resources_collected),
        "health_remaining": _get_agent_health(),  # Implement this
        "time_elapsed": float(_current_tick - _start_tick)
    }

# Track when resources are collected
func _on_resource_collected():
    _resources_collected += 1
```

### 3. Update IPC Client

Modify `_build_perception()` or wherever observations are constructed:

```gdscript
# In scene controller or IPC client
func _build_perception(agent: Node) -> Dictionary:
    var perception = {
        "agent_id": agent.agent_id,
        "tick": _current_tick,
        "position": [...],
        "rotation": [...],
        # ... existing fields ...

        # NEW: Add objective fields
        "scenario_name": get_scenario_name(),
        "objective": get_objective(),
        "current_progress": get_current_progress()
    }
    return perception
```

### 4. Implement for Other Scenarios

After foraging works, implement for:
- **Crafting Chain** (`scripts/crafting.gd`)
- **Team Capture** (`scripts/team_capture.gd`)

---

## Example: Complete Foraging Objective

```json
{
  "scenario_name": "foraging",
  "objective": {
    "description": "Collect resources while avoiding hazards and staying healthy.",
    "success_metrics": {
      "resources_collected": {
        "target": 10.0,
        "weight": 1.0,
        "lower_is_better": false,
        "required": false
      },
      "health_remaining": {
        "target": 50.0,
        "weight": 0.5,
        "lower_is_better": false,
        "required": false
      },
      "time_taken": {
        "target": 300.0,
        "weight": 0.2,
        "lower_is_better": true,
        "required": false
      }
    },
    "time_limit": 600
  },
  "current_progress": {
    "resources_collected": 3.0,
    "health_remaining": 85.0,
    "time_elapsed": 142.0
  }
}
```

---

## Testing

### Python Test

```python
# Test that Python can parse objectives
from agent_runtime.schemas import Observation

data = {
    "agent_id": "test",
    "tick": 100,
    "position": [0, 0, 0],
    "scenario_name": "foraging",
    "objective": {
        "description": "Collect resources",
        "success_metrics": {
            "resources_collected": {
                "target": 10.0,
                "weight": 1.0,
                "lower_is_better": False,
                "required": False
            }
        },
        "time_limit": 600
    },
    "current_progress": {
        "resources_collected": 3.0
    }
}

obs = Observation.from_dict(data)
assert obs.scenario_name == "foraging"
assert obs.objective is not None
assert obs.objective.description == "Collect resources"
assert "resources_collected" in obs.current_progress
print("✓ Objective parsing works!")
```

### End-to-End Test

1. Start Python server with beginner agent (once implemented)
2. Run foraging scene in Godot
3. Connect agent
4. Verify agent receives objective data in observations
5. Check agent console logs for objective info

---

## Acceptance Criteria

- [ ] `BaseSceneController` has objective interface methods
- [ ] Foraging scene implements all three methods
- [ ] IPC client includes objective fields in perception
- [ ] Python agents receive objectives in `Observation` object
- [ ] No errors when parsing objective data
- [ ] Documented in `docs/ipc_protocol.md` ✅ (already done)

---

## Dependencies

**Blocks:**
- Issue #60 Phase 3 (Starter templates need objectives to be useful)
- Issue #57 (Starter templates)

**Depends on:**
- Issue #60 Phase 2 ✅ (Python schemas - DONE)

---

## Implementation Notes

### Default Values

If Godot doesn't send objective fields yet, Python will use defaults:
- `scenario_name = ""`
- `objective = None`
- `current_progress = {}`

This ensures backward compatibility during the transition.

### Performance

Objective data is small (~200 bytes) and doesn't change every tick, so performance impact is minimal.

### Future Enhancements

- Dynamic objectives that change mid-episode
- Multi-agent shared objectives
- Objective templates for scenario variants
