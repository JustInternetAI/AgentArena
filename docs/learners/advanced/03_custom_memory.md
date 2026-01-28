# Custom Memory Systems

Beyond the built-in `SlidingWindowMemory`, you can build sophisticated memory systems that enable complex behaviors.

## Memory Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      MEMORY SYSTEM                           │
├─────────────────────────────────────────────────────────────┤
│  Working Memory          │  Episodic Memory                 │
│  - Current observation   │  - Past observations             │
│  - Active goals          │  - Successful patterns           │
│  - Immediate context     │  - Failure cases                 │
├──────────────────────────┼──────────────────────────────────┤
│  Semantic Memory         │  Spatial Memory                  │
│  - Learned facts         │  - Map of explored areas         │
│  - Entity knowledge      │  - Resource locations            │
│  - General rules         │  - Hazard positions              │
└─────────────────────────────────────────────────────────────┘
```

## The Memory Interface

All memory systems implement this interface:

```python
from abc import ABC, abstractmethod
from agent_runtime import Observation


class Memory(ABC):
    """Base interface for memory systems."""

    @abstractmethod
    def store(self, observation: Observation) -> None:
        """Store an observation."""
        pass

    @abstractmethod
    def retrieve(self, query: str | None = None) -> list:
        """Retrieve relevant memories."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all stored memories."""
        pass
```

## Spatial Memory

Remember where things are in the world:

```python
from dataclasses import dataclass
from typing import Optional
import math


@dataclass
class SpatialMemoryEntry:
    """A remembered location."""
    position: tuple[float, float, float]
    entity_type: str  # "resource", "hazard", "visited"
    entity_name: str
    last_seen_tick: int
    still_exists: bool = True


