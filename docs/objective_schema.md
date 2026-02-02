# Objective Schema

This document defines how scenarios communicate objectives to agents. The objective system enables general-purpose agents that can adapt to different goals.

## Overview

Every scenario passes an objective to agents as part of the observation data. Agents use this objective to understand what they should achieve.

```
┌─────────────────┐     Observation (includes objective)     ┌─────────────────┐
│    Scenario     │ ─────────────────────────────────────────▶│      Agent      │
│   (Godot Game)  │                                           │   (Python)      │
│                 │◀───────────────────────────────────────── │                 │
└─────────────────┘              Decision                     └─────────────────┘
```

## Objective Format (v1 - Simple)

We start with a simple format that can evolve as we learn what agents need.

```python
{
    "scenario_name": "foraging",
    "objective": {
        "description": "Collect resources while avoiding hazards and staying healthy.",
        "success_metrics": {
            "resources_collected": {
                "target": 10,
                "weight": 1.0
            },
            "health_remaining": {
                "target": 50,
                "weight": 0.5
            },
            "time_taken": {
                "target": 300,
                "weight": 0.2,
                "lower_is_better": true
            }
        },
        "time_limit": 600
    },
    "current_progress": {
        "resources_collected": 3,
        "health_remaining": 85,
        "time_elapsed": 142
    }
}
```

## Field Definitions

### Top-Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `scenario_name` | string | Identifier for the scenario (e.g., "foraging", "crafting_chain", "team_capture") |
| `objective` | object | The goal definition |
| `current_progress` | object | Real-time progress toward goals (updated each tick) |

### Objective Object

| Field | Type | Description |
|-------|------|-------------|
| `description` | string | Human-readable description of the goal. LLM agents can read this directly. |
| `success_metrics` | object | Dictionary of metrics that determine success/scoring |
| `time_limit` | integer | Maximum ticks before scenario ends (0 = unlimited) |

### Success Metrics

Each metric in `success_metrics` has:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `target` | number | required | Target value to achieve |
| `weight` | float | 1.0 | Importance for final score calculation |
| `lower_is_better` | boolean | false | If true, lower values are better (e.g., time_taken) |
| `required` | boolean | false | If true, must meet target to "pass" the scenario |

### Current Progress

The `current_progress` object mirrors `success_metrics` keys but contains current values:

```python
"current_progress": {
    "resources_collected": 3,    # Currently collected 3/10
    "health_remaining": 85,      # Current health is 85
    "time_elapsed": 142          # 142 ticks have passed
}
```

## Scenario Examples

### Foraging Scenario

```python
{
    "scenario_name": "foraging",
    "objective": {
        "description": "Collect as many resources as possible while staying healthy. Avoid hazards that damage you.",
        "success_metrics": {
            "resources_collected": {"target": 10, "weight": 1.0},
            "health_remaining": {"target": 50, "weight": 0.5},
            "time_taken": {"target": 300, "weight": 0.2, "lower_is_better": true}
        },
        "time_limit": 600
    }
}
```

### Crafting Chain Scenario

```python
{
    "scenario_name": "crafting_chain",
    "objective": {
        "description": "Gather raw materials and craft an iron sword. You'll need to mine ore, smelt it into ingots, and use a crafting station.",
        "success_metrics": {
            "iron_sword_crafted": {"target": 1, "weight": 1.0, "required": true},
            "materials_wasted": {"target": 0, "weight": 0.3, "lower_is_better": true},
            "time_taken": {"target": 500, "weight": 0.2, "lower_is_better": true}
        },
        "time_limit": 1200
    }
}
```

### Team Capture Scenario

```python
{
    "scenario_name": "team_capture",
    "objective": {
        "description": "Work with your team to capture and hold control points. Coordinate with teammates to maximize team score.",
        "success_metrics": {
            "team_score": {"target": 100, "weight": 1.0},
            "points_captured": {"target": 3, "weight": 0.5},
            "team_deaths": {"target": 0, "weight": 0.3, "lower_is_better": true}
        },
        "time_limit": 1800
    }
}
```

## Using Objectives in Agent Code

### Beginner Approach (Check Metrics)

