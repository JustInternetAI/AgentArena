# Intermediate Agent Starter

Agent with memory, multi-step planning, and crafting for more sophisticated strategies.

## What's Different vs Beginner

| Feature | Beginner | Intermediate |
|---------|----------|--------------|
| Memory | None — each tick is fresh | Last 50 observations |
| Planning | React to what's visible | Multi-step plans across ticks |
| Resource finding | Only visible resources | Visible + remembered locations |
| Hazard avoidance | Only visible hazards | Visible + remembered hazard zones |
| Crafting | Only when already at station | Plans: gather materials → go to station → craft |
| Exploration | First frontier target | Avoids revisiting, seeks productive areas |
| Tool results | Ignored | Detects failures and replans |
| Pattern detection | None | Finds resource clusters |

## Files

```
intermediate/
├── agent.py         # Decision logic with memory + planning
├── memory.py        # Sliding window memory with pattern detection (YOUR CODE!)
├── planner.py       # Goal decomposition + multi-step plans (YOUR CODE!)
├── run.py           # Entry point — connects to Agent Arena
├── test_agent.py    # Unit tests (run with pytest)
└── requirements.txt # Just the SDK
```

## Quick Start

```bash
pip install -r requirements.txt
python run.py
```

Then connect from Agent Arena game.

## How It Works

```
Observation ──► Memory ──► Planner ──► Agent ──► Decision
                  │            │          │
                  │   decompose into      │
                  │   sub-goals      execute plan
                  │            │     step-by-step
                  │            ▼          │
                  │     ActionStep[]      │
                  │     [move_to,         │
                  │      collect,         │
                  │      craft_item]      │
                  │            │          │
                  ▼            ▼          ▼
          find_uncollected  plan_collect  Decision(tool, params)
          find_hazard_zones plan_craft
          find_productive   plan_explore
```

### Decision Priority

Each tick, the agent decides in this order:

1. **Handle tool result** — Did the last action succeed? Advance the plan or replan.
2. **Escape danger** — Nearby hazard? Cancel plan and flee.
3. **Continue plan** — Mid-plan? Execute the next step.
4. **Pursue objectives** — No plan? Decompose objective into sub-goals, create a plan.
5. **Opportunistic craft** — At a station with materials? Craft something.
6. **Explore** — Nothing to do? Head toward productive areas or frontiers.

### Multi-Step Plans

Instead of choosing one action per tick, the planner creates a **sequence of steps** and executes them across ticks:

```python
# Example: Crafting a torch
planner.plan_craft("torch", "workbench_001", station_pos,
                   missing_materials=[("wood_001", wood_pos)])
# Creates: [move_to wood, collect wood, move_to workbench, craft torch]
```

If any step fails (tool result reports error), the plan is cancelled and the agent replans.

### Memory-Driven Decisions

The agent doesn't just react to what's visible — it remembers:

```python
# "I saw a berry at (10, 0, 5) on tick 3. Nothing visible now, so go back."
uncollected = memory.find_uncollected_resources(current_tick)

# "Fire was at (5, 0, 5) recently. Stay away."
hazard_zones = memory.find_hazard_zones(current_tick)

# "Resources tend to cluster near (12, 0, 8). Explore there."
productive = memory.find_productive_areas()
```

## Modification Ideas

### 1. Change Hazard Avoidance Radius (Simple)

In `agent.py`, the agent flees when a hazard is within 3 units and avoids
remembered hazards within 4 units. Try adjusting:

```python
# In _check_danger():
if hazard.distance < 5.0:     # Was 3.0 — more cautious
    ...
if distance < 6.0:            # Was 4.0 — wider remembered-hazard buffer
    ...
```

### 2. Add a New Recipe (Intermediate)

Add a recipe to `agent.py` and the agent will automatically plan for it:

```python
RECIPES = {
    "torch": ("workbench", {"wood": 1, "stone": 1}),
    "meal": ("workbench", {"berry": 2}),
    "shelter": ("anvil", {"wood": 3, "stone": 2}),
    "potion": ("workbench", {"berry": 1, "mushroom": 1}),  # NEW
}
```

### 3. Implement Resource Value Weighting (Advanced)

Instead of always picking the closest resource, weight by type value:

```python
# In _plan_resource_collection():
RESOURCE_VALUES = {"gold": 10, "stone": 3, "wood": 2, "berry": 1}

if obs.nearby_resources:
    # Score = value / distance (higher is better)
    best = max(
        obs.nearby_resources,
        key=lambda r: RESOURCE_VALUES.get(r.type, 1) / max(r.distance, 0.1),
    )
```

### 4. Add Exploration Memory Decay (Advanced)

Make the agent forget old productive areas and re-explore:

```python
# In memory.py, modify find_productive_areas():
# Only count resources seen in the last 30 ticks
resource_positions = []
for obs in self._observations:
    if current_tick - obs.tick < 30:  # Recency window
        for resource in obs.nearby_resources:
            resource_positions.append(resource.position)
```

## Debugging Tips

### Inspect Memory State

Add a print in `decide()` to see what the agent remembers:

```python
def decide(self, obs):
    self.memory.store(obs)
    print(self.memory.summarize())  # Shows resources, hazards, productive areas
    ...
```

### Trace Planning Decisions

See what the planner is doing:

```python
sub_goals = self.planner.decompose(obs.objective, obs.current_progress)
print(self.planner.explain_plan(sub_goals))
```

### Run Eval Scenarios

Test specific situations without running the full game:

```bash
# Run all scenarios
python ../../python/evals/eval_agent.py --adapter intermediate

# Test just hazard escape
python ../../python/evals/eval_agent.py --adapter intermediate --scenario hazard_escape

# Interactive mode — type your own observations
python ../../python/evals/eval_agent.py --adapter intermediate --interactive
```

### Run Unit Tests

```bash
python -m pytest test_agent.py -v
```

## When to Graduate

Move to the `claude/` or `langgraph/` starter when you want:

- Natural language reasoning about complex situations
- LLM-driven tool selection instead of if/else logic
- Framework observability (LangSmith, Anthropic Console)
- Few-shot learning from examples