class SpatialMemory(Memory):
    """Memory system for tracking locations."""

    def __init__(self, grid_size: float = 5.0):
        self.grid_size = grid_size
        self.entries: dict[tuple[int, int], list[SpatialMemoryEntry]] = {}
        self.visited_cells: set[tuple[int, int]] = set()

    def _pos_to_cell(self, pos: tuple) -> tuple[int, int]:
        """Convert position to grid cell."""
        return (int(pos[0] // self.grid_size), int(pos[2] // self.grid_size))

    def store(self, observation: Observation) -> None:
        """Update spatial memory from observation."""
        current_tick = observation.tick

        # Mark current cell as visited
        my_cell = self._pos_to_cell(observation.position)
        self.visited_cells.add(my_cell)

        # Remember resources
        for resource in observation.nearby_resources:
            self._remember_entity(
                position=resource.position,
                entity_type="resource",
                entity_name=resource.name,
                tick=current_tick
            )

        # Remember hazards
        for hazard in observation.nearby_hazards:
            self._remember_entity(
                position=hazard.position,
                entity_type="hazard",
                entity_name=hazard.name,
                tick=current_tick
            )

    def _remember_entity(self, position: tuple, entity_type: str,
                         entity_name: str, tick: int) -> None:
        """Add or update entity in memory."""
        cell = self._pos_to_cell(position)

        if cell not in self.entries:
            self.entries[cell] = []

        # Check if we already know this entity
        for entry in self.entries[cell]:
            if entry.entity_name == entity_name:
                entry.last_seen_tick = tick
                entry.still_exists = True
                return

        # New entity
        self.entries[cell].append(SpatialMemoryEntry(
            position=position,
            entity_type=entity_type,
            entity_name=entity_name,
            last_seen_tick=tick
        ))

    def retrieve(self, query: str | None = None) -> list:
        """Retrieve spatial memories."""
        all_entries = []
        for cell_entries in self.entries.values():
            all_entries.extend(cell_entries)

        if query == "resources":
            return [e for e in all_entries if e.entity_type == "resource" and e.still_exists]
        elif query == "hazards":
            return [e for e in all_entries if e.entity_type == "hazard"]
        elif query == "visited":
            return list(self.visited_cells)
        else:
            return all_entries

    def get_unexplored_cells(self, current_pos: tuple, radius: int = 5) -> list[tuple[int, int]]:
        """Find unexplored cells near current position."""
        current_cell = self._pos_to_cell(current_pos)
        unexplored = []

        for dx in range(-radius, radius + 1):
            for dz in range(-radius, radius + 1):
                cell = (current_cell[0] + dx, current_cell[1] + dz)
                if cell not in self.visited_cells:
                    unexplored.append(cell)

        # Sort by distance to current cell
        unexplored.sort(key=lambda c: abs(c[0] - current_cell[0]) + abs(c[1] - current_cell[1]))
        return unexplored

    def mark_collected(self, resource_name: str) -> None:
        """Mark a resource as collected (no longer exists)."""
        for cell_entries in self.entries.values():
            for entry in cell_entries:
                if entry.entity_name == resource_name:
                    entry.still_exists = False
                    return

    def clear(self) -> None:
        """Clear all spatial memory."""
        self.entries.clear()
        self.visited_cells.clear()
```

## Pattern Memory

Remember successful action sequences:

```python
from collections import defaultdict


@dataclass
class ActionOutcome:
    """Record of an action and its outcome."""
    tool: str
    params: dict
    context_hash: str  # Hash of situation when action was taken
    success: bool
    reward: float  # Could be health gained, resource collected, etc.


class PatternMemory(Memory):
    """Memory for learning action patterns."""

    def __init__(self, max_patterns: int = 100):
        self.max_patterns = max_patterns
        self.patterns: list[ActionOutcome] = []
        self.context_success_rate: dict[str, dict[str, float]] = defaultdict(dict)

    def store_outcome(self, tool: str, params: dict, context: str,
                      success: bool, reward: float = 0.0) -> None:
        """Store an action outcome."""
        outcome = ActionOutcome(
            tool=tool,
            params=params,
            context_hash=context,
            success=success,
            reward=reward
        )
        self.patterns.append(outcome)

        # Update success rate tracking
        if tool not in self.context_success_rate[context]:
            self.context_success_rate[context][tool] = 0.5  # Prior

        # Exponential moving average
        current = self.context_success_rate[context][tool]
        self.context_success_rate[context][tool] = 0.8 * current + 0.2 * (1.0 if success else 0.0)

        # Trim if too large
        if len(self.patterns) > self.max_patterns:
            self.patterns = self.patterns[-self.max_patterns:]

    def get_best_action_for_context(self, context: str, available_tools: list[str]) -> str | None:
        """Get the historically best action for a context."""
        if context not in self.context_success_rate:
            return None

        rates = self.context_success_rate[context]
        valid_rates = {k: v for k, v in rates.items() if k in available_tools}

        if not valid_rates:
            return None

        return max(valid_rates, key=valid_rates.get)

    def store(self, observation: Observation) -> None:
        """Not used directly - use store_outcome instead."""
        pass

    def retrieve(self, query: str | None = None) -> list:
        """Retrieve patterns matching a context."""
        if query:
            return [p for p in self.patterns if p.context_hash == query]
        return self.patterns

    def clear(self) -> None:
        """Clear pattern memory."""
        self.patterns.clear()
        self.context_success_rate.clear()
```

## Semantic Memory

Store and retrieve facts and knowledge:

```python
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Fact:
    """A piece of knowledge."""
    subject: str
    predicate: str
    value: Any
    confidence: float = 1.0
    source: str = "observation"


class SemanticMemory(Memory):
    """Knowledge base for facts about the world."""

    def __init__(self):
        self.facts: dict[str, list[Fact]] = defaultdict(list)

    def learn(self, subject: str, predicate: str, value: Any,
              confidence: float = 1.0, source: str = "observation") -> None:
        """Learn a new fact or update existing knowledge."""
        fact = Fact(subject, predicate, value, confidence, source)

        # Check if we already know this
        for existing in self.facts[subject]:
            if existing.predicate == predicate:
                # Update if new info is more confident
                if confidence >= existing.confidence:
                    existing.value = value
                    existing.confidence = confidence
                    existing.source = source
                return

        self.facts[subject].append(fact)

    def query(self, subject: str, predicate: str | None = None) -> list[Fact]:
        """Query facts about a subject."""
        facts = self.facts.get(subject, [])
        if predicate:
            return [f for f in facts if f.predicate == predicate]
        return facts

    def store(self, observation: Observation) -> None:
        """Extract facts from observation."""
        # Learn about resources
        for resource in observation.nearby_resources:
            self.learn(resource.name, "type", resource.type)
            self.learn(resource.type, "found_at", resource.position, confidence=0.8)

        # Learn about hazards
        for hazard in observation.nearby_hazards:
            self.learn(hazard.name, "damage", hazard.damage)
            self.learn(hazard.type, "is_dangerous", True)

    def retrieve(self, query: str | None = None) -> list:
        """Retrieve all facts or filter by subject."""
        if query:
            return self.facts.get(query, [])
        return [f for facts in self.facts.values() for f in facts]

    def clear(self) -> None:
        """Clear semantic memory."""
        self.facts.clear()
```

## Composite Memory

Combine multiple memory systems:

```python
class CompositeMemory(Memory):
    """Combines multiple memory systems."""

    def __init__(self):
        from agent_runtime.memory import SlidingWindowMemory

        self.episodic = SlidingWindowMemory(capacity=50)  # Recent observations
        self.spatial = SpatialMemory(grid_size=5.0)       # Location knowledge
        self.semantic = SemanticMemory()                   # Facts and rules
        self.patterns = PatternMemory(max_patterns=100)    # Action patterns

    def store(self, observation: Observation) -> None:
        """Store observation in all memory systems."""
        self.episodic.store(observation)
        self.spatial.store(observation)
        self.semantic.store(observation)

    def retrieve(self, query: str | None = None) -> dict:
        """Retrieve from all memory systems."""
        return {
            "recent": self.episodic.retrieve()[-5:],
            "spatial": self.spatial.retrieve(query),
            "facts": self.semantic.retrieve(query),
            "patterns": self.patterns.retrieve(query)
        }

    def get_context_for_llm(self, observation: Observation) -> str:
        """Build rich context from all memories."""
        recent = self.episodic.retrieve()[-3:]
        unexplored = self.spatial.get_unexplored_cells(observation.position, radius=3)
        known_resources = self.spatial.retrieve("resources")
        known_hazards = self.spatial.retrieve("hazards")

        return f"""
## MEMORY CONTEXT

### Recent History
- Observations stored: {len(self.episodic.retrieve())}
- Recent positions: {[o.position for o in recent]}

### Spatial Knowledge
- Explored cells: {len(self.spatial.visited_cells)}
- Unexplored nearby: {len(unexplored)} cells
- Known resources: {[r.entity_name for r in known_resources if r.still_exists]}
- Known hazards: {[h.entity_name for h in known_hazards]}

### Learned Facts
- Resource types seen: {set(f.value for f in self.semantic.query("", "type") if f.subject.endswith("_resource"))}
"""

    def clear(self) -> None:
        """Clear all memory systems."""
        self.episodic.clear()
        self.spatial.clear()
        self.semantic.clear()
        self.patterns.clear()

    def on_action_complete(self, tool: str, params: dict, context: str,
                           success: bool, reward: float = 0.0) -> None:
        """Record action outcome for pattern learning."""
        self.patterns.store_outcome(tool, params, context, success, reward)
```

## Using Composite Memory

```python
from agent_runtime import LLMAgentBehavior, Observation, AgentDecision, ToolSchema


class MemoryRichAgent(LLMAgentBehavior):
    """Agent with sophisticated memory."""

    def __init__(self):
        super().__init__(backend="anthropic", model="claude-3-haiku-20240307")
        self.memory = CompositeMemory()
        self.last_action = None
        self.last_context = None

    def on_episode_start(self) -> None:
        self.memory.clear()
        self.last_action = None

    def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
        # Store observation
        self.memory.store(observation)

        # Build context with memory
        memory_context = self.memory.get_context_for_llm(observation)
        state_context = self._format_state(observation, tools)

        full_context = f"{memory_context}\n\n{state_context}"

        # Check if patterns suggest a good action
        context_hash = self._hash_context(observation)
        pattern_suggestion = self.memory.patterns.get_best_action_for_context(
            context_hash,
            [t.name for t in tools]
        )

        if pattern_suggestion:
            full_context += f"\n\nNote: Pattern memory suggests '{pattern_suggestion}' works well in this situation."

        # Get LLM decision
        response = self.complete(full_context)
        decision = self._parse_response(response, tools)

        # Track for outcome learning
        self.last_action = decision
        self.last_context = context_hash

        return decision

    def on_tool_result(self, tool: str, result: dict) -> None:
        """Learn from action outcome."""
        if self.last_action and self.last_context:
            success = result.get("success", False)
            reward = 1.0 if success else -0.5

            self.memory.on_action_complete(
                tool=tool,
                params=self.last_action.params,
                context=self.last_context,
                success=success,
                reward=reward
            )

            # If we collected something, mark it in spatial memory
            if tool == "collect" and success:
                resource_id = self.last_action.params.get("resource_id")
                if resource_id:
                    self.memory.spatial.mark_collected(resource_id)

    def _hash_context(self, obs: Observation) -> str:
        """Create context hash for pattern matching."""
        return f"r{len(obs.nearby_resources)}_h{len(obs.nearby_hazards)}_hp{obs.health//20}"
```

## Memory for Planning

Use memory to inform multi-step plans:

```python
class PlanningMemory:
    """Memory specialized for planning tasks."""

    def __init__(self):
        self.goals: list[str] = []
        self.completed_goals: set[str] = set()
        self.failed_attempts: dict[str, int] = defaultdict(int)
        self.resource_locations: dict[str, tuple] = {}

    def set_goals(self, goals: list[str]) -> None:
        """Set goals for the current plan."""
        self.goals = goals
        self.completed_goals.clear()

    def mark_goal_complete(self, goal: str) -> None:
        """Mark a goal as completed."""
        self.completed_goals.add(goal)

    def get_next_goal(self) -> str | None:
        """Get the next incomplete goal."""
        for goal in self.goals:
            if goal not in self.completed_goals:
                return goal
        return None

    def record_failure(self, goal: str) -> None:
        """Record a failed attempt at a goal."""
        self.failed_attempts[goal] += 1

    def should_skip_goal(self, goal: str, max_attempts: int = 3) -> bool:
        """Check if we've failed too many times."""
        return self.failed_attempts[goal] >= max_attempts

    def remember_resource_location(self, resource_type: str, position: tuple) -> None:
        """Remember where a resource type can be found."""
        self.resource_locations[resource_type] = position

    def get_resource_location(self, resource_type: str) -> tuple | None:
        """Recall where to find a resource type."""
        return self.resource_locations.get(resource_type)
```

## Next Steps

- [Planning](04_planning.md) - Use memory for multi-step reasoning
- [Multi-Agent](05_multi_agent.md) - Share memory between agents
