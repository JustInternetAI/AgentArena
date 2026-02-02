# Universal Tools

This document defines the complete set of tools available to agents in Agent Arena. These tools are **universal** - the same tools work in ALL scenarios.

## Design Philosophy

**Scenarios differ by world content, not by APIs.**

- Foraging has resources to collect → use `collect`
- Crafting has stations and recipes → use `craft`
- Team capture has objectives and teammates → use `send_message`

The tools are always available. What matters is what's in the world.

## Tool Overview

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `move_to` | Navigate to a position | Moving toward resources, escaping hazards |
| `collect` | Pick up a nearby resource | Resource is within collection range |
| `craft` | Create an item at a station | Have materials, near station |
| `query_world` | Get detailed surroundings info | Need more information |
| `query_inventory` | Check what you're carrying | Planning crafting, checking progress |
| `send_message` | Communicate with other agents | Multi-agent coordination |
| `idle` | Do nothing this tick | Waiting, no valid action |

---

## Tool Specifications

### move_to

Navigate the agent toward a target position. The game handles pathfinding.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `target_x` | float | Yes | Target X coordinate |
| `target_y` | float | Yes | Target Y coordinate (vertical) |
| `target_z` | float | Yes | Target Z coordinate |
| `speed` | float | No | Speed multiplier (default: 1.0) |

**Shorthand** (alternative format):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `target` | list[float] | Yes | [x, y, z] position |
| `speed` | float | No | Speed multiplier (default: 1.0) |

**Example:**
```python
# Move to position (12, 0, 6)
Decision(
    tool="move_to",
    params={"target_x": 12.0, "target_y": 0.0, "target_z": 6.0}
)

# Or using shorthand
Decision(
    tool="move_to",
    params={"target": [12.0, 0.0, 6.0]}
)

# Move faster
Decision(
    tool="move_to",
    params={"target": [12.0, 0.0, 6.0], "speed": 1.5}
)
```

**Behavior:**
- Agent moves toward target using navigation mesh
- Movement continues until target reached or new command given
- Obstacles are automatically avoided
- Returns success when movement starts (not when destination reached)

**Common Patterns:**
```python
# Move to nearest resource
if obs.nearby_resources:
    closest = min(obs.nearby_resources, key=lambda r: r.distance)
    return Decision(tool="move_to", params={"target": closest.position})

# Move away from hazard
def move_away_from(self, hazard, obs):
    # Calculate direction away from hazard
    dx = obs.position[0] - hazard.position[0]
    dz = obs.position[2] - hazard.position[2]
    # Normalize and scale
    dist = (dx**2 + dz**2) ** 0.5
    if dist > 0:
        dx, dz = dx/dist * 5, dz/dist * 5  # Move 5 units away
    target = [obs.position[0] + dx, 0, obs.position[2] + dz]
    return Decision(tool="move_to", params={"target": target})
```

---

### collect

Pick up a nearby resource and add it to inventory.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `target_name` | string | Yes | Name of the resource to collect |

**Example:**
```python
# Collect a specific resource
Decision(
    tool="collect",
    params={"target_name": "Berry1"}
)
```

**Behavior:**
- Agent must be within collection range (typically 2.0 units)
- Resource is removed from world and added to inventory
- Returns error if resource not in range or doesn't exist
- Collection is instant (no animation delay for now)

**Common Patterns:**
```python
COLLECTION_RANGE = 2.0

def pursue_resources(self, obs):
    if not obs.nearby_resources:
        return Decision.idle()

    closest = min(obs.nearby_resources, key=lambda r: r.distance)

    if closest.distance < COLLECTION_RANGE:
        # In range - collect it
        return Decision(tool="collect", params={"target_name": closest.name})
    else:
        # Not in range - move closer
        return Decision(tool="move_to", params={"target": closest.position})
```

---

### craft

Combine items from inventory at a crafting station.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `item_name` | string | Yes | Name of item to craft |
| `station_name` | string | Yes | Name of the crafting station to use |

**Example:**
```python
# Craft an iron ingot at a furnace
Decision(
    tool="craft",
    params={"item_name": "iron_ingot", "station_name": "Furnace1"}
)
```

**Behavior:**
- Agent must be near the specified station
- Must have required materials in inventory
- Materials are consumed, crafted item added to inventory
- Some recipes take multiple ticks (agent is busy during crafting)
- Returns error if missing materials or not near station

**Common Patterns:**
```python
def attempt_craft(self, obs, item_name):
    # Check if we have the recipe requirements
    recipe = obs.available_recipes.get(item_name)
    if not recipe:
        return None  # Unknown recipe

    # Check materials
    for material, count in recipe.inputs.items():
        if obs.inventory.get(material, 0) < count:
            return None  # Missing materials

    # Find nearest station of correct type
    for station in obs.nearby_stations:
        if station.type == recipe.station_type:
            if station.distance < 3.0:
                return Decision(
                    tool="craft",
                    params={"item_name": item_name, "station_name": station.name}
                )
            else:
                # Move to station first
                return Decision(tool="move_to", params={"target": station.position})

    return None  # No suitable station found
```

---

### query_world

Get detailed information about entities in the world. More detailed than the standard observation.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `radius` | float | No | Search radius in units (default: 20.0) |
| `filter_type` | string | No | Filter by entity type: "resource", "hazard", "agent", "station" |

**Example:**
```python
# Query everything nearby
Decision(
    tool="query_world",
    params={"radius": 30.0}
)

# Query only resources
Decision(
    tool="query_world",
    params={"radius": 20.0, "filter_type": "resource"}
)
```

**Response:**
The query result is included in the next tick's observation under `query_result`:

