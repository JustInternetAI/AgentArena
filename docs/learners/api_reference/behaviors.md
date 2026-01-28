# Behaviors API

Base classes for implementing agent behaviors.

## SimpleAgentBehavior (Beginner)

The simplest way to create an agent:

```python
from agent_runtime import SimpleAgentBehavior, SimpleContext


class MySimpleAgent(SimpleAgentBehavior):
    """A beginner-level agent."""

    system_prompt = "A helpful foraging agent."

    def decide(self, context: SimpleContext) -> str:
        """
        Decide what action to take.

        Args:
            context: Simplified observation data

        Returns:
            Tool name as a string: "move_to", "collect", or "idle"
        """
        if context.nearby_resources:
            return "collect"
        return "move_to"
```

### Class Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `system_prompt` | str | Description of the agent (for documentation) |

### Methods to Override

#### `decide(context: SimpleContext) -> str`

**Required.** Called every tick to get the agent's action.

- **Parameters**: `context` - Simplified observation data
- **Returns**: Tool name (`"move_to"`, `"collect"`, or `"idle"`)

---

## AgentBehavior (Intermediate)

Full control over decisions with typed data:

```python
from agent_runtime import AgentBehavior, Observation, AgentDecision, ToolSchema


class MyAgent(AgentBehavior):
    """An intermediate-level agent."""

    def __init__(self):
        """Initialize agent state."""
        self.visited_positions = set()

    def on_episode_start(self) -> None:
        """Called when a new episode begins."""
        self.visited_positions.clear()

    def on_episode_end(self, success: bool, metrics: dict | None = None) -> None:
        """Called when an episode ends."""
        print(f"Episode ended: {'success' if success else 'failure'}")
        if metrics:
            print(f"Score: {metrics.get('score', 0)}")

    def on_tool_result(self, tool: str, result: dict) -> None:
        """Called after each tool execution."""
        if tool == "collect" and result.get("success"):
            print(f"Successfully collected!")

    def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
        """
        Decide what action to take.

        Args:
            observation: Full observation data with typed classes
            tools: List of available tools with parameter schemas

        Returns:
            AgentDecision with tool, params, and reasoning
        """
        # Track position
        pos_key = (int(observation.position[0]), int(observation.position[2]))
        self.visited_positions.add(pos_key)

        # Make decision
        if observation.nearby_resources:
            target = observation.nearby_resources[0]
            if target.distance < 2.0:
                return AgentDecision(
                    tool="collect",
                    params={"resource_id": target.name},
                    reasoning=f"Collecting {target.name}"
                )
            return AgentDecision(
                tool="move_to",
                params={"target_position": list(target.position)},
                reasoning=f"Moving to {target.name}"
            )

        return AgentDecision.idle(reasoning="No resources visible")
```

### Lifecycle Methods

```
┌──────────────────────────────────────────────────────────────┐
│                     AGENT LIFECYCLE                           │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  __init__()                                                   │
│      │                                                        │
│      ▼                                                        │
│  on_episode_start()  ◄──────────────────────────┐            │
│      │                                           │            │
│      ▼                                           │            │
│  ┌──────────────────────────────────────────┐   │            │
│  │              TICK LOOP                    │   │            │
│  │                                           │   │            │
│  │  decide() ───► tool execution             │   │            │
│  │      │              │                     │   │            │
│  │      │              ▼                     │   │            │
│  │      │       on_tool_result()             │   │            │
│  │      │              │                     │   │            │
│  │      ◄──────────────┘                     │   │            │
│  │                                           │   │            │
│  └──────────────────────────────────────────┘   │            │
│      │                                           │            │
│      ▼                                           │            │
│  on_episode_end() ──────────────────────────────┘            │
│                   (if multi-episode)                          │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

#### `__init__(self)`

Called once when the agent is created.

```python
def __init__(self):
    # Initialize any persistent state
    self.total_episodes = 0
    self.best_score = 0
    self.memory = SlidingWindowMemory(capacity=50)
```

#### `on_episode_start(self) -> None`

Called at the beginning of each episode.

```python
def on_episode_start(self) -> None:
    # Reset episode-specific state
    self.memory.clear()
    self.current_goal = "explore"
    self.damage_taken = 0
```

#### `on_episode_end(self, success: bool, metrics: dict | None = None) -> None`

Called when an episode ends.

```python
def on_episode_end(self, success: bool, metrics: dict | None = None) -> None:
    self.total_episodes += 1

    if metrics:
        score = metrics.get("score", 0)
        if score > self.best_score:
            self.best_score = score
            print(f"New best: {score}")

    if success:
        print("Victory!")
```

#### `on_tool_result(self, tool: str, result: dict) -> None`

Called after each tool execution with the result.

```python
def on_tool_result(self, tool: str, result: dict) -> None:
    success = result.get("success", False)

    if tool == "collect":
        if success:
            self.items_collected += 1
        else:
            print(f"Collection failed: {result.get('error')}")

    elif tool == "move_to":
        if not success:
            # Movement blocked - maybe obstacle
            self.stuck_count += 1
```

#### `decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision`

**Required.** Called every tick to get the agent's action.

```python
def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
    # This is where your agent logic goes
    ...
    return AgentDecision(tool="idle", params={}, reasoning="")
```

---

## LLMAgentBehavior (Advanced)

Extends AgentBehavior with LLM capabilities:

```python
from agent_runtime import LLMAgentBehavior, Observation, AgentDecision, ToolSchema


class MyLLMAgent(LLMAgentBehavior):
    """An LLM-powered agent."""

    def __init__(self):
        super().__init__(
            backend="anthropic",           # or "openai", "ollama"
            model="claude-3-haiku-20240307"  # model identifier
        )
        self.system_prompt = "You are an intelligent foraging agent."

    def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
        # Build context for LLM
        context = self._format_observation(observation)

        # Get LLM response
        response = self.complete(
            prompt=context,
            temperature=0.3
        )

        # Parse response into decision
        return self._parse_response(response, tools)
```

### Constructor

```python
def __init__(self, backend: str = "anthropic", model: str = "claude-3-haiku-20240307"):
    """
    Initialize LLM agent.

    Args:
        backend: LLM provider ("anthropic", "openai", "ollama")
        model: Model identifier for the backend
    """
```

### Additional Methods

#### `complete(prompt: str, system: str | None = None, temperature: float = 0.7) -> str`

Send a prompt to the LLM and get a response.

```python
response = self.complete(
    prompt="What should I do next?",
    system="You are a careful foraging agent.",  # Optional override
    temperature=0.3  # 0 = deterministic, 1 = creative
)
```

### Environment Variables

Set these for your chosen backend:

```bash
# Anthropic
export ANTHROPIC_API_KEY="sk-..."

# OpenAI
export OPENAI_API_KEY="sk-..."

# Ollama (local)
# No API key needed, just run: ollama serve
```

---

## Registration

Agents must be registered to receive observations:

```python
from agent_runtime import AgentRegistry

# Create your agent
agent = MyAgent()

# Register it
registry = AgentRegistry()
registry.register("my_agent_id", agent)
```

The agent ID must match the ID configured in the Godot scene.
