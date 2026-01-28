# Memory API

Built-in memory systems for tracking past observations.

## SlidingWindowMemory

A fixed-size buffer that stores the most recent observations:

```python
from agent_runtime.memory import SlidingWindowMemory
from agent_runtime import Observation


class MyAgent(AgentBehavior):
    def __init__(self):
        # Store last 50 observations
        self.memory = SlidingWindowMemory(capacity=50)

    def on_episode_start(self):
        self.memory.clear()

    def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
        # Store current observation
        self.memory.store(observation)

        # Retrieve past observations
        past = self.memory.retrieve()
        print(f"Have {len(past)} observations in memory")

        # Use memory for decisions
        if self._am_i_stuck(past):
            return self._try_different_direction(observation)

        ...
```

### Constructor

```python
SlidingWindowMemory(capacity: int = 100)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `capacity` | int | 100 | Maximum number of observations to store |

### Methods

#### `store(observation: Observation) -> None`

Store an observation. If at capacity, oldest observation is removed.

```python
def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
    self.memory.store(observation)
    ...
```

#### `retrieve(count: int | None = None) -> list[Observation]`

Retrieve stored observations, oldest first.

```python
# Get all observations
all_obs = self.memory.retrieve()

# Get last 5 observations
recent = self.memory.retrieve(5)

# Get most recent observation
if recent:
    last = recent[-1]
```

#### `clear() -> None`

Remove all stored observations.

```python
def on_episode_start(self):
    self.memory.clear()  # Start fresh each episode
```

### Properties

#### `capacity: int`

Maximum number of observations that can be stored.

```python
print(f"Memory capacity: {self.memory.capacity}")
```

---

## Memory Interface

For building custom memory systems:

```python
from abc import ABC, abstractmethod
from agent_runtime import Observation


class Memory(ABC):
    """Abstract base class for memory systems."""

    @abstractmethod
    def store(self, observation: Observation) -> None:
        """Store an observation."""
        pass

    @abstractmethod
    def retrieve(self, query: str | None = None) -> list:
        """Retrieve memories, optionally filtered by query."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all stored memories."""
        pass
```

---

## Common Memory Patterns

### Stuck Detection

Detect when the agent isn't making progress:

```python
def _am_i_stuck(self, past_observations: list[Observation], threshold: float = 1.0) -> bool:
    """Check if position hasn't changed significantly."""
    if len(past_observations) < 5:
        return False

    recent = past_observations[-5:]
    first_pos = recent[0].position
    last_pos = recent[-1].position

    distance = sum((a - b) ** 2 for a, b in zip(first_pos, last_pos)) ** 0.5
    return distance < threshold
```

### Position History

Track where the agent has been:

```python
class PositionTrackingAgent(AgentBehavior):
    def __init__(self):
        self.memory = SlidingWindowMemory(capacity=100)
        self.visited_positions = set()
        self.grid_size = 2.0

    def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
        self.memory.store(observation)

        # Track visited grid cells
        cell = (
            int(observation.position[0] // self.grid_size),
            int(observation.position[2] // self.grid_size)
        )
        self.visited_positions.add(cell)

        # Use for exploration
        ...
```

### Health Trend

Track health changes over time:

```python
def _health_trend(self, past_observations: list[Observation]) -> str:
    """Determine if health is improving, declining, or stable."""
    if len(past_observations) < 3:
        return "unknown"

    recent = past_observations[-3:]
    first_health = recent[0].health
    last_health = recent[-1].health

    if last_health > first_health + 5:
        return "improving"
    elif last_health < first_health - 5:
        return "declining"
    else:
        return "stable"
```

### Resource Tracking

Remember where resources were seen:

```python
class ResourceMemoryAgent(AgentBehavior):
    def __init__(self):
        self.memory = SlidingWindowMemory(capacity=50)
        self.known_resources = {}  # name -> (position, last_seen_tick)

    def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
        self.memory.store(observation)

        # Update resource knowledge
        for resource in observation.nearby_resources:
            self.known_resources[resource.name] = (
                resource.position,
                observation.tick
            )

        # Find resource we saw before but can't see now
        remembered = [
            (name, pos, tick)
            for name, (pos, tick) in self.known_resources.items()
            if name not in [r.name for r in observation.nearby_resources]
        ]

        # Go back to a remembered resource
        if remembered and not observation.nearby_resources:
            name, position, _ = remembered[0]
            return AgentDecision(
                tool="move_to",
                params={"target_position": list(position)},
                reasoning=f"Returning to remembered resource: {name}"
            )

        ...
```

### Danger Zone Memory

Remember hazardous areas:

```python
class SafetyMemoryAgent(AgentBehavior):
    def __init__(self):
        self.memory = SlidingWindowMemory(capacity=50)
        self.danger_zones = {}  # name -> position

    def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
        self.memory.store(observation)

        # Remember all hazards seen
        for hazard in observation.nearby_hazards:
            self.danger_zones[hazard.name] = hazard.position

        # Check if target path crosses danger zone
        if observation.nearby_resources:
            target = observation.nearby_resources[0]
            if self._path_crosses_danger(observation.position, target.position):
                return self._find_safe_path(observation, target)

        ...

    def _path_crosses_danger(self, start: tuple, end: tuple, buffer: float = 3.0) -> bool:
        """Check if a path comes too close to known dangers."""
        for name, danger_pos in self.danger_zones.items():
            # Simple distance check (could be improved with line-segment distance)
            mid = [(s + e) / 2 for s, e in zip(start, end)]
            dist = sum((a - b) ** 2 for a, b in zip(mid, danger_pos)) ** 0.5
            if dist < buffer:
                return True
        return False
```

---

## Memory Size Considerations

| Capacity | Use Case | Memory Usage |
|----------|----------|--------------|
| 10-20 | Quick reactions, stuck detection | Low |
| 50-100 | Standard gameplay, pattern recognition | Medium |
| 200+ | Complex planning, extensive history | Higher |

Tips:
- Smaller capacity = faster retrieval, less memory
- Larger capacity = more context for decisions
- Clear memory at episode start unless learning across episodes
