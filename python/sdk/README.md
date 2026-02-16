# Agent Arena SDK

Minimal SDK for building AI agents in Agent Arena simulations.

## Philosophy

This SDK is **intentionally minimal**. It provides only:
- Communication layer (IPC between game and Python)
- Data schemas (Observation, Decision, Objective)
- Connection manager (AgentArena)

**What's NOT included:**
- Behavior base classes
- Memory systems
- LLM clients
- Planning utilities

These live in **starter templates** that you copy and own. This gives you full visibility and control over your agent code.

## Installation

```bash
pip install agent-arena-sdk
```

For development:
```bash
cd python/sdk
pip install -e .
```

## Quick Start

```python
from agent_arena_sdk import AgentArena, Observation, Decision

def decide(obs: Observation) -> Decision:
    """Your agent logic goes here."""

    # Check for nearby resources
    if obs.nearby_resources:
        resource = obs.nearby_resources[0]
        return Decision(
            tool="move_to",
            params={"target_position": resource.position},
            reasoning="Moving to collect resource"
        )

    # Default: do nothing
    return Decision.idle("No resources nearby")

# Connect to game and run
arena = AgentArena(host="127.0.0.1", port=5000)
arena.run(decide)  # Blocks until stopped
```

## Core Components

### AgentArena

Connection manager that handles IPC with the game.

```python
arena = AgentArena(host="127.0.0.1", port=5000)
arena.run(decide_callback)  # Blocking
# or
await arena.run_async(decide_callback)  # Async
```

### Observation

What your agent receives each tick:

```python
@dataclass
class Observation:
    agent_id: str
    tick: int
    position: tuple[float, float, float]
    rotation: tuple[float, float, float] | None
    velocity: tuple[float, float, float] | None
    visible_entities: list[EntityInfo]
    nearby_resources: list[ResourceInfo]
    nearby_hazards: list[HazardInfo]
    inventory: list[ItemInfo]
    health: float
    energy: float
    exploration: ExplorationInfo | None
    # Objective system
    scenario_name: str
    objective: Objective | None
    current_progress: dict[str, float]
    custom: dict
```

### Decision

What your agent returns each tick:

```python
@dataclass
class Decision:
    tool: str
    params: dict
    reasoning: str | None

# Examples
Decision(tool="move_to", params={"target_position": [1, 0, 2]})
Decision(tool="collect", params={"target_name": "berry_001"})
Decision.idle("Waiting for resources")
```

### Objective

Scenario goals passed to your agent:

```python
@dataclass
class Objective:
    description: str
    success_metrics: dict[str, MetricDefinition]
    time_limit: int

# Access in decide()
def decide(obs: Observation) -> Decision:
    if obs.objective:
        print(f"Goal: {obs.objective.description}")
        for metric, definition in obs.objective.success_metrics.items():
            current = obs.current_progress.get(metric, 0)
            target = definition.target
            print(f"{metric}: {current}/{target}")
```

## Universal Tools

Available in all scenarios:

| Tool | Description | Parameters |
|------|-------------|------------|
| `move_to` | Navigate to position | `target_position: [x, y, z]` |
| `collect` | Pick up resource | `target_name: str` |
| `craft` | Craft item | `item_name: str`, `station_name: str` |
| `query_world` | Get surroundings | `radius: float` |
| `query_inventory` | Check inventory | - |
| `send_message` | Team communication | `message: str`, `target_agent: str` |
| `idle` | Do nothing | - |

## Starter Templates

For complete examples, see the starters in the main repository:

- **beginner/** - Simple if/else logic
- **intermediate/** - Memory + planning
- **llm/** - LLM-powered reasoning

Copy a starter, modify it, and make it your own!

## Development

Run tests:
```bash
pytest
```

Type checking:
```bash
mypy agent_arena_sdk
```

Formatting:
```bash
black agent_arena_sdk
ruff check agent_arena_sdk
```

## Links

- [Main Repository](https://github.com/JustInternetAI/AgentArena)
- [Documentation](https://github.com/JustInternetAI/AgentArena/tree/main/docs)
- [Starter Templates](https://github.com/JustInternetAI/AgentArena/tree/main/starters)

## License

MIT
