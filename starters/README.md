# Agent Arena Starters

This directory contains **starter templates** for building agents at different skill levels. Each starter is a complete, self-contained implementation that you copy to your own project and modify.

## Philosophy

**You own all the code.**

Unlike frameworks that hide complexity behind base classes, starters give you working implementations that you can read, understand, and modify. There's no "magic" - everything your agent does is in your files.

## Available Starters

| Starter | Description | Best For |
|---------|-------------|----------|
| [beginner/](beginner/) | Simple if/else logic, no memory | Learning the basics |
| [intermediate/](intermediate/) | Memory, planning, state tracking | Building real skills |
| [llm/](llm/) | LLM-powered reasoning | Advanced techniques |

## Quick Start

### 1. Install the SDK

```bash
pip install agent-arena-sdk
```

### 2. Copy a Starter

**Option A: Using CLI (recommended)**
```bash
agent-arena init beginner    # Creates beginner starter in current directory
```

**Option B: Manual copy**
```bash
cp -r starters/beginner/* my-agent/
```

### 3. Run Your Agent

```bash
cd my-agent
python run.py
```

### 4. Launch Game and Connect

Open Agent Arena game, connect to `localhost:5000`, run a scenario.

---

## Beginner Starter

**Location:** `starters/beginner/`

**Contents:**
```
beginner/
├── agent.py              # Your agent logic (modify this!)
├── run.py                # Entry point
├── requirements.txt      # Dependencies
└── README.md             # Instructions
```

**What it does:**
- Simple priority-based decision making
- Reacts to immediate observations
- No memory between ticks
- No LLM integration

**Sample agent.py:**
```python
from agent_arena_sdk import Observation, Decision

class Agent:
    def decide(self, obs: Observation) -> Decision:
        # Priority 1: Escape danger
        for hazard in obs.nearby_hazards:
            if hazard.distance < 3.0:
                return self.escape_hazard(hazard, obs)

        # Priority 2: Pursue objectives
        if "resources_collected" in obs.objective.success_metrics:
            return self.pursue_resources(obs)

        return Decision.idle()
```

**Learning goals:**
- Understand the observation → decision → action loop
- Learn to use tools (move_to, collect, idle)
- React to world state
- Read objectives and progress

**When to graduate:** When you want to remember past observations or plan ahead.

---

## Intermediate Starter

**Location:** `starters/intermediate/`

**Contents:**
```
intermediate/
├── agent.py              # Decision logic with memory
├── memory.py             # Sliding window memory (you can see how it works!)
├── planner.py            # Goal decomposition
├── run.py
├── requirements.txt
└── README.md
```

**What it does:**
- Maintains memory of past observations
- Decomposes objectives into sub-goals
- Tracks progress over time
- Explicit planning and state management

**Sample memory.py:**
```python
class SlidingWindowMemory:
    """
    Stores recent observations in a fixed-size window.
    YOU can modify this! Try different strategies.
    """
    def __init__(self, capacity=50):
        self.capacity = capacity
        self.observations = []

    def store(self, observation):
        self.observations.append(observation)
        if len(self.observations) > self.capacity:
            self.observations.pop(0)

    def get_recent(self, n=10):
        return self.observations[-n:]

    def find_resources_seen(self):
        """Find all unique resources we've ever seen."""
        seen = {}
        for obs in self.observations:
            for resource in obs.nearby_resources:
                seen[resource.name] = resource
        return list(seen.values())
```

**Learning goals:**
- Implement and modify memory systems
- Plan multi-step actions
- Track state across ticks
- Debug with memory inspection

**When to graduate:** When you want to use LLMs for reasoning.

---

## LLM Starter

**Location:** `starters/llm/`

**Contents:**
```
llm/
├── agent.py              # LLM-powered decision making
├── memory.py             # Semantic memory with embeddings
├── llm_client.py         # LLM API wrapper (you can see it!)
├── prompts/
│   ├── system.txt        # System prompt
│   └── decision.txt      # Decision prompt template
├── run.py
├── requirements.txt      # Includes anthropic/openai
└── README.md
```

**What it does:**
- Uses LLM to interpret objectives
- Generates reasoning before acting
- Semantic memory with embeddings
- Prompt engineering techniques

