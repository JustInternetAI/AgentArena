# Decisions API

How your agent communicates its chosen action back to the system.

## Beginner: Return a String

At the beginner level, just return the tool name:

```python
class SimpleAgentBehavior:
    def decide(self, context: SimpleContext) -> str:
        """Return the name of the tool to use."""
        return "move_to"  # or "collect" or "idle"
```

The framework automatically fills in parameters based on context.

---

## Intermediate+: AgentDecision

For full control, return an `AgentDecision`:

```python
@dataclass
class AgentDecision:
    """A decision about what action to take."""

    tool: str
    """Name of the tool to execute (e.g., "move_to", "collect")."""

    params: dict
    """Parameters for the tool."""

    reasoning: str
    """Explanation of why this action was chosen (for debugging/logging)."""
```

### Constructor

```python
# Full specification
decision = AgentDecision(
    tool="move_to",
    params={"target_position": [10.0, 0.0, 5.0]},
    reasoning="Moving toward nearest apple"
)

# Minimal (empty params, no reasoning)
decision = AgentDecision(tool="idle", params={}, reasoning="")
```

### Static Methods

#### `AgentDecision.idle(reasoning: str = "") -> AgentDecision`

Create an idle decision:

```python
# Quick idle
return AgentDecision.idle()

# Idle with reason
return AgentDecision.idle(reasoning="Waiting for resources to respawn")
```

### Example Usage

```python
from agent_runtime import AgentBehavior, Observation, AgentDecision, ToolSchema


class MyAgent(AgentBehavior):
    def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
        # Check for danger
        if self._in_danger(observation):
            return AgentDecision(
                tool="move_to",
                params={"target_position": self._safe_position(observation)},
                reasoning="Escaping from hazard"
            )

        # Collect if close
        for resource in observation.nearby_resources:
            if resource.distance < 2.0:
                return AgentDecision(
                    tool="collect",
                    params={"resource_id": resource.name},
                    reasoning=f"Collecting nearby {resource.name}"
                )

        # Move toward resource
        if observation.nearby_resources:
            target = observation.nearby_resources[0]
            return AgentDecision(
                tool="move_to",
                params={"target_position": list(target.position)},
                reasoning=f"Moving to {target.name}"
            )

        # Nothing to do
        return AgentDecision.idle(reasoning="No resources visible")
```

---

## ToolSchema

Information about available tools:

```python
@dataclass
class ToolSchema:
    """Schema describing a tool."""

    name: str
    """Tool identifier (e.g., "move_to")."""

    description: str
    """Human-readable description of what the tool does."""

    parameters: list[ParameterSchema]
    """List of parameters the tool accepts."""
```

```python
@dataclass
class ParameterSchema:
    """Schema for a single parameter."""

    name: str
    """Parameter name."""

    type: str
    """Parameter type (e.g., "array", "string", "number")."""

    required: bool
    """Whether the parameter is required."""

    description: str
    """What the parameter does."""
```

### Inspecting Available Tools

```python
def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
    # See what tools are available
    for tool in tools:
        print(f"Tool: {tool.name} - {tool.description}")
        for param in tool.parameters:
            req = "required" if param.required else "optional"
            print(f"  {param.name}: {param.type} ({req})")

    # Check if a specific tool exists
    tool_names = [t.name for t in tools]
    if "craft" in tool_names:
        # Crafting is available in this scenario
        ...
```

---

## Tool Parameters by Action

### move_to

Move toward a target position.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `target_position` | array[3] | Yes | [x, y, z] world position |

```python
AgentDecision(
    tool="move_to",
    params={"target_position": [10.0, 0.0, 5.0]},
    reasoning="Moving to target"
)
```

### collect

Collect a nearby resource.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `resource_id` | string | Yes | Name/ID of the resource |

```python
AgentDecision(
    tool="collect",
    params={"resource_id": "Apple_001"},
    reasoning="Collecting apple"
)
```

### idle

Do nothing this tick.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| (none) | - | - | - |

```python
AgentDecision(
    tool="idle",
    params={},
    reasoning="Resting"
)

# Or use the helper:
AgentDecision.idle(reasoning="Resting")
```

### craft (scenario-dependent)

Craft an item from materials.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `recipe` | string | Yes | Recipe name to craft |

```python
AgentDecision(
    tool="craft",
    params={"recipe": "planks"},
    reasoning="Crafting planks from wood"
)
```

---

## Decision Validation

The framework validates decisions before execution:

1. **Tool exists**: The tool name must match an available tool
2. **Required params**: All required parameters must be provided
3. **Type checking**: Parameters must be the correct type

Invalid decisions are treated as `idle`.

```python
# Invalid - unknown tool (becomes idle)
AgentDecision(tool="teleport", params={}, reasoning="")

# Invalid - missing required param (becomes idle)
AgentDecision(tool="move_to", params={}, reasoning="")

# Invalid - wrong type (becomes idle)
AgentDecision(tool="move_to", params={"target_position": "north"}, reasoning="")
```

---

## Reasoning Field

The `reasoning` field is for debugging and logging:

- It's displayed in the console during simulation
- It helps you understand why your agent made a decision
- It's useful for LLM-based agents to explain their thinking
- Keep it concise (< 200 characters recommended)

```python
# Good reasoning
reasoning="Nearest resource is Apple_001 at 3.2m"
reasoning="Health low (25%), prioritizing escape"
reasoning="Step 3/7: Gathering fiber"

# Too verbose (gets truncated)
reasoning="After careful consideration of all available options and weighing..."
```
