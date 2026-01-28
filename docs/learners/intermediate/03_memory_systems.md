# Memory Systems

Memory is what transforms a reactive agent into an intelligent one. Without memory, your agent treats each tick as completely independent - it can't learn, plan, or remember what it's already done.

## Why Memory Matters

```python
# Without memory: Agent might revisit the same spot repeatedly
# Tick 1: "Oh, an apple at (5, 0, 3)!" → moves there
# Tick 50: "Oh, an apple at (5, 0, 3)!" → moves there (it was collected!)

# With memory: Agent remembers what it's done
# Tick 1: "Apple at (5, 0, 3)!" → moves there, remembers location
# Tick 50: "I already collected that apple" → goes elsewhere
```

## Built-in Memory Systems

Agent Arena provides memory implementations you can use directly.

### SlidingWindowMemory

Stores the last N observations. Simple and effective.

```python
from agent_runtime.memory import SlidingWindowMemory

class RememberingAgent(AgentBehavior):
    def __init__(self, memory_capacity: int = 10):
        self.memory = SlidingWindowMemory(capacity=memory_capacity)

    def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
        # Store current observation
        self.memory.store(observation)

        # Retrieve past observations
        past = self.memory.retrieve()  # Returns list[Observation]

        # Get a summary (useful for prompts)
        summary = self.memory.summarize()  # Returns string

        # Your decision logic using memory...
```

**Use cases:**
- Detecting if you're stuck (same position multiple ticks)
- Tracking collected resources
- Observing patterns over time

### SummarizingMemory

Uses an LLM to compress observations into text summaries. Useful for long-term memory.

```python
from agent_runtime.memory import SummarizingMemory

class LongTermAgent(AgentBehavior):
    def __init__(self, backend):
        self.memory = SummarizingMemory(
            backend=backend,
            window_size=20,       # Observations before summarizing
            summary_length=200    # Max characters in summary
        )

    def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
        self.memory.store(observation)

        # Get compressed summary of entire history
        history_summary = self.memory.summarize()
        # → "Agent explored NW quadrant, collected 3 apples, avoided 2 pits..."
```

## Memory Interface

All memory systems implement this interface:

```python
class AgentMemory(ABC):
    @abstractmethod
    def store(self, observation: Observation) -> None:
        """Store an observation."""
        pass

    @abstractmethod
    def retrieve(self, query: str | None = None) -> list[Observation]:
        """Retrieve relevant observations."""
        pass

    @abstractmethod
    def summarize(self) -> str:
        """Return memory as string (for LLM context)."""
        pass

    def clear(self) -> None:
        """Clear all memory."""
        pass
```

## Practical Memory Patterns

### Pattern 1: Visited Locations

Track where you've been to avoid revisiting:

```python
class ExplorerAgent(AgentBehavior):
    def __init__(self):
        self.memory = SlidingWindowMemory(capacity=50)
        self.visited_positions = set()

    def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
        self.memory.store(observation)

        # Round position to grid cell (1 unit = 1 cell)
        pos = observation.position
        grid_pos = (round(pos[0]), round(pos[2]))
        self.visited_positions.add(grid_pos)

        # Find unvisited resources
        unvisited = []
        for resource in observation.nearby_resources:
            r_pos = (round(resource.position[0]), round(resource.position[2]))
            if r_pos not in self.visited_positions:
                unvisited.append(resource)

        if unvisited:
            target = min(unvisited, key=lambda r: r.distance)
            return AgentDecision(
                tool="move_to",
                params={"target_position": list(target.position)},
                reasoning=f"Moving to unvisited resource: {target.name}"
            )

        return AgentDecision.idle(reasoning="All locations visited")
```

### Pattern 2: Stuck Detection

Detect when you're not making progress:

