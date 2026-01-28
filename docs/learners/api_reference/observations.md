# Observations API

Observations contain all the information your agent can perceive about the world.

## SimpleContext (Beginner)

Simplified context for beginner agents:

```python
@dataclass
class SimpleContext:
    """Beginner-friendly observation format."""

    position: tuple[float, float, float]
    """Agent's current (x, y, z) position in the world."""

    nearby_resources: list[dict]
    """
    List of visible resources. Each dict contains:
    - "name": str - Resource identifier (e.g., "Apple_001")
    - "type": str - Resource type (e.g., "berry", "wood")
    - "distance": float - Distance from agent
    """

    nearby_hazards: list[dict]
    """
    List of visible hazards. Each dict contains:
    - "name": str - Hazard identifier (e.g., "Pit_001")
    - "type": str - Hazard type (e.g., "pit", "fire")
    - "distance": float - Distance from agent
    """

    inventory: list[str]
    """List of item names in inventory (e.g., ["Apple", "Wood"])."""

    tick: int
    """Current simulation tick (frame number)."""
```

**Example usage:**
```python
def decide(self, context: SimpleContext) -> str:
    print(f"I'm at {context.position}")
    print(f"I can see {len(context.nearby_resources)} resources")

    if context.nearby_resources:
        nearest = min(context.nearby_resources, key=lambda r: r["distance"])
        print(f"Nearest: {nearest['name']} at {nearest['distance']:.1f}m")

    return "move_to"
```

---

## Observation (Intermediate+)

Full observation with typed data classes:

```python
@dataclass
class Observation:
    """Complete observation data."""

    # === Identity ===
    agent_id: str
    """Unique identifier for this agent."""

    tick: int
    """Current simulation tick."""

    # === Spatial State ===
    position: tuple[float, float, float]
    """(x, y, z) world position."""

    rotation: tuple[float, float, float] | None
    """(pitch, yaw, roll) facing direction. May be None."""

    velocity: tuple[float, float, float] | None
    """(vx, vy, vz) movement velocity. May be None."""

    # === Perception ===
    visible_entities: list[EntityInfo]
    """All visible entities (agents, NPCs, objects)."""

    nearby_resources: list[ResourceInfo]
    """Collectible resources in perception range."""

    nearby_hazards: list[HazardInfo]
    """Dangerous areas in perception range."""

    # === Agent State ===
    inventory: list[ItemInfo]
    """Items the agent is carrying."""

    health: float
    """Current health (0-100). Agent dies at 0."""

    energy: float
    """Current energy (0-100). Affects some actions."""

    # === Scenario-Specific ===
    custom: dict
    """Extra data from the scenario."""

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        ...
```

---

## ResourceInfo

Information about a collectible resource:

```python
@dataclass
class ResourceInfo:
    """A collectible resource."""

    name: str
    """Unique identifier (e.g., "Apple_001")."""

    type: str
    """Resource category (e.g., "berry", "wood", "stone")."""

    position: tuple[float, float, float]
    """World position (x, y, z)."""

    distance: float
    """Distance from agent in world units."""
```

**Example:**
```python
def find_nearest_resource(self, obs: Observation, resource_type: str) -> ResourceInfo | None:
    """Find the nearest resource of a specific type."""
    matching = [r for r in obs.nearby_resources if r.type == resource_type]
    if not matching:
        return None
    return min(matching, key=lambda r: r.distance)
```

---

## HazardInfo

Information about a dangerous area:

```python
@dataclass
class HazardInfo:
    """A hazardous area."""

    name: str
    """Unique identifier (e.g., "Pit_001")."""

    type: str
    """Hazard category (e.g., "pit", "fire", "water")."""

    position: tuple[float, float, float]
    """World position (x, y, z)."""

    distance: float
    """Distance from agent in world units."""

    damage: float
    """Damage dealt on contact. 0 for some hazards (e.g., slow areas)."""
```

**Example:**
```python
def is_in_danger(self, obs: Observation, threshold: float = 3.0) -> bool:
    """Check if any hazard is dangerously close."""
    for hazard in obs.nearby_hazards:
        if hazard.distance < threshold:
            return True
    return False
```

---

## ItemInfo

Information about an inventory item:

```python
@dataclass
class ItemInfo:
    """An item in inventory."""

    id: str
    """Unique item identifier."""

    name: str
    """Item display name (e.g., "Apple", "Wood")."""

    quantity: int
    """Stack size (default 1)."""
```

**Example:**
```python
def count_item(self, obs: Observation, item_name: str) -> int:
    """Count how many of an item type we have."""
    total = 0
    for item in obs.inventory:
        if item.name.lower() == item_name.lower():
            total += item.quantity
    return total
```

---

## EntityInfo

Information about a visible entity:

```python
@dataclass
class EntityInfo:
    """A visible entity in the world."""

    id: str
    """Entity identifier."""

    type: str
    """Entity type (e.g., "agent", "npc", "object")."""

    position: tuple[float, float, float]
    """World position."""

    distance: float
    """Distance from agent."""

    metadata: dict
    """Additional entity-specific data."""
```

**Example:**
```python
def find_other_agents(self, obs: Observation) -> list[EntityInfo]:
    """Find all other agents in view."""
    return [e for e in obs.visible_entities if e.type == "agent"]
```

---

## Custom Data

Scenarios can include extra data in `observation.custom`:

```python
# Example custom data in foraging scenario
obs.custom = {
    "resources_remaining": 5,
    "resources_collected": 2,
    "time_limit": 120,
    "score": 75
}

# Accessing custom data
remaining = obs.custom.get("resources_remaining", 0)
```

---

## Coordinate System

Agent Arena uses a right-handed coordinate system:

```
        +Y (up)
         │
         │
         │
         └───────── +X (east)
        /
       /
      /
    +Z (south)
```

- Position `(0, 0, 0)` is typically the world origin
- Y is vertical (height)
- X and Z are horizontal (ground plane)
- Distances are in world units (typically ~1 meter per unit)
