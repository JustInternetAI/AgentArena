# Agent Arena Learner Tiers

This guide explains the three-tier progression for building AI agents in Agent Arena. Each tier builds on the previous, allowing you to gradually take more control as you learn.

## Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  TIER 1: Beginner                                               │
│  "Just implement decide()"                                      │
│                                                                 │
│  class MyAgent(SimpleAgentBehavior):                           │
│      def decide(self, observation, tools) -> AgentDecision     │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  TIER 2: Intermediate                                           │
│  "Customize the prompt, integrate LLMs"                        │
│                                                                 │
│  class MyLLMAgent(LLMAgentBehavior):                           │
│      system_prompt = "..."                                      │
│      def build_prompt(self, observation) -> str                │
│      def parse_response(self, response) -> AgentDecision       │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  TIER 3: Advanced                                               │
│  "Full control over memory, reasoning, reflection"             │
│                                                                 │
│  class MyAdvancedAgent(LLMAgentBehavior):                      │
│      memory: AgentMemory        # explicit, inspectable        │
│      reasoning_trace: list      # step-by-step log             │
│                                                                 │
│      def reflect(self, outcome) -> str      # learn from past  │
│      def plan(self, goal) -> list[Step]     # multi-step       │
│      def retrieve(self, query) -> list      # RAG access       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tier 1: Beginner

**Goal**: Understand the perception → decision → action loop.

**What you control**: Just the `decide()` function.

**What the framework handles**: Memory, prompts, LLM calls, tool execution.

### Example: Simple Forager

```python
from agent_runtime import SimpleAgentBehavior, AgentDecision, Observation

class SimpleForager(SimpleAgentBehavior):
    """A simple rule-based foraging agent."""

    def decide(self, observation: Observation, tools: list) -> AgentDecision:
        # Find nearest resource
        if observation.nearby_resources:
            nearest = min(observation.nearby_resources,
                         key=lambda r: r["distance"])

            return AgentDecision(
                tool="move_to",
                params={"target_position": nearest["position"]},
                reasoning=f"Moving to {nearest['type']}"
            )

        # Nothing to do
        return AgentDecision.idle(reasoning="No resources nearby")
```

### Key Concepts

- **Observation**: What the agent sees (position, resources, hazards, inventory)
- **AgentDecision**: What the agent does (tool name, parameters, reasoning)
- **Tools**: Available actions (move_to, collect, etc.)

### When to Graduate to Tier 2

Move to Tier 2 when you want to:
- Use an LLM for decision-making
- Customize how observations are presented to the LLM
- Control how LLM responses are parsed

---

## Tier 2: Intermediate

**Goal**: Integrate LLMs and control prompt engineering.

**What you control**: Prompts, response parsing, LLM configuration.

**What the framework handles**: LLM API calls, basic memory, tool execution.

### Example: LLM-Powered Forager

```python
from agent_runtime import LLMAgentBehavior, AgentDecision, Observation

class LLMForager(LLMAgentBehavior):
    """An LLM-powered foraging agent."""

    # Configure LLM
    provider = "ollama"  # or "anthropic", "openai"
    model = "llama2"

    system_prompt = """You are a foraging agent in a survival game.
    Your goal is to collect resources while avoiding hazards.

    Always respond with a JSON object:
    {"tool": "tool_name", "params": {...}, "reasoning": "why"}
    """

    def build_prompt(self, observation: Observation, tools: list) -> str:
        """Customize how observations are presented to the LLM."""

        resources = "\n".join([
            f"- {r['type']} at distance {r['distance']:.1f}"
            for r in observation.nearby_resources
        ])

        hazards = "\n".join([
            f"- {h['type']} at distance {h['distance']:.1f}"
            for h in observation.nearby_hazards
        ])

        return f"""
Current position: {observation.position}
Inventory: {observation.inventory}

Nearby resources:
{resources or "None"}

Nearby hazards:
{hazards or "None"}

Available tools: {[t.name for t in tools]}

What should I do next?
"""

    def parse_response(self, response: str, tools: list) -> AgentDecision:
        """Parse LLM response into an AgentDecision."""
        import json

        try:
            data = json.loads(response)
            return AgentDecision(
                tool=data["tool"],
                params=data.get("params", {}),
                reasoning=data.get("reasoning", "")
            )
        except json.JSONDecodeError:
            # Fallback if LLM doesn't return valid JSON
            return AgentDecision.idle(reasoning="Failed to parse LLM response")
```

### Key Concepts

- **system_prompt**: Instructions for the LLM
- **build_prompt()**: How to format observations for the LLM
- **parse_response()**: How to extract decisions from LLM output
- **provider/model**: Which LLM backend to use

### When to Graduate to Tier 3

Move to Tier 3 when you want to:
- Implement custom memory systems
- Add reflection and learning from past episodes
- Build multi-step planning
- Inspect and debug the agent's reasoning process

---

## Tier 3: Advanced

