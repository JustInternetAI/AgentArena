# Intermediate Agent Starter

Agent with memory and planning for more sophisticated strategies.

## What's New vs Beginner

| Feature | Beginner | Intermediate |
|---------|----------|--------------|
| Memory | None | Last 50 observations |
| Planning | React only | Goal decomposition |
| Exploration | Random | Avoids revisiting |
| Decision making | Immediate | Considers history |

## Files

```
intermediate/
├── agent.py         # Agent with memory & planning
├── memory.py        # Sliding window memory (YOUR CODE!)
├── planner.py       # Goal decomposition (YOUR CODE!)
├── run.py           # Entry point
└── requirements.txt # Just the SDK
```

## Quick Start

```bash
pip install -r requirements.txt
python run.py
```

Then connect from Agent Arena game.

## How Memory Works

```python
from memory import SlidingWindowMemory

memory = SlidingWindowMemory(capacity=50)

# Store each observation
memory.store(obs)

# Retrieve recent history
last_10 = memory.get_recent(10)

# Find things you've seen
resources = memory.find_resources_seen()
hazards = memory.find_hazards_seen()
```

## How Planning Works

```python
from planner import Planner

planner = Planner()

# Break objective into sub-goals
sub_goals = planner.decompose(obs.objective, obs.current_progress)

# Pick highest priority
current_goal = planner.select_goal(sub_goals)

# Work on it
decision = execute_sub_goal(current_goal, obs)
```

## Modification Ideas

**Memory enhancements:**
- Semantic search
- Importance weighting
- Compression/summarization

**Planning improvements:**
- Multi-step plans
- Dependency tracking
- Dynamic re-planning

**State tracking:**
- World model
- Resource timers
- Hazard predictions

## When to Graduate

Move to `llm/` starter when you want:
- Natural language reasoning
- Complex decision making
- Few-shot learning from examples

## Resources

- [Memory Systems](../../docs/memory_systems.md)
- [Planning Strategies](../../docs/planning.md)