```python
"query_result": {
    "entities": [
        {
            "name": "Berry1",
            "type": "resource",
            "resource_type": "berry",
            "position": [12.0, 0.5, 6.0],
            "distance": 2.1
        },
        {
            "name": "Furnace1",
            "type": "station",
            "station_type": "furnace",
            "position": [0.0, 0.5, -5.0],
            "distance": 12.3,
            "in_use": false
        }
    ]
}
```

**Common Patterns:**
```python
def explore_area(self, obs):
    # Periodically query for more information
    if obs.tick % 60 == 0:  # Every 60 ticks
        return Decision(tool="query_world", params={"radius": 30.0})
    return self.normal_behavior(obs)
```

---

### query_inventory

Get detailed information about current inventory contents.

**Parameters:** None

**Example:**
```python
Decision(tool="query_inventory", params={})
```

**Response:**
The inventory details are included in the next tick's observation under `inventory_details`:

```python
"inventory_details": {
    "items": [
        {"name": "berry", "count": 5, "type": "food"},
        {"name": "iron_ore", "count": 3, "type": "material"},
        {"name": "wood", "count": 10, "type": "material"}
    ],
    "capacity": 50,
    "used": 18
}
```

**Common Patterns:**
```python
def can_craft(self, item_name, obs):
    recipe = obs.available_recipes.get(item_name)
    if not recipe:
        return False

    for material, needed in recipe.inputs.items():
        have = obs.inventory.get(material, 0)
        if have < needed:
            return False
    return True
```

---

### send_message

Send a message to other agents. Used for multi-agent coordination.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `message` | string | Yes | Message content |
| `target_agent` | string | No | Specific agent ID, or "all" for broadcast (default: "all") |

**Example:**
```python
# Broadcast to all teammates
Decision(
    tool="send_message",
    params={"message": "I'm capturing point A", "target_agent": "all"}
)

# Send to specific agent
Decision(
    tool="send_message",
    params={"message": "Need backup!", "target_agent": "agent_002"}
)
```

**Behavior:**
- Messages delivered to target agent(s) on next tick
- Received messages appear in observation under `messages`
- Range-limited: only agents within communication range receive messages
- No guaranteed delivery (simulates real-world communication)

**Response (in receiver's observation):**
```python
"messages": [
    {
        "from": "agent_001",
        "content": "I'm capturing point A",
        "tick": 142
    }
]
```

**Common Patterns:**
```python
def coordinate_capture(self, obs):
    # Check for messages from teammates
    for msg in obs.messages:
        if "capturing" in msg.content:
            # Teammate is capturing, go to different point
            return self.find_unclaimed_point(obs)

    # Announce our intention
    if self.current_target:
        return Decision(
            tool="send_message",
            params={"message": f"Capturing {self.current_target}"}
        )
```

---

### idle

Do nothing this tick. Agent stays in place.

**Parameters:** None

**Example:**
```python
Decision(tool="idle", params={})

# Or use the helper
Decision.idle()
```

**Behavior:**
- Agent does not move or take any action
- Still receives observations
- Use when waiting or when no valid action available

**Common Patterns:**
```python
def decide(self, obs):
    # No resources visible, nothing to do
    if not obs.nearby_resources and not obs.nearby_hazards:
        return Decision.idle()

    # ... rest of logic
```

---

## Error Handling

Tools can fail. When they do, the next observation includes an error:

```python
"last_action_result": {
    "success": false,
    "error_code": "OUT_OF_RANGE",
    "error_message": "Target 'Berry1' is 5.2 units away, collection range is 2.0"
}
```

**Common Error Codes:**

| Code | Description |
|------|-------------|
| `OUT_OF_RANGE` | Target too far away |
| `NOT_FOUND` | Target doesn't exist |
| `MISSING_MATERIALS` | Don't have required items |
| `INVALID_PARAMS` | Bad parameter values |
| `BUSY` | Agent is already performing an action |

**Handling Errors:**
```python
def decide(self, obs):
    # Check if last action failed
    if obs.last_action_result and not obs.last_action_result.success:
        error = obs.last_action_result.error_code
        if error == "OUT_OF_RANGE":
            # Move closer and retry
            return Decision(tool="move_to", params={"target": self.last_target})

    # Normal logic
    ...
```

---

## Tool Availability by Scenario

All tools are always available. What varies is what's useful:

| Tool | Foraging | Crafting | Team Capture |
|------|----------|----------|--------------|
| `move_to` | ✓ Essential | ✓ Essential | ✓ Essential |
| `collect` | ✓ Primary action | ✓ Gathering phase | ○ Limited use |
| `craft` | ○ Not used | ✓ Primary action | ○ Not used |
| `query_world` | ✓ Useful | ✓ Useful | ✓ Useful |
| `query_inventory` | ✓ Track progress | ✓ Essential | ○ Limited use |
| `send_message` | ○ Not used | ○ Not used | ✓ Essential |
| `idle` | ✓ Fallback | ✓ Fallback | ✓ Fallback |

✓ = Commonly used, ○ = Rarely used or not applicable

---

## Decision Helper Class

The SDK provides a `Decision` helper:

```python
from agent_arena_sdk import Decision

# Create a decision with tool and params
d = Decision(tool="move_to", params={"target": [1, 0, 2]})

# Add reasoning (optional, for debugging)
d = Decision(
    tool="collect",
    params={"target_name": "Berry1"},
    reasoning="Nearest resource, within range"
)

# Helper for idle
d = Decision.idle()

# Check decision properties
print(d.tool)        # "move_to"
print(d.params)      # {"target": [1, 0, 2]}
print(d.reasoning)   # Optional explanation
```

---

## References

- [Objective Schema](objective_schema.md) - How scenarios define goals
- [Learner Developer Experience](learner_developer_experience.md) - Overall architecture
- [IPC Protocol](ipc_protocol.md) - Full message format