**Goal**: Full control over memory, reflection, and reasoning.

**What you control**: Everything in Tier 2, plus:
- Memory storage and retrieval
- Reasoning traces for debugging
- Reflection on past outcomes
- Multi-step planning

### Example: Reflective Forager

```python
from agent_runtime import LLMAgentBehavior, AgentDecision, Observation
from agent_runtime.memory import EpisodicMemory
import time

class ReflectiveForager(LLMAgentBehavior):
    """Advanced agent with memory, reflection, and full inspection."""

    provider = "ollama"
    model = "llama2"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Tier 3: Explicit memory management
        self.memory = EpisodicMemory(capacity=100)

        # Tier 3: Reasoning trace for inspection
        self.reasoning_trace = []

        # Tier 3: Store reflections
        self.reflections = []

    def decide(self, observation: Observation, tools: list) -> AgentDecision:
        """Make a decision with full logging and memory."""

        # 1. Retrieve relevant past experiences
        relevant = self.memory.query(observation, k=5)
        self.log_step("retrieved", relevant)

        # 2. Build prompt with retrieved context
        prompt = self.build_prompt(observation, tools, relevant)
        self.log_step("prompt", prompt)

        # 3. Get LLM response
        response = self.complete(prompt)
        self.log_step("response", response)

        # 4. Parse into decision
        decision = self.parse_response(response, tools)
        self.log_step("decision", decision)

        # 5. Store for future retrieval
        self.memory.add(observation, decision)

        return decision

    def build_prompt(self, observation: Observation, tools: list,
                     relevant_memories: list) -> str:
        """Build prompt with retrieved context."""

        # Include relevant past experiences
        memory_context = "\n".join([
            f"- Past: {m.summary}" for m in relevant_memories
        ]) if relevant_memories else "No relevant memories."

        return f"""
{self.system_prompt}

## Relevant Past Experiences
{memory_context}

## Current Situation
Position: {observation.position}
Resources: {observation.nearby_resources}
Hazards: {observation.nearby_hazards}

What should I do?
"""

    def reflect(self, outcome: dict) -> None:
        """Called after episode ends - learn from experience."""

        prompt = f"""
Episode summary:
- Resources collected: {outcome.get('resources_collected', 0)}
- Damage taken: {outcome.get('damage_taken', 0)}
- Decisions made: {len(self.reasoning_trace)}

Review the reasoning trace and identify:
1. What decisions worked well?
2. What could be improved?
3. What patterns should I remember?
"""

        insight = self.complete(prompt)
        self.reflections.append({
            "timestamp": time.time(),
            "outcome": outcome,
            "insight": insight
        })
        self.log_step("reflection", insight)

    def log_step(self, step_name: str, data) -> None:
        """Add to reasoning trace for inspection."""
        self.reasoning_trace.append({
            "step": step_name,
            "timestamp": time.time(),
            "data": data
        })

    def inspect(self) -> dict:
        """Return full state for debugging."""
        return {
            "memory": self.memory.dump(),
            "reasoning_trace": self.reasoning_trace,
            "reflections": self.reflections
        }

    def on_episode_start(self) -> None:
        """Clear per-episode state."""
        self.reasoning_trace = []

    def on_episode_end(self, success: bool) -> None:
        """Trigger reflection."""
        self.reflect({"success": success})
```

### Key Concepts

- **self.memory**: Explicit memory storage and retrieval
- **self.reasoning_trace**: Log every step of the decision process
- **self.reflections**: Store insights from past episodes
- **log_step()**: Record each step for later inspection
- **reflect()**: Learn from episode outcomes
- **inspect()**: Export full state for debugging

### Inspection Tooling

Tier 3 agents can be inspected using CLI tools:

```bash
# View last decision trace
python -m tools.inspect_agent --agent foraging_agent_001 --last-decision

# View memory contents
python -m tools.inspect_agent --agent foraging_agent_001 --memory

# Watch live decisions
python -m tools.inspect_agent --agent foraging_agent_001 --watch
```

---

## Summary

| Tier | Focus | You Control | Framework Handles |
|------|-------|-------------|-------------------|
| 1 | Logic | `decide()` | Everything else |
| 2 | Prompting | `decide()`, `build_prompt()`, `parse_response()` | LLM calls, memory, tools |
| 3 | Learning | All of Tier 2 + memory, reflection, traces | LLM calls, tools |

## What Stays in Infrastructure

Regardless of tier, learners never need to touch:

- HTTP/IPC communication with Godot
- GPU memory management
- Model loading and inference
- Godot scene scripts
- Tool execution mechanics

These are **infrastructure** - they just work. Learners focus on **agent behavior** - what the agent thinks and decides.

---

## Related Documentation

- [architecture.md](architecture.md) - System architecture overview
- [foraging_demo_guide.md](foraging_demo_guide.md) - Running the foraging demo
- [backlog_items.md](backlog_items.md) - Feature roadmap including Tier 3 tooling