```python
class AntiStuckAgent(AgentBehavior):
    def __init__(self):
        self.memory = SlidingWindowMemory(capacity=10)
        self.stuck_threshold = 5  # ticks without movement

    def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
        self.memory.store(observation)

        # Check if stuck
        if self._is_stuck():
            return self._escape_stuck(observation)

        # Normal decision logic...

    def _is_stuck(self) -> bool:
        """Check if position hasn't changed recently."""
        past = self.memory.retrieve()
        if len(past) < self.stuck_threshold:
            return False

        # Compare current to oldest in window
        recent = past[-self.stuck_threshold:]
        positions = [obs.position for obs in recent]

        # Check if all positions are very similar
        first = positions[0]
        for pos in positions[1:]:
            dist = sum((a-b)**2 for a, b in zip(first, pos)) ** 0.5
            if dist > 0.5:  # Moved more than 0.5 units
                return False
        return True

    def _escape_stuck(self, observation: Observation) -> AgentDecision:
        """Try to escape stuck state."""
        import random
        # Move in random direction
        angle = random.uniform(0, 6.28)
        escape_pos = [
            observation.position[0] + 5.0 * math.cos(angle),
            observation.position[1],
            observation.position[2] + 5.0 * math.sin(angle)
        ]
        return AgentDecision(
            tool="move_to",
            params={"target_position": escape_pos},
            reasoning="Escaping stuck state"
        )
```

### Pattern 3: Resource Tracking

Remember which resources were collected:

```python
class ResourceTracker(AgentBehavior):
    def __init__(self):
        self.memory = SlidingWindowMemory(capacity=100)
        self.collected_resources = set()  # Names of collected resources

    def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
        self.memory.store(observation)

        # Track newly collected resources
        current_inventory = {item.name for item in observation.inventory}
        new_items = current_inventory - self.collected_resources
        if new_items:
            print(f"Collected: {new_items}")
            self.collected_resources.update(new_items)

        # Find resources we haven't collected yet
        available = [
            r for r in observation.nearby_resources
            if r.name not in self.collected_resources
        ]

        if available:
            target = min(available, key=lambda r: r.distance)
            return AgentDecision(
                tool="move_to",
                params={"target_position": list(target.position)},
                reasoning=f"Targeting uncollected: {target.name}"
            )

        return AgentDecision.idle(reasoning="All known resources collected")
```

## Episode Lifecycle

Memory should be reset between episodes:

```python
class EpisodicAgent(AgentBehavior):
    def __init__(self):
        self.memory = SlidingWindowMemory(capacity=50)
        self.episode_count = 0

    def on_episode_start(self) -> None:
        """Called when new episode begins."""
        self.memory.clear()
        self.episode_count += 1
        print(f"Starting episode {self.episode_count}")

    def on_episode_end(self, success: bool, metrics: dict | None = None) -> None:
        """Called when episode ends."""
        summary = self.memory.summarize()
        print(f"Episode {self.episode_count} ended. Success: {success}")
        print(f"Memory summary: {summary}")

        # Could save metrics, learn from experience, etc.

    def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
        self.memory.store(observation)
        # Decision logic...
```

## Memory Tips

1. **Choose the right capacity** - Too small and you forget important info. Too large and you waste computation.

2. **Clear on reset** - Always clear memory when the episode restarts.

3. **Use appropriate granularity** - Don't remember every tiny detail. Abstract when possible.

4. **Consider what to remember** - Not all observations are equally important. Maybe only store observations when something changes.

```python
def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
    # Only store if something changed
    if self._significant_change(observation):
        self.memory.store(observation)

def _significant_change(self, obs: Observation) -> bool:
    past = self.memory.retrieve()
    if not past:
        return True
    last = past[-1]
    # Check if position changed significantly
    dist = sum((a-b)**2 for a,b in zip(obs.position, last.position)) ** 0.5
    return dist > 1.0  # More than 1 unit moved
```

## Next Steps

- [State Tracking](04_state_tracking.md) - Managing state across episodes
- [Crafting Challenge](05_crafting_challenge.md) - Apply memory to multi-step tasks
