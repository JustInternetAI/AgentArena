# What is an Agent?

## The Core Concept

An **agent** is a program that can:
1. **Perceive** - Receive information about its environment
2. **Reason** - Decide what to do based on that information
3. **Act** - Execute actions that affect the environment

This creates a continuous loop:

```
     ┌──────────────────────────────────────┐
     │                                      │
     ▼                                      │
┌─────────┐     ┌─────────┐     ┌─────────┐│
│ PERCEIVE│────▶│  REASON │────▶│   ACT   ││
└─────────┘     └─────────┘     └─────────┘│
     │                                      │
     │         Environment changes          │
     └──────────────────────────────────────┘
```

## A Simple Example

Imagine a robot vacuum cleaner:

| Step | What Happens |
|------|--------------|
| **Perceive** | Sensors detect dirt, walls, furniture |
| **Reason** | "There's dirt to my left, no obstacles" |
| **Act** | Move left and turn on suction |

The vacuum repeats this loop continuously until the floor is clean.

## Agents in Agent Arena

In Agent Arena, your agent lives in a simulated world. Each "tick" (moment in time):

1. **The world sends an observation** - What your agent can see
2. **Your code decides what to do** - Which tool to use
3. **The world executes the action** - Your agent moves, collects, etc.

```python
# Your agent receives this observation:
{
    "position": [5.0, 0.0, 3.0],      # Where you are
    "nearby_resources": [              # What you can collect
        {"name": "Apple", "distance": 2.5},
        {"name": "Wood", "distance": 4.1}
    ],
    "nearby_hazards": [                # What can hurt you
        {"name": "Pit", "distance": 6.0}
    ]
}

# Your agent decides:
"move_to"  # Go toward the nearest resource

# The world moves your agent toward the apple
```

## What Makes a Good Agent?

Good agents:
- **Use all available information** - Don't ignore hazards!
- **Have clear goals** - Know what "success" means
- **Learn from mistakes** - Remember what didn't work
- **Plan ahead** - Think beyond the current moment

Bad agents:
- Only look at one piece of information
- React randomly without strategy
- Repeat the same mistakes
- Get stuck in loops

## Your Role as the Programmer

You don't need to:
- Understand how the simulation works (Godot/C++)
- Know how movement is calculated (pathfinding)
- Handle graphics or physics

You DO need to:
- Understand what your agent observes
- Write the decision-making logic
- Choose which tools to use and when

## The Simplest Possible Agent

```python
from agent_runtime import SimpleAgentBehavior, SimpleContext

class DoNothingAgent(SimpleAgentBehavior):
    """An agent that does absolutely nothing."""

    def decide(self, context: SimpleContext) -> str:
        return "idle"  # Just sit there
```

This agent is valid! It perceives (receives context), reasons (returns "idle"), and acts (does nothing). It's not useful, but it's a complete agent.

## A Slightly Better Agent

```python
class GreedyCollector(SimpleAgentBehavior):
    """An agent that always moves toward resources."""

    def decide(self, context: SimpleContext) -> str:
        if context.nearby_resources:
            return "move_to"  # Go get it!
        return "idle"  # Nothing to collect
```

This agent will move toward resources when it sees them. But it ignores hazards - it might walk right into a pit!

## Next Steps

Now that you understand what an agent is:
- [Learn about observations](02_observations.md) - What your agent can perceive
- [Learn about tools](03_tools.md) - What your agent can do
- [Build your first agent](04_your_first_agent.md) - Hands-on coding!