```python
def decide(self, obs: Observation) -> Decision:
    objective = obs.objective
    progress = obs.current_progress

    # Check what we need to do
    for metric_name, metric_def in objective.success_metrics.items():
        current = progress.get(metric_name, 0)
        target = metric_def["target"]

        if metric_name == "resources_collected" and current < target:
            return self.pursue_resources(obs)

        if metric_name == "health_remaining" and current < target:
            return self.seek_safety(obs)

    # All goals met or no clear action
    return Decision.idle()
```

### LLM Approach (Read Description)

```python
def decide(self, obs: Observation) -> Decision:
    # Format objective for LLM
    prompt = f"""
    Scenario: {obs.scenario_name}
    Objective: {obs.objective.description}

    Current Progress:
    {self.format_progress(obs.current_progress, obs.objective.success_metrics)}

    What should I do next?
    """

    response = self.llm.complete(prompt)
    return self.parse_decision(response)
```

### Intermediate Approach (Goal Decomposition)

```python
def decide(self, obs: Observation) -> Decision:
    objective = obs.objective
    progress = obs.current_progress

    # Decompose into sub-goals
    sub_goals = self.planner.decompose(objective, progress)

    # Prioritize sub-goals
    current_goal = self.planner.select_goal(sub_goals, obs)

    # Execute current goal
    return self.execute_goal(current_goal, obs)
```

## Scoring Algorithm

The final score is calculated as:

```python
def calculate_score(progress, metrics):
    total_score = 0
    total_weight = 0

    for name, definition in metrics.items():
        target = definition["target"]
        weight = definition.get("weight", 1.0)
        lower_is_better = definition.get("lower_is_better", False)
        current = progress.get(name, 0)

        # Calculate metric score (0-100)
        if lower_is_better:
            # Lower is better: score = 100 if at or below target
            if current <= target:
                metric_score = 100
            else:
                metric_score = max(0, 100 - (current - target) * 10)
        else:
            # Higher is better: score = percentage of target achieved (capped at 100)
            metric_score = min(100, (current / target) * 100)

        total_score += metric_score * weight
        total_weight += weight

    return total_score / total_weight if total_weight > 0 else 0
```

## Pass/Fail Determination

A scenario is "passed" if:
1. All `required` metrics meet their targets
2. Time limit not exceeded (if set)

A scenario can still have a score even if not "passed" - this allows partial credit.

## Future Extensions (v2+)

The simple v1 format can evolve to support:

### Compound Goals
```python
"success_metrics": {
    "craft_sword": {
        "target": 1,
        "requires": ["gather_iron", "gather_wood"]  # Dependencies
    }
}
```

### Dynamic Objectives
```python
"dynamic_objectives": [
    {"trigger": "time_elapsed > 300", "add_metric": "bonus_collected"}
]
```

### Multi-Agent Objectives
```python
"team_objective": {
    "description": "As a team, capture all points",
    "shared_metrics": {...},
    "individual_metrics": {...}
}
```

We intentionally start simple and add complexity as needed based on real usage.

## Integration with Observations

Objectives are included in every observation sent to agents:

```python
{
    "tick": 142,
    "agent_id": "agent_001",
    "position": [10.5, 0.0, 5.2],
    "health": 85,
    "inventory": {...},
    "nearby_resources": [...],
    "nearby_hazards": [...],

    # Objective data
    "scenario_name": "foraging",
    "objective": {
        "description": "...",
        "success_metrics": {...},
        "time_limit": 600
    },
    "current_progress": {
        "resources_collected": 3,
        "health_remaining": 85,
        "time_elapsed": 142
    }
}
```

## Pydantic Models (SDK)

```python
from pydantic import BaseModel
from typing import Dict, Optional

class MetricDefinition(BaseModel):
    target: float
    weight: float = 1.0
    lower_is_better: bool = False
    required: bool = False

class Objective(BaseModel):
    description: str
    success_metrics: Dict[str, MetricDefinition]
    time_limit: int = 0  # 0 = unlimited

class Observation(BaseModel):
    tick: int
    agent_id: str
    position: list[float]
    # ... other fields ...

    scenario_name: str
    objective: Objective
    current_progress: Dict[str, float]
```

## References

- [Learner Developer Experience](learner_developer_experience.md) - Overall architecture
- [Universal Tools](universal_tools.md) - Tools agents can use
- [IPC Protocol](ipc_protocol.md) - Full message format
