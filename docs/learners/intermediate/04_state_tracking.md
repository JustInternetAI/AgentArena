# State Tracking

Beyond memory, your agent needs to track internal state - goals, plans, and situational awareness that persists across ticks and episodes.

## Agent Lifecycle

Your agent goes through these phases:

```
┌─────────────────────────────────────────────────────────────────┐
│                        AGENT LIFECYCLE                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│   __init__()          on_episode_start()        decide()         │
│   ──────────    ─────▶  ────────────────   ────▶ ────────        │
│   Create agent          Reset for new          Called each       │
│   Set up state          episode               tick               │
│                                                  │                │
│                                                  │ (many ticks)   │
│                                                  ▼                │
│                                               decide()           │
│                                                  │                │
│                                                  │                │
│                                                  ▼                │
│                        on_episode_end()      on_tool_result()    │
│                        ────────────────      ────────────────    │
│                        Cleanup, learn        After each tool     │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Lifecycle Methods

```python
class StatefulAgent(AgentBehavior):
    def __init__(self):
        """Called once when agent is created."""
        # Persistent state (survives episodes)
        self.total_episodes = 0
        self.best_score = 0

        # Episode state (reset each episode)
        self.current_goal = None
        self.collected_this_episode = 0

    def on_episode_start(self) -> None:
        """Called at the start of each episode."""
        self.total_episodes += 1
        self.current_goal = "collect_all"
        self.collected_this_episode = 0
        print(f"Starting episode {self.total_episodes}")

    def on_episode_end(self, success: bool, metrics: dict | None = None) -> None:
        """Called when episode ends."""
        score = metrics.get("score", 0) if metrics else 0
        if score > self.best_score:
            self.best_score = score
            print(f"New best score: {score}!")

        print(f"Episode {self.total_episodes}: {'Success' if success else 'Failure'}")

    def on_tool_result(self, tool: str, result: dict) -> None:
        """Called after each tool execution."""
        if tool == "collect" and result.get("success"):
            self.collected_this_episode += 1
            print(f"Collected item! Total this episode: {self.collected_this_episode}")

    def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
        """Called each tick."""
        # Use state in decisions
        if self.collected_this_episode >= 7:
            return AgentDecision.idle(reasoning="Goal complete!")
        # ... rest of logic
```

## State Categories

### 1. Configuration State
Set once, never changes:

```python
class ConfiguredAgent(AgentBehavior):
    def __init__(self, danger_threshold: float = 3.0, aggressive: bool = False):
        self.danger_threshold = danger_threshold
        self.aggressive = aggressive
        # These won't change during execution
```

### 2. Persistent State
Survives across episodes (learning):

```python
class LearningAgent(AgentBehavior):
    def __init__(self):
        # Persistent knowledge
        self.known_hazard_positions = set()  # Remember dangerous areas
        self.successful_strategies = []       # What worked before

    def on_episode_end(self, success: bool, metrics: dict | None = None):
        if success:
            self.successful_strategies.append(self._current_strategy)
```

### 3. Episode State
Reset each episode:

```python
class EpisodeAgent(AgentBehavior):
    def __init__(self):
        self._reset_episode_state()

    def _reset_episode_state(self):
        self.visited = set()
        self.current_plan = []
        self.resources_collected = 0
        self.damage_taken = 0

    def on_episode_start(self):
        self._reset_episode_state()
```

### 4. Tick State
Computed fresh each tick:

```python
def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
    # Tick state - computed from current observation
    closest_hazard = min(observation.nearby_hazards, key=lambda h: h.distance, default=None)
    closest_resource = min(observation.nearby_resources, key=lambda r: r.distance, default=None)
    is_in_danger = closest_hazard and closest_hazard.distance < 3.0

    # Use tick state in decisions
    if is_in_danger:
        return self._escape(closest_hazard)
```

## Goal Tracking

Track what you're trying to accomplish:

```python
from enum import Enum

class Goal(Enum):
    EXPLORE = "explore"
    COLLECT = "collect"
    ESCAPE = "escape"
    IDLE = "idle"

