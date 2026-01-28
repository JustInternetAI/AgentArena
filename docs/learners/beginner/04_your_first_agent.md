# Build Your First Agent

Now let's put everything together and build a working agent!

## Step 1: Create Your Agent File

Create a new file at `python/user_agents/my_first_agent.py`:

```python
"""
My First Agent - A beginner foraging agent.
"""

from agent_runtime import SimpleAgentBehavior, SimpleContext


class MyFirstAgent(SimpleAgentBehavior):
    """
    A simple agent that collects resources while avoiding hazards.

    This agent uses a priority-based decision system:
    1. Escape immediate danger
    2. Collect resources in range
    3. Move toward visible resources
    4. Idle when nothing to do
    """

    # Optional: Set a system prompt (used if you later add LLM)
    system_prompt = "You are a foraging agent. Collect resources safely."

    def decide(self, context: SimpleContext) -> str:
        """
        Decide what tool to use this tick.

        Args:
            context: Current observation (position, resources, hazards, etc.)

        Returns:
            Tool name: "move_to", "collect", or "idle"
        """

        # PRIORITY 1: Escape immediate danger
        # If a hazard is within 2 units, move away!
        for hazard in context.nearby_hazards:
            if hazard["distance"] < 2.0:
                print(f"DANGER! {hazard['name']} at distance {hazard['distance']:.1f}")
                return "move_to"  # Framework moves away from hazard

        # PRIORITY 2: Collect resource if in range
        # Collection range is about 2 units
        if context.nearby_resources:
            closest = min(context.nearby_resources, key=lambda r: r["distance"])
            if closest["distance"] < 2.0:
                print(f"Collecting {closest['name']}")
                return "collect"

        # PRIORITY 3: Move toward nearest resource
        if context.nearby_resources:
            closest = min(context.nearby_resources, key=lambda r: r["distance"])
            print(f"Moving toward {closest['name']} at distance {closest['distance']:.1f}")
            return "move_to"

        # PRIORITY 4: Nothing to do
        print("No resources visible, idling...")
        return "idle"
```

## Step 2: Create a Run Script

Create `python/run_my_agent.py`:

```python
"""
Run my custom agent in the foraging scenario.
"""

import logging
from agent_runtime import AgentArena
from user_agents.my_first_agent import MyFirstAgent

# Setup logging so we can see what's happening
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

def main():
    print("=" * 60)
    print("My First Agent - Foraging Demo")
    print("=" * 60)
    print()
    print("Instructions:")
    print("1. This script starts the Python agent server")
    print("2. Open Godot and run scenes/foraging.tscn")
    print("3. Press SPACE to start the simulation")
    print("4. Watch your agent in action!")
    print()
    print("=" * 60)

    # Create the arena (handles communication with Godot)
    arena = AgentArena.connect(host="127.0.0.1", port=5000)

    # Register your agent
    # The agent_id must match what's in the Godot scene
    agent_id = "foraging_agent_001"
    arena.register(agent_id, MyFirstAgent())

    print(f"✓ Registered MyFirstAgent as '{agent_id}'")
    print("✓ Waiting for Godot connection...")
    print()

    # Run the arena (this blocks until you stop it with Ctrl+C)
    arena.run()


if __name__ == "__main__":
    main()
```

## Step 3: Run Your Agent

```bash
cd python
venv\Scripts\activate
python run_my_agent.py
```

Then in Godot:
1. Open `scenes/foraging.tscn`
2. Press F5 to run
3. Press SPACE to start
4. Watch your agent collect resources!

## Understanding What Happens

When the simulation runs:

```
Tick 1:
  → Godot sends observation to Python
  → Your decide() method is called
  → You return "move_to"
  → Godot moves your agent toward nearest resource

Tick 2:
  → Godot sends new observation (agent has moved)
  → Your decide() method is called again
  → You return "move_to" (still heading to resource)
  → Godot continues moving your agent

Tick 10:
  → Agent is now close to resource (distance < 2.0)
  → Your decide() returns "collect"
  → Godot collects the resource, adds to inventory

...and so on
```

## Improving Your Agent

### Add Hazard Awareness

Current problem: We only run when hazards are VERY close.

```python
def decide(self, context: SimpleContext) -> str:
    # Check for nearby hazards (not just immediate danger)
    CAUTION_DISTANCE = 4.0  # Start being careful at 4 units
    DANGER_DISTANCE = 2.0   # Run away at 2 units

    for hazard in context.nearby_hazards:
        if hazard["distance"] < DANGER_DISTANCE:
            print(f"RUNNING from {hazard['name']}!")
            return "move_to"
        elif hazard["distance"] < CAUTION_DISTANCE:
            print(f"Caution: {hazard['name']} nearby at {hazard['distance']:.1f}")
            # Continue but be aware...

    # Rest of decision logic...
```

### Add Resource Prioritization

Prefer closer resources, but also consider resource type:

```python
def decide(self, context: SimpleContext) -> str:
    if context.nearby_resources:
        # Score each resource (lower = better)
        def score_resource(r):
            distance_score = r["distance"]
            # Prefer berries (food) over other resources
            type_bonus = -1.0 if r["type"] == "berry" else 0.0
            return distance_score + type_bonus

        best = min(context.nearby_resources, key=score_resource)
        print(f"Targeting {best['name']} (score: {score_resource(best):.1f})")

        if best["distance"] < 2.0:
            return "collect"
        return "move_to"

    return "idle"
```

### Add Simple Memory

Track what you've collected:

```python
class MemoryAgent(SimpleAgentBehavior):
    def __init__(self):
        super().__init__()
        self.collected_count = 0
        self.last_position = None

    def decide(self, context: SimpleContext) -> str:
        # Track inventory changes
        if len(context.inventory) > self.collected_count:
            self.collected_count = len(context.inventory)
            print(f"*** Collected item! Total: {self.collected_count} ***")

        # Detect if stuck (same position multiple ticks)
        if self.last_position == context.position:
            print("Might be stuck...")
        self.last_position = context.position

        # Rest of logic...
```

## Common Issues

### Agent Doesn't Move

**Possible causes:**
- Python server not running
- Wrong agent_id (must match Godot scene)
- Didn't press SPACE to start simulation

**Debug:** Check Python console for "Using registered behavior" message.

### Agent Walks Into Hazards

**Cause:** Your hazard avoidance isn't triggering.

**Fix:** Check your distance thresholds:
```python
print(f"Hazard distances: {[h['distance'] for h in context.nearby_hazards]}")
```

### Agent Gets Stuck

**Cause:** Decision logic creates a loop (e.g., move toward resource, then away from hazard, repeat).

**Fix:** Add tie-breaking or momentum:
```python
def __init__(self):
    super().__init__()
    self.target_resource = None  # Remember what we're going for
```

## Exercises

1. **Modify danger distance** - What happens if you set `DANGER_DISTANCE = 5.0`?

2. **Add resource type preference** - Make your agent prefer wood over berries.

3. **Add completion detection** - Print a message when all resources are collected.

4. **Track efficiency** - Count how many ticks it takes to collect each resource.

## Next Steps

Congratulations! You've built your first agent!

- Try the [Foraging Challenge](05_foraging_challenge.md) to test your skills
- When ready, move to [Intermediate: Full Observations](../intermediate/01_full_observations.md)
