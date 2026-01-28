# Explicit Tool Parameters

At the intermediate level, you have full control over tool parameters using `AgentDecision`.

## From Tool Name to AgentDecision

```python
# Beginner: Just return tool name
def decide(self, context: SimpleContext) -> str:
    return "move_to"  # Framework infers parameters

# Intermediate: Return full decision
def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
    return AgentDecision(
        tool="move_to",
        params={"target_position": [10.0, 0.0, 5.0], "speed": 1.5},
        reasoning="Moving to specific location"
    )
```

## The AgentDecision Dataclass

```python
@dataclass
class AgentDecision:
    tool: str                    # Tool name
    params: dict                 # Tool parameters
    reasoning: str | None = None # Optional explanation
```

## Tool Parameters

### move_to

```python
AgentDecision(
    tool="move_to",
    params={
        "target_position": [x, y, z],  # Where to go (required)
        "speed": 1.0                    # Speed multiplier (optional, default 1.0)
    }
)
```

**Speed values:**
- `0.5` - Slow/cautious movement
- `1.0` - Normal speed (default)
- `1.5` - Fast movement
- `2.0` - Sprint (if supported)

**Examples:**
```python
# Move to exact coordinates
AgentDecision(
    tool="move_to",
    params={"target_position": [10.0, 0.0, 5.0]}
)

# Move toward a resource quickly
target = observation.nearby_resources[0]
AgentDecision(
    tool="move_to",
    params={
        "target_position": list(target.position),
        "speed": 1.5
    },
    reasoning=f"Rushing to collect {target.name}"
)

# Retreat slowly and carefully
AgentDecision(
    tool="move_to",
    params={
        "target_position": safe_position,
        "speed": 0.5
    },
    reasoning="Careful retreat from hazard"
)
```

### collect

```python
AgentDecision(
    tool="collect",
    params={
        "resource_id": "resource_name"  # Which resource to collect
    }
)
```

**Example:**
```python
if observation.nearby_resources:
    closest = min(observation.nearby_resources, key=lambda r: r.distance)
    if closest.distance < 2.0:
        AgentDecision(
            tool="collect",
            params={"resource_id": closest.name},
            reasoning=f"Collecting {closest.name}"
        )
```

### idle

```python
AgentDecision(
    tool="idle",
    params={}  # No parameters needed
)

# Convenience method:
AgentDecision.idle(reasoning="Waiting for better opportunity")
```

## Using Tool Schemas

You receive `tools: list[ToolSchema]` which describes available tools:

```python
@dataclass
class ToolSchema:
    name: str           # "move_to", "collect", etc.
    description: str    # Human-readable description
    parameters: dict    # JSON Schema for parameters
```

**Inspecting tools:**
```python
def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
    # List available tools
    for tool in tools:
        print(f"Tool: {tool.name}")
        print(f"  Description: {tool.description}")
        print(f"  Parameters: {tool.parameters}")

    # Check if a specific tool is available
    tool_names = [t.name for t in tools]
    if "craft" in tool_names:
        # Crafting is available in this scenario
        pass
```

## The Reasoning Field

Always include reasoning - it helps with:
1. **Debugging** - Understand why your agent made a decision
2. **Logging** - Track decision patterns over time
3. **LLM integration** - Some backends use this field

```python
# Good reasoning
AgentDecision(
    tool="move_to",
    params={"target_position": [5, 0, 3]},
    reasoning="Moving to Apple (closest resource, 2.5 units away, no hazards in path)"
)

# Bad reasoning (too vague)
AgentDecision(
    tool="move_to",
    params={"target_position": [5, 0, 3]},
    reasoning="moving"  # Not helpful!
)
```

## Computed Positions

Now you can calculate custom positions:

### Move Away from Hazard
```python
def escape_hazard(self, observation: Observation, hazard: HazardInfo) -> list[float]:
    """Calculate position away from hazard."""
    my_pos = observation.position
    hazard_pos = hazard.position

    # Direction from hazard to me
    dx = my_pos[0] - hazard_pos[0]
    dz = my_pos[2] - hazard_pos[2]

    # Normalize
    dist = (dx*dx + dz*dz) ** 0.5
    if dist > 0:
        dx /= dist
        dz /= dist

    # Move 5 units in escape direction
    escape_dist = 5.0
    return [
        my_pos[0] + dx * escape_dist,
        my_pos[1],
        my_pos[2] + dz * escape_dist
    ]
```

### Move Between Two Points
```python
def midpoint(self, pos1, pos2) -> list[float]:
    """Calculate midpoint between two positions."""
    return [
        (pos1[0] + pos2[0]) / 2,
        (pos1[1] + pos2[1]) / 2,
        (pos1[2] + pos2[2]) / 2
    ]
```

### Move in a Direction
```python
def move_in_direction(self, start, direction, distance) -> list[float]:
    """Move from start in direction by distance."""
    return [
        start[0] + direction[0] * distance,
        start[1] + direction[1] * distance,
        start[2] + direction[2] * distance
    ]
```

## Complete Example

```python
from agent_runtime import AgentBehavior, Observation, AgentDecision, ToolSchema


class IntermediateAgent(AgentBehavior):
    """An intermediate agent with explicit parameter control."""

    DANGER_DISTANCE = 3.0
    COLLECTION_RANGE = 2.0

    def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
        # Check for nearby hazards
        closest_hazard = self._get_closest_hazard(observation)
        if closest_hazard and closest_hazard.distance < self.DANGER_DISTANCE:
            escape_pos = self._calculate_escape(observation, closest_hazard)
            return AgentDecision(
                tool="move_to",
                params={"target_position": escape_pos, "speed": 2.0},
                reasoning=f"ESCAPE: {closest_hazard.name} at {closest_hazard.distance:.1f}"
            )

        # Check for collectible resources
        closest_resource = self._get_closest_resource(observation)
        if closest_resource:
            if closest_resource.distance < self.COLLECTION_RANGE:
                return AgentDecision(
                    tool="collect",
                    params={"resource_id": closest_resource.name},
                    reasoning=f"Collecting {closest_resource.name}"
                )
            else:
                return AgentDecision(
                    tool="move_to",
                    params={
                        "target_position": list(closest_resource.position),
                        "speed": 1.0
                    },
                    reasoning=f"Approaching {closest_resource.name} ({closest_resource.distance:.1f} units)"
                )

        return AgentDecision.idle(reasoning="No targets")

    def _get_closest_hazard(self, obs: Observation) -> HazardInfo | None:
        if not obs.nearby_hazards:
            return None
        return min(obs.nearby_hazards, key=lambda h: h.distance)

    def _get_closest_resource(self, obs: Observation) -> ResourceInfo | None:
        if not obs.nearby_resources:
            return None
        return min(obs.nearby_resources, key=lambda r: r.distance)

    def _calculate_escape(self, obs: Observation, hazard: HazardInfo) -> list[float]:
        my_pos = obs.position
        dx = my_pos[0] - hazard.position[0]
        dz = my_pos[2] - hazard.position[2]
        dist = (dx*dx + dz*dz) ** 0.5 or 1.0
        return [
            my_pos[0] + (dx/dist) * 5.0,
            my_pos[1],
            my_pos[2] + (dz/dist) * 5.0
        ]
```

## Next Steps

- [Memory Systems](03_memory_systems.md) - Remember and learn from past observations
- [State Tracking](04_state_tracking.md) - Manage state across ticks and episodes
