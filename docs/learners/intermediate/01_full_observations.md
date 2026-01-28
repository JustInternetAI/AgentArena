# Full Observation Details

Welcome to the intermediate level! You now have access to the complete `Observation` dataclass with full type information and more detailed data.

## From SimpleContext to Observation

At the beginner level, you received `SimpleContext` - a simplified view. Now you work directly with `Observation`:

```python
# Beginner: SimpleContext
def decide(self, context: SimpleContext) -> str:
    context.nearby_resources  # List of dicts

# Intermediate: Full Observation
def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
    observation.nearby_resources  # List of ResourceInfo objects
```

## The Observation Dataclass

```python
from dataclasses import dataclass

@dataclass
class Observation:
    # Identity
    agent_id: str                           # Your unique identifier
    tick: int                               # Current simulation tick

    # Spatial State
    position: tuple[float, float, float]    # (x, y, z) location
    rotation: tuple[float, float, float] | None  # Facing direction (if available)
    velocity: tuple[float, float, float] | None  # Movement speed (if available)

    # Perception
    visible_entities: list[EntityInfo]      # All visible entities
    nearby_resources: list[ResourceInfo]    # Collectible resources
    nearby_hazards: list[HazardInfo]        # Dangerous areas

    # Agent State
    inventory: list[ItemInfo]               # Items you're carrying
    health: float                           # 0-100
    energy: float                           # 0-100

    # Scenario-Specific
    custom: dict                            # Extra data from the scenario
```

## Typed Data Classes

Instead of raw dictionaries, you now get typed objects:

### ResourceInfo
```python
@dataclass
class ResourceInfo:
    name: str                               # "Apple", "Wood", etc.
    type: str                               # "berry", "wood", "stone"
    position: tuple[float, float, float]    # Exact location
    distance: float                         # Distance from you
```

**Using ResourceInfo:**
```python
def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
    for resource in observation.nearby_resources:
        # Typed access - IDE autocomplete works!
        print(f"{resource.name} at {resource.position}, {resource.distance:.1f} units away")

        # Type checking catches errors
        resource.name      # ✓ str
        resource.distance  # ✓ float
        resource.foo       # ✗ Error: no attribute 'foo'
```

### HazardInfo
```python
@dataclass
class HazardInfo:
    name: str                               # "Pit", "Fire"
    type: str                               # "pit", "fire"
    position: tuple[float, float, float]    # Exact location
    distance: float                         # Distance from you
    damage: float                           # Damage if touched (0 for some hazards)
```

### ItemInfo (Inventory)
```python
@dataclass
class ItemInfo:
    id: str                                 # Unique item ID
    name: str                               # "Apple", "Wood"
    quantity: int                           # Stack size (default 1)
```

**Using ItemInfo:**
```python
# Beginner: Just names
# context.inventory → ["Apple", "Wood"]

# Intermediate: Full item info
# observation.inventory → [ItemInfo(id="item_1", name="Apple", quantity=1), ...]

for item in observation.inventory:
    print(f"Carrying {item.quantity}x {item.name} (id: {item.id})")
```

### EntityInfo (Visible Entities)
```python
@dataclass
class EntityInfo:
    id: str                                 # Entity identifier
    type: str                               # "agent", "npc", "object"
    position: tuple[float, float, float]    # Location
    distance: float                         # Distance from you
    metadata: dict                          # Extra entity data
```

This is used in multi-agent scenarios to see other agents.

## Health and Energy

```python
observation.health  # 0-100, you die at 0
observation.energy  # 0-100, affects actions (scenario-dependent)
```

Track your vitals:
```python
def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
    if observation.health < 30:
        print("WARNING: Low health!")
        # Maybe prioritize safety over collection

    if observation.energy < 20:
        print("WARNING: Low energy!")
        # Maybe rest (idle) to recover
```

## Custom Data

Scenarios can add extra data:
```python
observation.custom  # Dict with scenario-specific info
```

Example in foraging:
```python
{
    "resources_remaining": 5,
    "resources_collected": 2,
    "time_limit": 120
}
```

## Position Math

With full positions, you can do vector math:

```python
import math

def distance_between(pos1, pos2) -> float:
    """Calculate 3D distance between two points."""
    dx = pos1[0] - pos2[0]
    dy = pos1[1] - pos2[1]
    dz = pos1[2] - pos2[2]
    return math.sqrt(dx*dx + dy*dy + dz*dz)

def direction_to(from_pos, to_pos) -> tuple[float, float, float]:
    """Get normalized direction vector."""
    dx = to_pos[0] - from_pos[0]
    dy = to_pos[1] - from_pos[1]
    dz = to_pos[2] - from_pos[2]
    dist = math.sqrt(dx*dx + dy*dy + dz*dz)
    if dist == 0:
        return (0, 0, 0)
    return (dx/dist, dy/dist, dz/dist)

# Usage:
def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
    my_pos = observation.position

    # Find resource that's NOT near a hazard
    for resource in observation.nearby_resources:
        # Check if any hazard is between us and the resource
        resource_dir = direction_to(my_pos, resource.position)
        is_safe = True

        for hazard in observation.nearby_hazards:
            hazard_dist = hazard.distance
            if hazard_dist < resource.distance:
                # Hazard might be in the way
                hazard_dir = direction_to(my_pos, hazard.position)
                # Simple check: are directions similar?
                dot = sum(a*b for a,b in zip(resource_dir, hazard_dir))
                if dot > 0.8:  # Pointing roughly same direction
                    is_safe = False
                    break

        if is_safe:
            return AgentDecision(
                tool="move_to",
                params={"target_position": list(resource.position)},
                reasoning=f"Moving to safe resource: {resource.name}"
            )
```

## Converting Observation to Dict

For logging or serialization:
```python
obs_dict = observation.to_dict()
print(json.dumps(obs_dict, indent=2))
```

## Next Steps

Now that you understand full observations:
- [Explicit Parameters](02_explicit_parameters.md) - Take control of tool parameters
- [Memory Systems](03_memory_systems.md) - Remember past observations
