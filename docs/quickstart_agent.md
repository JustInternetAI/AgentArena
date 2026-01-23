# Quickstart: Creating Your First Agent

This guide will help you create and run your first agent in Agent Arena.

## Prerequisites

- Python 3.11+ installed
- Agent Arena repository cloned
- Python virtual environment set up (see main README)

## Step 1: Test the Example Agents

Before creating your own agent, let's verify everything works by testing the provided example agents:

```bash
cd python
python test_simple_agent.py
```

You should see output like:
```
🧪 Testing Example Agents

====================================...
Testing SimpleForager (Full AgentBehavior)
====================================...

Test 1: Resource nearby
  Decision: move_to
  ...
  ✓ PASSED

🎉 ALL TESTS PASSED! 🎉
```

## Step 2: Understanding Agent Types

Agent Arena provides two interfaces for building agents:

### SimpleAgentBehavior (Beginner-Friendly)

**Best for:** Learning the basics, quick prototypes, rule-based agents

**You only implement:** A `decide()` method that returns a tool name

**Framework handles:** Memory, parameter inference, context simplification

**Example:**
```python
from agent_runtime import SimpleAgentBehavior

class MyFirstAgent(SimpleAgentBehavior):
    system_prompt = "You are a foraging agent."
    memory_capacity = 5

    def decide(self, context):
        # Just return a tool name!
        if context.nearby_resources:
            return "move_to"  # Framework infers where to go
        return "idle"
```

### AgentBehavior (Full Control)

**Best for:** Complex agents, LLM integration, custom memory, advanced logic

**You implement:** Full `decide()` method with observations and tools

**You control:** Memory systems, parameter calculation, reasoning

**Example:**
```python
from agent_runtime import AgentBehavior, AgentDecision, SlidingWindowMemory

class MyAdvancedAgent(AgentBehavior):
    def __init__(self):
        self.memory = SlidingWindowMemory(capacity=10)

    def decide(self, observation, tools):
        self.memory.store(observation)

        # Full control over decision-making
        if observation.nearby_resources:
            nearest = min(observation.nearby_resources, key=lambda r: r.distance)
            return AgentDecision(
                tool="move_to",
                params={"target_position": nearest.position, "speed": 1.5},
                reasoning=f"Moving to {nearest.name}"
            )

        return AgentDecision.idle()
```

## Step 3: Choose Your Starting Point

### Option A: Start with SimpleAgentBehavior

1. Look at the example: `python/user_agents/examples/simple_forager_simple.py`
2. Copy it as a template:
```bash
cd python/user_agents
cp examples/simple_forager_simple.py my_first_agent.py
```

3. Modify the `decide()` method:
```python
from agent_runtime import SimpleAgentBehavior

class MyFirstAgent(SimpleAgentBehavior):
    system_prompt = "You are a helpful foraging agent."
    memory_capacity = 5

    def decide(self, context):
        # Your custom logic here!
        if context.nearby_hazards:
            return "move_to"  # Escape!

        if context.nearby_resources:
            if min(r["distance"] for r in context.nearby_resources) < 1.0:
                return "pickup"
            return "move_to"

        return "idle"
```

### Option B: Start with Full AgentBehavior

1. Look at the example: `python/user_agents/examples/simple_forager.py`
2. Copy it as a template:
```bash
cd python/user_agents
cp examples/simple_forager.py my_advanced_agent.py
```

3. Customize the behavior as needed

## Step 4: Test Your Agent

Test your agent without Godot:

```python
# python/test_my_agent.py
from user_agents.my_first_agent import MyFirstAgent
from agent_runtime.schemas import Observation, ResourceInfo, ToolSchema

agent = MyFirstAgent()
tools = [ToolSchema(name="move_to", description="Move", parameters={})]

obs = Observation(
    agent_id="test",
    tick=1,
    position=(0.0, 0.0, 0.0),
    nearby_resources=[
        ResourceInfo(name="apple", type="food", position=(5.0, 0.0, 0.0), distance=5.0)
    ]
)

# For SimpleAgentBehavior:
decision = agent._internal_decide(obs, tools)

# For AgentBehavior:
# decision = agent.decide(obs, tools)

print(f"Tool: {decision.tool}")
print(f"Params: {decision.params}")
```

## Step 5: Run Your Agent with Godot (Optional)

If you have a Godot simulation running:

1. Edit `python/run_agent.py`:
```python
# Uncomment and modify:
from user_agents.my_first_agent import MyFirstAgent

# ...in main():
arena.register('agent_001', MyFirstAgent())
```

2. Start the Godot simulation

3. Run your agent:
```bash
cd python
python run_agent.py
```

## Available Tools

Your agent can use these tools by returning them in decisions:

- `move_to` - Move to a position
  - Params: `target_position` (tuple), `speed` (float)
- `pickup` - Pick up an item
  - Params: `item_id` (string)
- `drop` - Drop an item
  - Params: `item_name` (string)
- `use` - Use an item
  - Params: `item_name` (string)
- `idle` - Do nothing
  - Params: none

## What You Get in Observations

### For SimpleAgentBehavior (SimpleContext):
- `position` - Your position (x, y, z)
- `nearby_resources` - List of dicts with name, type, distance, position
- `nearby_hazards` - List of dicts with name, type, distance, damage
- `inventory` - List of item names
- `tick` - Current simulation tick
- `goal` - Optional goal string

### For AgentBehavior (Observation):
- All of the above plus:
- `visible_entities` - List of EntityInfo objects
- `rotation` - Your rotation
- `velocity` - Your velocity
- `health` - Current health (0-100)
- `energy` - Current energy (0-100)
- `custom` - Custom data dict

## Next Steps

1. **Add Memory**: Use `SlidingWindowMemory` or `SummarizingMemory`
```python
from agent_runtime import SlidingWindowMemory

self.memory = SlidingWindowMemory(capacity=10)
self.memory.store(observation)
context = self.memory.summarize()  # Get text summary
```

2. **Add LLM Integration**: Connect an LLM backend
```python
# Coming soon: LLM backend integration examples
```

3. **Study Example Agents**:
   - `SimpleForager` - Basic resource collection
   - `SimpleForagerSimple` - Minimal beginner version

4. **Read Architecture Docs**: See `docs/architecture.md` for details

## Troubleshooting

**Import errors?**
- Make sure you're in the `python/` directory
- Check your virtual environment is activated

**Agent not making decisions?**
- Add print statements in your `decide()` method
- Use the standalone test script to debug without Godot

**Parameters not working?**
- For SimpleAgentBehavior, the framework infers params automatically
- For AgentBehavior, you must provide all params in AgentDecision

## Example Agent Template

Here's a complete minimal agent to get started:

```python
# python/user_agents/my_agent.py
from agent_runtime import AgentBehavior, AgentDecision

class MyAgent(AgentBehavior):
    """My custom agent."""

    def decide(self, observation, tools):
        # Your logic here
        if observation.nearby_resources:
            nearest = min(observation.nearby_resources, key=lambda r: r.distance)
            return AgentDecision(
                tool="move_to",
                params={"target_position": nearest.position, "speed": 1.0},
                reasoning=f"Going to {nearest.name}"
            )

        return AgentDecision.idle(reasoning="Nothing to do")
```

Happy agent building! 🤖
