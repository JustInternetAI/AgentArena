# Prompt Engineering for Agents

Crafting effective prompts is crucial for LLM-powered agents. This guide covers techniques specific to agentic AI.

## The Anatomy of an Agent Prompt

Agent prompts have distinct components:

```
┌─────────────────────────────────────────────────────────────┐
│  SYSTEM PROMPT                                               │
│  - Agent identity and role                                   │
│  - Core behaviors and priorities                             │
│  - Output format requirements                                │
├─────────────────────────────────────────────────────────────┤
│  CONTEXT                                                     │
│  - Current state (position, health, inventory)               │
│  - Perception (resources, hazards, entities)                 │
│  - Memory (past observations, patterns)                      │
├─────────────────────────────────────────────────────────────┤
│  AVAILABLE ACTIONS                                           │
│  - Tool descriptions with parameters                         │
│  - Examples of valid responses                               │
├─────────────────────────────────────────────────────────────┤
│  QUERY                                                       │
│  - What decision is needed now?                              │
│  - Any specific constraints or goals?                        │
└─────────────────────────────────────────────────────────────┘
```

## System Prompts

The system prompt establishes your agent's identity and behavior:

### Basic System Prompt

```python
system_prompt = """You are a foraging agent in a simulated environment.
Your goal is to collect all resources while staying safe."""
```

### Detailed System Prompt

```python
system_prompt = """You are an autonomous foraging agent operating in a game environment.

IDENTITY:
- You are a survival-focused collector
- You prioritize safety over efficiency
- You learn from past experiences

CORE BEHAVIORS:
1. SAFETY FIRST: Always check for nearby hazards before moving
2. EFFICIENCY: Minimize unnecessary movement
3. AWARENESS: Remember where you've been and what you've seen
4. ADAPTABILITY: Change strategy when current approach isn't working

DECISION PROCESS:
1. Assess current threats
2. Evaluate available opportunities
3. Consider past experience
4. Choose action that maximizes long-term success

OUTPUT FORMAT:
Always respond with:
REASONING: Your step-by-step analysis
TOOL: The tool name to execute
PARAMS: JSON object with parameters"""
```

## Context Formatting

How you present information affects LLM comprehension:

### Poor Context (Dense, Hard to Parse)

```python
# Avoid this
context = f"pos={obs.position} hp={obs.health} resources={obs.nearby_resources} hazards={obs.nearby_hazards}"
```

### Good Context (Structured, Clear)

```python
def format_context(self, obs: Observation) -> str:
    return f"""
## CURRENT STATE
- Position: ({obs.position[0]:.1f}, {obs.position[1]:.1f}, {obs.position[2]:.1f})
- Health: {obs.health}/100 {"[CRITICAL]" if obs.health < 30 else ""}
- Energy: {obs.energy}/100
- Inventory: {len(obs.inventory)} items

## NEARBY RESOURCES ({len(obs.nearby_resources)} visible)
{self._format_resources(obs.nearby_resources)}

## HAZARDS ({len(obs.nearby_hazards)} detected)
{self._format_hazards(obs.nearby_hazards)}
"""

def _format_resources(self, resources: list) -> str:
    if not resources:
        return "None in range"
    lines = []
    for r in sorted(resources, key=lambda x: x.distance)[:5]:
        lines.append(f"  - {r.name} ({r.type}): {r.distance:.1f}m away")
    return "\n".join(lines)

def _format_hazards(self, hazards: list) -> str:
    if not hazards:
        return "None detected"
    lines = []
    for h in sorted(hazards, key=lambda x: x.distance)[:3]:
        danger = "DANGER" if h.distance < 3 else "warning"
        lines.append(f"  - [{danger}] {h.name}: {h.distance:.1f}m, {h.damage} damage")
    return "\n".join(lines)
```

## Tool Descriptions

Help the LLM understand what tools do:

### Basic Tool Format

```python
def format_tools(self, tools: list[ToolSchema]) -> str:
    lines = ["## AVAILABLE ACTIONS"]
    for tool in tools:
        params = ", ".join(f"{p.name}" for p in tool.parameters)
        lines.append(f"- {tool.name}({params})")
    return "\n".join(lines)
```

### Rich Tool Format with Examples

```python
def format_tools_rich(self, tools: list[ToolSchema]) -> str:
    tool_docs = {
        "move_to": {
            "description": "Move toward a target position",
            "example": '{"target_position": [10.0, 0.0, 5.0]}',
            "notes": "Movement is gradual; may take multiple ticks to reach target"
        },
        "collect": {
            "description": "Collect a nearby resource (must be within 2 units)",
            "example": '{"resource_id": "apple_001"}',
            "notes": "Will fail if resource is too far away"
        },
        "idle": {
            "description": "Do nothing this tick (rest, observe)",
            "example": '{}',
            "notes": "Useful when waiting or recovering energy"
        }
    }

    lines = ["## AVAILABLE ACTIONS\n"]
    for tool in tools:
        doc = tool_docs.get(tool.name, {})
        lines.append(f"### {tool.name}")
        lines.append(f"Description: {doc.get('description', tool.description)}")
        lines.append(f"Example: PARAMS: {doc.get('example', '{}')}")
        if doc.get('notes'):
            lines.append(f"Note: {doc['notes']}")
        lines.append("")

    return "\n".join(lines)
```

