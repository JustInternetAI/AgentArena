# Available Tools

## What are Tools?

**Tools** are actions your agent can take. Each tick, your agent chooses ONE tool to use. The framework then executes that tool in the simulation.

At the beginner level, you just return the tool name - the framework figures out the parameters automatically.

## Core Tools

### `move_to` - Movement

Move toward a target position.

```python
def decide(self, context: SimpleContext) -> str:
    return "move_to"
```

**Automatic behavior:**
- If there are nearby resources → moves toward the closest one
- If there are nearby hazards → moves away from the closest one
- If neither → stays in place

**What you DON'T need to worry about:**
- Pathfinding (handled automatically)
- Obstacle avoidance (handled automatically)
- Movement speed (uses sensible default)

### `idle` - Do Nothing

Wait and do nothing this tick.

```python
def decide(self, context: SimpleContext) -> str:
    return "idle"
```

**When to use:**
- Waiting for something to happen
- No good options available
- Observing the environment

### `collect` - Pick Up Resource

Collect a nearby resource (must be within range).

```python
def decide(self, context: SimpleContext) -> str:
    if context.nearby_resources:
        closest = min(context.nearby_resources, key=lambda r: r["distance"])
        if closest["distance"] < 2.0:  # Within collection range
            return "collect"
    return "move_to"  # Get closer first
```

**Automatic behavior:**
- Collects the nearest resource within range
- Adds it to your inventory

## Tool Selection Strategy

Your agent's intelligence comes from choosing the RIGHT tool at the RIGHT time:

### Bad Strategy: Always Move
```python
def decide(self, context: SimpleContext) -> str:
    return "move_to"  # Will walk into hazards!
```

### Better Strategy: Avoid Hazards
```python
def decide(self, context: SimpleContext) -> str:
    # Check for danger first
    for hazard in context.nearby_hazards:
        if hazard["distance"] < 3.0:
            return "move_to"  # Move away from hazard

    # Then go for resources
    if context.nearby_resources:
        return "move_to"

    return "idle"
```

### Best Strategy: Prioritized Decision
```python
def decide(self, context: SimpleContext) -> str:
    # 1. IMMEDIATE DANGER - escape!
    close_hazards = [h for h in context.nearby_hazards if h["distance"] < 2.0]
    if close_hazards:
        return "move_to"  # Framework moves away

    # 2. RESOURCE IN RANGE - collect it!
    if context.nearby_resources:
        closest = min(context.nearby_resources, key=lambda r: r["distance"])
        if closest["distance"] < 2.0:
            return "collect"

    # 3. RESOURCE VISIBLE - go get it!
    if context.nearby_resources:
        return "move_to"

    # 4. NOTHING TO DO
    return "idle"
```

## How the Framework Infers Parameters

When you return just a tool name, the framework figures out the details:

| Tool | Parameter Inference |
|------|---------------------|
| `move_to` | Target = nearest resource, or away from nearest hazard |
| `collect` | Item = nearest resource within range |
| `idle` | No parameters needed |

This means your beginner code stays simple:
```python
return "move_to"  # You don't specify WHERE to move
```

At the intermediate level, you'll have full control over parameters.

## Scenario-Specific Tools

Some scenarios add extra tools:

### Crafting Scenarios
- `craft` - Combine inventory items
- `use` - Use an item

### Multi-Agent Scenarios
- `communicate` - Send message to other agents
- `coordinate` - Request team action

These are covered in scenario-specific guides.

## Common Mistakes

### Mistake 1: Forgetting to Return a String
```python
def decide(self, context: SimpleContext) -> str:
    if context.nearby_resources:
        "move_to"  # WRONG - forgot 'return'!
```

### Mistake 2: Returning Invalid Tool Name
```python
def decide(self, context: SimpleContext) -> str:
    return "go_to"  # WRONG - should be "move_to"
```

### Mistake 3: Ignoring Hazards
```python
def decide(self, context: SimpleContext) -> str:
    # WRONG - never checks for hazards!
    if context.nearby_resources:
        return "move_to"
    return "idle"
```

## Debugging Tool Selection

Add print statements to understand your agent's decisions:

```python
def decide(self, context: SimpleContext) -> str:
    print(f"Tick {context.tick}: pos={context.position}")
    print(f"  Resources: {len(context.nearby_resources)}")
    print(f"  Hazards: {len(context.nearby_hazards)}")

    if context.nearby_hazards:
        closest = min(context.nearby_hazards, key=lambda h: h["distance"])
        print(f"  Closest hazard: {closest['name']} at {closest['distance']:.1f}")

    # Your decision logic here...
    tool = "idle"
    print(f"  Decision: {tool}")
    return tool
```

## Next Steps

Now that you understand tools:
- [Build your first agent](04_your_first_agent.md) - Put observations and tools together!
- [Foraging Challenge](05_foraging_challenge.md) - Test your skills