class GoalDrivenAgent(AgentBehavior):
    def __init__(self):
        self.current_goal = Goal.EXPLORE
        self.goal_progress = 0
        self.memory = SlidingWindowMemory(capacity=20)

    def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
        self.memory.store(observation)

        # Update goal based on situation
        self._update_goal(observation)

        # Execute goal-specific behavior
        if self.current_goal == Goal.ESCAPE:
            return self._execute_escape(observation)
        elif self.current_goal == Goal.COLLECT:
            return self._execute_collect(observation)
        elif self.current_goal == Goal.EXPLORE:
            return self._execute_explore(observation)
        else:
            return AgentDecision.idle()

    def _update_goal(self, observation: Observation):
        """Decide what goal to pursue."""
        # Emergency override: escape if in danger
        if self._in_danger(observation):
            if self.current_goal != Goal.ESCAPE:
                print(f"Goal change: {self.current_goal} → ESCAPE")
                self.current_goal = Goal.ESCAPE
            return

        # If we were escaping and now safe, resume previous goal
        if self.current_goal == Goal.ESCAPE and not self._in_danger(observation):
            self.current_goal = Goal.COLLECT if observation.nearby_resources else Goal.EXPLORE
            print(f"Danger passed, goal: {self.current_goal}")
            return

        # Normal goal selection
        if observation.nearby_resources and self.current_goal != Goal.COLLECT:
            self.current_goal = Goal.COLLECT
        elif not observation.nearby_resources and self.current_goal == Goal.COLLECT:
            self.current_goal = Goal.EXPLORE
```

## Plan Tracking

For multi-step tasks, track your plan:

```python
class PlanningAgent(AgentBehavior):
    def __init__(self):
        self.plan: list[str] = []  # List of actions
        self.plan_step = 0

    def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
        # Create plan if needed
        if not self.plan:
            self.plan = self._create_plan(observation)
            self.plan_step = 0
            print(f"New plan: {self.plan}")

        # Check if plan still valid
        if not self._is_plan_valid(observation):
            print("Plan invalidated, replanning...")
            self.plan = self._create_plan(observation)
            self.plan_step = 0

        # Execute current plan step
        if self.plan_step < len(self.plan):
            action = self.plan[self.plan_step]
            self.plan_step += 1
            return self._action_to_decision(action, observation)

        # Plan complete
        self.plan = []
        return AgentDecision.idle(reasoning="Plan complete")

    def _create_plan(self, observation: Observation) -> list[str]:
        """Create a plan based on current state."""
        plan = []
        # Simple planning: visit all resources in order of distance
        resources = sorted(observation.nearby_resources, key=lambda r: r.distance)
        for resource in resources:
            plan.append(f"goto:{resource.name}")
            plan.append(f"collect:{resource.name}")
        return plan

    def _is_plan_valid(self, observation: Observation) -> bool:
        """Check if current plan is still achievable."""
        # Invalid if danger appeared
        if any(h.distance < 2.0 for h in observation.nearby_hazards):
            return False
        return True

    def _action_to_decision(self, action: str, observation: Observation) -> AgentDecision:
        """Convert plan action to AgentDecision."""
        parts = action.split(":")
        if parts[0] == "goto":
            target_name = parts[1]
            target = next((r for r in observation.nearby_resources if r.name == target_name), None)
            if target:
                return AgentDecision(
                    tool="move_to",
                    params={"target_position": list(target.position)},
                    reasoning=f"Plan step: go to {target_name}"
                )
        elif parts[0] == "collect":
            return AgentDecision(
                tool="collect",
                params={"resource_id": parts[1]},
                reasoning=f"Plan step: collect {parts[1]}"
            )
        return AgentDecision.idle()
```

## Debugging State

Add methods to inspect state:

```python
class DebuggableAgent(AgentBehavior):
    def __init__(self):
        self.memory = SlidingWindowMemory(capacity=20)
        self.current_goal = "explore"
        self.visited = set()

    def get_state_summary(self) -> dict:
        """Return current state for debugging."""
        return {
            "goal": self.current_goal,
            "visited_count": len(self.visited),
            "memory_size": len(self.memory.retrieve()),
        }

    def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
        # Log state periodically
        if observation.tick % 10 == 0:
            print(f"State at tick {observation.tick}: {self.get_state_summary()}")

        # Normal decision logic...
```

## Next Steps

- [Crafting Challenge](05_crafting_challenge.md) - Apply these concepts to multi-step planning
- [Advanced: LLM Backends](../advanced/01_llm_backends.md) - Add language model reasoning