**Sample llm_client.py:**
```python
import anthropic

class LLMClient:
    """
    Wrapper for LLM API calls.
    YOU can modify this! Try different models, prompts, etc.
    """
    def __init__(self, model="claude-3-haiku-20240307"):
        self.client = anthropic.Anthropic()
        self.model = model

    def complete(self, system_prompt, user_prompt, tools=None):
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            tools=tools
        )
        return response

    def complete_with_tools(self, system_prompt, user_prompt, tools):
        """Use function calling to select a tool."""
        response = self.complete(system_prompt, user_prompt, tools)
        # Parse tool use from response
        for block in response.content:
            if block.type == "tool_use":
                return {"tool": block.name, "params": block.input}
        return None
```

**Sample system prompt:**
```
You are an AI agent in a simulation. You receive observations about your
environment and must decide what action to take.

Your current objective: {objective_description}

Available tools:
- move_to: Navigate to a position
- collect: Pick up a nearby resource
- idle: Do nothing

Think step-by-step about what action will best achieve your objective.
```

**Learning goals:**
- Prompt engineering for agents
- LLM tool use / function calling
- Semantic memory and retrieval
- Balance reasoning vs. speed

**Requirements:**
- API key for Claude, GPT-4, or Ollama
- Set `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` in environment

---

## Customizing Starters

### Modifying Memory

The intermediate and LLM starters include `memory.py`. Try these modifications:

```python
# Add location-based memory
class SpatialMemory:
    def __init__(self, grid_size=10):
        self.grid = {}  # (x, z) -> list of observations

    def store(self, obs):
        key = (int(obs.position[0] / 10), int(obs.position[2] / 10))
        if key not in self.grid:
            self.grid[key] = []
        self.grid[key].append(obs)

    def get_nearby(self, position, radius=1):
        # Return observations from nearby grid cells
        ...
```

### Adding Planning

The intermediate starter includes a basic `planner.py`. Extend it:

```python
class Planner:
    def decompose(self, objective, progress):
        """Break objective into sub-goals."""
        sub_goals = []

        for metric, definition in objective.success_metrics.items():
            current = progress.get(metric, 0)
            target = definition.target

            if current < target:
                sub_goals.append({
                    "metric": metric,
                    "current": current,
                    "target": target,
                    "priority": definition.weight
                })

        # Sort by priority
        sub_goals.sort(key=lambda g: g["priority"], reverse=True)
        return sub_goals
```

### Custom LLM Prompts

The LLM starter stores prompts in `prompts/`. Experiment with:

- Different system prompts
- Chain-of-thought reasoning
- Few-shot examples
- Reflection prompts

---

## Moving Between Starters

### Beginner → Intermediate

1. Copy your decision logic to new `agent.py`
2. Add memory usage:
```python
from memory import SlidingWindowMemory

class Agent:
    def __init__(self):
        self.memory = SlidingWindowMemory(capacity=100)

    def decide(self, obs):
        self.memory.store(obs)
        # Now you can use self.memory.get_recent() etc.
```

### Intermediate → LLM

1. Keep your memory system
2. Add LLM client:
```python
from llm_client import LLMClient

class Agent:
    def __init__(self):
        self.memory = SlidingWindowMemory()
        self.llm = LLMClient()

    def decide(self, obs):
        self.memory.store(obs)

        # Use LLM for complex decisions
        if self.needs_reasoning(obs):
            return self.llm_decide(obs)
        else:
            return self.rule_based_decide(obs)
```

---

## Scenario-Specific Tips

While agents are general-purpose, some strategies work better in certain scenarios:

### Foraging
- Prioritize closer resources
- Balance collection vs. hazard avoidance
- Track resources you've seen but couldn't reach

### Crafting Chain
- Plan backwards from goal item
- Track material dependencies
- Remember station locations

### Team Capture
- Communicate intentions
- Coordinate point capture
- Respond to teammate messages

See `examples/` directory for scenario-specific example code.

---

## Debugging Your Agent

### Enable Debug Logging
```bash
python run.py --debug
```

### Inspect Memory
```bash
agent-arena debug memory
```

### View Decision History
```bash
agent-arena debug trace
```

### In-Game Tools
- Press `D` for debug overlay
- Press `T` for decision trace
- Press `L` for LLM inspector (LLM starter only)

---

## Contributing

Found a better way to implement something? Improvements to starters are welcome!

1. Fork the repo
2. Modify the starter
3. Test with all scenarios
4. Submit PR

Keep starters simple and educational - they're meant for learning, not production.

---

## References

- [Learner Developer Experience](../docs/learner_developer_experience.md)
- [Objective Schema](../docs/objective_schema.md)
- [Universal Tools](../docs/universal_tools.md)
- [Dev Tools](../docs/dev_tools.md)
