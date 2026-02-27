# Beginner Agent Starter

A simple priority-based agent for learning Agent Arena basics.

## What This Agent Does

This agent makes decisions based on immediate observations using a priority system:

1. **Escape Danger** - Move away from nearby hazards
2. **Pursue Objectives** - Work toward scenario goals (collect resources, maintain health)
3. **Explore** - Look for new areas when nothing urgent to do

**No memory, no planning, no LLM** - just simple if/else logic you can easily understand and modify.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs only the Agent Arena SDK - no other dependencies needed!

### 2. Run the Agent

```bash
python run.py
```

You should see:
```
Starting Beginner Agent...
============================================================
Waiting for connection from Agent Arena game...
Connect to: localhost:5000
============================================================
```

### 3. Launch Game and Connect

1. Open Agent Arena game
2. Go to Connection settings
3. Connect to `localhost:5000`
4. Run any scenario (foraging recommended for beginners)

### 4. Watch Your Agent!

The agent will:
- Avoid hazards automatically
- Collect resources when objectives require it
- Explore the world when idle

## Files in This Starter

```
beginner/
├── agent.py              # YOUR AGENT LOGIC (modify this!)
├── run.py                # Entry point (usually don't need to change)
├── requirements.txt      # Dependencies
└── README.md             # This file
```

## How It Works

### The Main Loop

```python
from agent_arena_sdk import AgentArena, Observation, Decision
from agent import Agent

agent = Agent()
arena = AgentArena(host="127.0.0.1", port=5000)
arena.run(agent.decide)  # Calls agent.decide() every tick
```

### The decide() Method

```python
def decide(self, obs: Observation) -> Decision:
    # Priority 1: Escape danger
    if danger_nearby:
        return Decision(tool="move_to", params={...})

    # Priority 2: Pursue objectives
    if resources_needed:
        return Decision(tool="collect", params={...})

    # Priority 3: Explore
    return Decision.idle()
```

## What You Can Modify

### Easy Modifications

1. **Change danger threshold**
   ```python
   if hazard.distance < 3.0:  # Change this number!
   ```

2. **Prioritize different resources**
   ```python
   # Prefer berries over other resources
   berries = [r for r in obs.nearby_resources if r.type == "berry"]
   if berries:
       closest = min(berries, key=lambda r: r.distance)
   ```

3. **Add new priorities**
   ```python
   def decide(self, obs: Observation) -> Decision:
       # Your new priority here!
       if obs.health < 30.0:
           return self.find_health_pack(obs)

       # Existing priorities...
   ```

### Challenge Modifications

1. **Resource scoring** - Rate resources by value/distance
2. **Hazard prediction** - Estimate where hazards will be next tick
3. **Tool switching** - Use different tools based on situation

## Available Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `move_to` | Navigate to position | `target_position: [x, y, z]` |
| `collect` | Pick up resource | `target_name: str` |
| `idle` | Do nothing | - |

See `docs/universal_tools.md` for complete tool reference.

## Understanding Observations

Every tick, your agent receives an `Observation` with:

```python
obs.agent_id          # Your agent's ID
obs.tick              # Current tick number
obs.position          # Your position [x, y, z]
obs.health            # Health (0-100)
obs.energy            # Energy (0-100)
obs.nearby_resources  # List of ResourceInfo
obs.nearby_hazards    # List of HazardInfo
obs.inventory         # List of ItemInfo

# Objective system (NEW!)
obs.scenario_name     # "foraging", "crafting", etc.
obs.objective         # Scenario goals
obs.current_progress  # Your progress toward goals
```

## Learning Path

### Master These Concepts First

1. ✅ **Observation → Decision** - How the game loop works
2. ✅ **Priority systems** - Handle most urgent situations first
3. ✅ **Tools** - Move, collect, idle
4. ✅ **Reading objectives** - Understand what the scenario wants

### Then Try

1. **Distance calculations** - Find nearest/farthest entities
2. **Conditional logic** - If health < X, do Y
3. **Resource filtering** - Find specific types of resources

### Ready to Graduate?

When you want to:
- **Remember past observations** → Try `intermediate/` starter
- **Plan ahead** → Try `intermediate/` starter
- **Use LLMs for reasoning** → Try `llm/` starter

## Debugging Tips

### Enable Debug Logging

```bash
python run.py --log-level DEBUG
```

### Print Observations

Add this to `agent.py`:
```python
def decide(self, obs: Observation) -> Decision:
    print(f"Tick {obs.tick}: Health={obs.health}, Resources={len(obs.nearby_resources)}")
    # ... rest of code
```

### Check Reasoning

Every `Decision` can include reasoning:
```python
Decision(tool="move_to", params={...}, reasoning="Going to collect berry")
```

This appears in the game's debug overlay (press `D` in-game).

## Common Issues

### Agent doesn't connect
- Check that `run.py` is running
- Verify port 5000 is not in use
- Make sure game is set to `localhost:5000`

### Agent stands still
- Check that `decide()` is returning a `Decision`
- Verify observation has data (`len(obs.nearby_resources)`)
- Use `Decision.idle()` instead of returning `None`

### Import errors
- Run `pip install -r requirements.txt`
- Check you're in the right virtual environment

## Next Steps

1. **Modify `agent.py`** - Change priorities, add features
2. **Test in different scenarios** - Foraging, crafting, team capture
3. **Compete** - See how your agent scores
4. **Graduate** - Move to `intermediate/` when ready

## Resources

- [Main Documentation](../../docs/)
- [IPC Protocol](../../docs/ipc_protocol.md)
- [Universal Tools](../../docs/universal_tools.md)
- [Objective System](../../docs/objective_schema.md)

---

**Remember:** You own this code! Don't be afraid to break things and experiment. That's how you learn.
