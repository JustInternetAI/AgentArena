# Tools API

Available actions your agent can take in the simulation.

## Core Tools

These tools are available in most scenarios:

### move_to

Move the agent toward a target position.

```python
AgentDecision(
    tool="move_to",
    params={"target_position": [10.0, 0.0, 5.0]},
    reasoning="Moving to target"
)
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `target_position` | array[3] | Yes | [x, y, z] world coordinates |

**Behavior:**
- Agent moves toward the target at its movement speed
- Movement happens over multiple ticks (not teleportation)
- Agent stops when within ~0.5 units of target
- Movement is blocked by obstacles

**Beginner mode:**
- Framework automatically selects nearest resource as target
- Or moves away from nearest hazard if in danger

**Tips:**
```python
# Move to a resource
target = observation.nearby_resources[0]
params = {"target_position": list(target.position)}

# Move to a specific coordinate
params = {"target_position": [15.0, 0.0, 20.0]}

# Move away from hazard
hazard = observation.nearby_hazards[0]
direction = [
    observation.position[0] - hazard.position[0],
    0,
    observation.position[2] - hazard.position[2]
]
# Normalize and scale
import math
length = math.sqrt(direction[0]**2 + direction[2]**2)
if length > 0:
    escape = [
        observation.position[0] + (direction[0] / length) * 5,
        0,
        observation.position[2] + (direction[2] / length) * 5
    ]
    params = {"target_position": escape}
```

---

### collect

Collect a nearby resource.

```python
AgentDecision(
    tool="collect",
    params={"resource_id": "Apple_001"},
    reasoning="Collecting apple"
)
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `resource_id` | string | Yes | Name/ID of the resource to collect |

**Behavior:**
- Resource must be within collection range (~2 units)
- Resource is removed from world and added to inventory
- Fails silently if resource is too far or doesn't exist

**Beginner mode:**
- Framework automatically selects nearest resource
- Only executes if resource is in range

**Tips:**
```python
# Check if in range first
def can_collect(self, obs: Observation) -> bool:
    for resource in obs.nearby_resources:
        if resource.distance < 2.0:
            return True
    return False

# Collect the nearest collectible resource
def collect_nearest(self, obs: Observation) -> AgentDecision:
    in_range = [r for r in obs.nearby_resources if r.distance < 2.0]
    if in_range:
        target = min(in_range, key=lambda r: r.distance)
        return AgentDecision(
            tool="collect",
            params={"resource_id": target.name},
            reasoning=f"Collecting {target.name}"
        )
    return AgentDecision.idle(reasoning="Nothing in range")
```

---

### idle

Do nothing this tick.

```python
AgentDecision(
    tool="idle",
    params={},
    reasoning="Waiting for opportunity"
)

# Or use the helper
AgentDecision.idle(reasoning="Waiting for opportunity")
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| (none) | - | - | No parameters needed |

**Behavior:**
- Agent stays in place
- Energy may regenerate (scenario-dependent)
- Use when no action is beneficial

**When to idle:**
- All resources collected
- Waiting for something to happen
- Recovering energy
- No valid action available

---

## Scenario-Specific Tools

These tools are only available in certain scenarios:

### craft

Craft an item from materials in inventory.

```python
AgentDecision(
    tool="craft",
    params={"recipe": "planks"},
    reasoning="Crafting planks from wood"
)
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `recipe` | string | Yes | Recipe name to craft |

**Behavior:**
- Checks if required materials are in inventory
- Consumes materials and creates the crafted item
- Fails if materials are insufficient

**Available recipes (crafting scenarios):**
```
planks = wood × 2
rope = fiber × 3
shelter = planks × 4 + rope × 2 + stone × 3
```

**Example:**
```python
RECIPES = {
    "planks": {"wood": 2},
    "rope": {"fiber": 3},
    "shelter": {"planks": 4, "rope": 2, "stone": 3}
}

def can_craft(self, recipe: str, obs: Observation) -> bool:
    required = RECIPES.get(recipe, {})
    inventory = {}
    for item in obs.inventory:
        name = item.name.lower()
        inventory[name] = inventory.get(name, 0) + item.quantity

    for material, quantity in required.items():
        if inventory.get(material, 0) < quantity:
            return False
    return True
```

---

## Checking Available Tools

At runtime, check what tools are available:

```python
def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
    # Get tool names
    available = [t.name for t in tools]

    # Check for specific tool
    if "craft" in available:
        # Crafting scenario - can try to craft
        ...

    # Inspect tool parameters
    for tool in tools:
        print(f"{tool.name}: {tool.description}")
        for param in tool.parameters:
            print(f"  - {param.name} ({param.type}): {param.description}")
```

---

## Tool Results

After a tool executes, `on_tool_result` is called:

```python
def on_tool_result(self, tool: str, result: dict) -> None:
    """Called after each tool execution."""

    # Common result fields
    success = result.get("success", False)
    error = result.get("error", None)

    if tool == "collect":
        if success:
            item = result.get("item")
            print(f"Collected: {item}")
        else:
            print(f"Collection failed: {error}")

    elif tool == "move_to":
        if success:
            new_pos = result.get("position")
            print(f"Moved to: {new_pos}")
        else:
            reason = result.get("blocked_by")
            print(f"Movement blocked: {reason}")

    elif tool == "craft":
        if success:
            crafted = result.get("item")
            print(f"Crafted: {crafted}")
        else:
            missing = result.get("missing_materials")
            print(f"Cannot craft - missing: {missing}")
```

---

## Tool Selection Strategy

```python
def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
    # Priority 1: Escape danger
    if self._in_danger(observation):
        return self._escape(observation)

    # Priority 2: Collect if possible
    in_range = [r for r in observation.nearby_resources if r.distance < 2.0]
    if in_range:
        target = in_range[0]
        return AgentDecision(
            tool="collect",
            params={"resource_id": target.name},
            reasoning=f"Collecting {target.name}"
        )

    # Priority 3: Craft if possible
    if "craft" in [t.name for t in tools]:
        if self._can_craft_something(observation):
            return self._craft_next(observation)

    # Priority 4: Move toward resource
    if observation.nearby_resources:
        target = min(observation.nearby_resources, key=lambda r: r.distance)
        return AgentDecision(
            tool="move_to",
            params={"target_position": list(target.position)},
            reasoning=f"Moving to {target.name}"
        )

    # Priority 5: Explore
    return self._explore(observation)

    # Fallback: Idle
    return AgentDecision.idle(reasoning="Nothing to do")
```
