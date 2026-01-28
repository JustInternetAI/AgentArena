# Understanding Observations

## What is an Observation?

An **observation** is everything your agent knows about the world at this moment. It's like your agent's "senses" - what it can see, feel, and know.

At the beginner level, you receive a `SimpleContext` with the essential information:

```python
class SimpleContext:
    position: tuple[float, float, float]  # Where am I? (x, y, z)
    nearby_resources: list[dict]          # What can I collect?
    nearby_hazards: list[dict]            # What should I avoid?
    inventory: list[str]                  # What am I carrying?
    goal: str | None                      # What am I trying to do?
    tick: int                             # What time is it?
```

## Your Position

```python
context.position  # → (5.0, 0.0, 3.0)
```

This is where your agent is in 3D space:
- `x` - Left/Right
- `y` - Up/Down (usually 0 for ground-based agents)
- `z` - Forward/Back

You don't need to do complex math with positions - just know that resources and hazards also have positions, and the framework calculates distances for you.

## Nearby Resources

```python
context.nearby_resources  # → List of things you can collect
```

Each resource is a dictionary:
```python
{
    "name": "Apple",           # What is it?
    "type": "berry",           # Category (berry, wood, stone)
    "position": (3.0, 0.5, 2.0),  # Where is it?
    "distance": 2.5            # How far away? (lower = closer)
}
```

**Common patterns:**

```python
# Check if there are any resources
if context.nearby_resources:
    print("I see something to collect!")

# Find the closest resource
if context.nearby_resources:
    closest = min(context.nearby_resources, key=lambda r: r["distance"])
    print(f"Nearest resource is {closest['name']} at distance {closest['distance']}")

# Find resources of a specific type
apples = [r for r in context.nearby_resources if r["type"] == "berry"]
```

## Nearby Hazards

```python
context.nearby_hazards  # → List of dangerous things
```

Each hazard is a dictionary:
```python
{
    "name": "Pit",             # What is it?
    "type": "pit",             # Category (pit, fire)
    "position": (7.0, 0.0, 4.0),  # Where is it?
    "distance": 3.0,           # How far away?
    "damage": 25.0             # How much it hurts
}
```

**Common patterns:**

```python
# Check if any hazard is dangerously close
DANGER_DISTANCE = 3.0
for hazard in context.nearby_hazards:
    if hazard["distance"] < DANGER_DISTANCE:
        print(f"WARNING: {hazard['name']} is too close!")

# Find the most dangerous nearby hazard
if context.nearby_hazards:
    closest_hazard = min(context.nearby_hazards, key=lambda h: h["distance"])
```

## Inventory

```python
context.inventory  # → ["Apple", "Wood"]
```

A simple list of item names you're carrying. At the beginner level, you just see names.

```python
# Check if carrying anything
if context.inventory:
    print(f"Carrying {len(context.inventory)} items")

# Check for specific item
if "Apple" in context.inventory:
    print("I have an apple!")
```

## Goal

```python
context.goal  # → "Collect all resources" or None
```

The goal is optionally set by the scenario. It tells your agent what it's trying to accomplish.

## Tick

```python
context.tick  # → 42
```

The current simulation tick (time step). Useful for:
- Tracking how long something is taking
- Time-based strategies
- Debugging

## Putting It All Together

Here's how you might use observations in a decision:

```python
def decide(self, context: SimpleContext) -> str:
    # Priority 1: Avoid danger
    for hazard in context.nearby_hazards:
        if hazard["distance"] < 2.0:
            return "move_to"  # Framework moves away from hazard

    # Priority 2: Collect resources
    if context.nearby_resources:
        return "move_to"  # Framework moves toward nearest resource

    # Priority 3: Nothing to do
    return "idle"
```

## What You DON'T See

At the beginner level, the framework hides complexity:

| Hidden | Why |
|--------|-----|
| How observations are gathered | C++ handles raycasting, spatial queries |
| Exact sensor mechanics | Just trust the distances |
| Other agents (in single-agent scenarios) | Simplified for learning |
| Detailed entity information | You get what you need |

As you advance to intermediate level, you'll get access to more detailed observations.

## Next Steps

Now that you understand observations:
- [Learn about tools](03_tools.md) - What actions your agent can take
- [Build your first agent](04_your_first_agent.md) - Put it all together!