## Few-Shot Examples

Give the LLM examples of good decisions:

```python
few_shot_examples = """
## DECISION EXAMPLES

### Example 1: Safe Collection
Situation: Apple 1.5m away, no hazards
REASONING: There's an apple very close and no threats. I should collect it.
TOOL: collect
PARAMS: {"resource_id": "apple_001"}

### Example 2: Avoiding Danger
Situation: Resource 5m away, pit between us at 2m
REASONING: The pit is between me and the resource. I need to move around it first.
TOOL: move_to
PARAMS: {"target_position": [8.0, 0.0, 12.0]}

### Example 3: Recovery
Situation: Health at 15%, no immediate threats
REASONING: My health is critically low. I should rest to recover before taking risks.
TOOL: idle
PARAMS: {}
"""
```

## Chain-of-Thought Prompting

Encourage step-by-step reasoning:

```python
query = """
Before deciding, work through these steps:

1. THREAT ASSESSMENT: Are there any immediate dangers?
2. OPPORTUNITY SCAN: What resources are available?
3. MEMORY CHECK: What have I learned from past observations?
4. ACTION SELECTION: Based on above, what's the best action?

Now analyze the current situation and decide:"""
```

## Handling Edge Cases

Prompt for graceful failure handling:

```python
system_prompt_addendum = """
EDGE CASES:
- If no resources visible: Explore by moving to unexplored areas
- If surrounded by hazards: Move toward the largest gap
- If stuck (same position for 3+ ticks): Try a random direction
- If health critical (<20%): Prioritize escape over collection
- If uncertain: Choose idle and observe

NEVER:
- Move directly toward a hazard
- Try to collect a resource that's too far
- Use an invalid tool name
"""
```

## Output Parsing Reliability

Design prompts for reliable parsing:

### Strict Format

```python
format_instructions = """
You MUST respond in EXACTLY this format:

REASONING: [Your analysis in 1-2 sentences]
TOOL: [exactly one of: move_to, collect, idle]
PARAMS: [valid JSON object on single line]

Example valid response:
REASONING: Apple is close and safe to collect.
TOOL: collect
PARAMS: {"resource_id": "apple_001"}

Do not include any other text outside this format.
"""
```

### Fallback Handling

```python
def _parse_with_fallback(self, response: str, tools: list[ToolSchema]) -> AgentDecision:
    """Parse response with multiple fallback strategies."""
    # Try strict parsing first
    decision = self._strict_parse(response)
    if decision:
        return decision

    # Try lenient parsing (common variations)
    decision = self._lenient_parse(response)
    if decision:
        return decision

    # Check if response contains a tool name anywhere
    for tool in tools:
        if tool.name in response.lower():
            return AgentDecision(
                tool=tool.name,
                params={},
                reasoning="Extracted tool from unstructured response"
            )

    # Ultimate fallback
    return AgentDecision.idle(reasoning="Could not parse LLM response")
```

## Temperature and Consistency

Control randomness for different situations:

```python
class AdaptiveAgent(LLMAgentBehavior):
    def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
        # Low temperature for dangerous situations (be predictable)
        if self._in_danger(observation):
            return self._decide_with_temperature(observation, tools, temperature=0.0)

        # Medium temperature for normal operation
        if observation.nearby_resources:
            return self._decide_with_temperature(observation, tools, temperature=0.3)

        # Higher temperature for exploration (be creative)
        return self._decide_with_temperature(observation, tools, temperature=0.7)

    def _decide_with_temperature(self, obs, tools, temperature: float) -> AgentDecision:
        context = self._build_context(obs, tools)
        response = self.complete(context, temperature=temperature)
        return self._parse_response(response, tools)
```

## Prompt Templates

Create reusable templates:

```python
class PromptTemplates:
    FORAGING = """
You are a foraging agent collecting resources in a meadow.

Current State:
{state}

Nearby Resources:
{resources}

Hazards:
{hazards}

Choose your next action wisely.
"""

    SURVIVAL = """
You are a survival agent in a dangerous environment.
Your primary goal is staying alive. Secondary goal is exploration.

Health: {health}/100 - {"CRITICAL" if health < 30 else "OK"}
Energy: {energy}/100

Threats: {threats}
Resources: {resources}

What do you do?
"""

    CRAFTING = """
You are a crafting agent working toward building a shelter.

Current inventory: {inventory}
Crafting goal: {goal}
Materials needed: {materials_needed}

Available resources nearby:
{nearby_resources}

Plan your next action to progress toward the crafting goal.
"""
```

## Debugging Prompts

Add debugging information when developing:

```python
def _build_debug_context(self, obs: Observation) -> str:
    return f"""
[DEBUG MODE]
Tick: {obs.tick}
Raw observation: {obs.to_dict()}

[MEMORY]
Stored observations: {len(self.memory.retrieve())}

[DECISION HISTORY]
Last 3 decisions: {self._recent_decisions}

Explain your reasoning in detail:
"""
```

## Next Steps

- [Custom Memory](03_custom_memory.md) - Build memory systems that enhance prompts
- [Planning](04_planning.md) - Implement multi-step reasoning
