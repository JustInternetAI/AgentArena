# LLM Backends

Welcome to the advanced tier! Here you'll integrate Large Language Models (LLMs) to give your agents natural language reasoning capabilities.

## Why Use an LLM?

Until now, your agents have used **hand-coded logic**:

```python
# Intermediate approach: explicit rules
if observation.health < 30:
    return self._escape()
elif observation.nearby_resources:
    return self._collect_nearest()
else:
    return self._explore()
```

With an LLM, your agent can **reason about situations**:

```python
# Advanced approach: LLM reasoning
response = self.llm.complete(f"""
You are a foraging agent. Current situation:
- Health: {observation.health}%
- Nearby resources: {len(observation.nearby_resources)}
- Nearby hazards: {len(observation.nearby_hazards)}

What should you do and why?
""")
# LLM: "My health is critically low at 25%. Even though I see 3 resources
# nearby, I should prioritize survival. I'll move away from hazards first,
# then consider collecting resources once I'm safe."
```

## The LLMAgentBehavior Base Class

```python
from agent_runtime import LLMAgentBehavior, Observation, AgentDecision, ToolSchema


class MyLLMAgent(LLMAgentBehavior):
    """Agent powered by an LLM backend."""

    def __init__(self, backend: str = "anthropic", model: str = "claude-3-haiku-20240307"):
        super().__init__(backend=backend, model=model)
        self.system_prompt = """You are an intelligent foraging agent.
        Your goal is to collect resources while avoiding hazards.
        Always explain your reasoning before choosing an action."""

    def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
        # Build context for the LLM
        context = self._build_context(observation, tools)

        # Get LLM response
        response = self.complete(context)

        # Parse response into decision
        return self._parse_response(response, tools)
```

## Supported Backends

### Anthropic (Claude)

```python
from agent_runtime import LLMAgentBehavior

class ClaudeAgent(LLMAgentBehavior):
    def __init__(self):
        super().__init__(
            backend="anthropic",
            model="claude-3-haiku-20240307",  # Fast and cheap
            # model="claude-3-sonnet-20240229",  # Balanced
            # model="claude-3-opus-20240229",    # Most capable
        )
```

**Setup:**
```bash
export ANTHROPIC_API_KEY="your-key-here"
```

### OpenAI (GPT)

```python
class GPTAgent(LLMAgentBehavior):
    def __init__(self):
        super().__init__(
            backend="openai",
            model="gpt-4o-mini",        # Fast and cheap
            # model="gpt-4o",            # Balanced
            # model="gpt-4-turbo",       # More capable
        )
```

**Setup:**
```bash
export OPENAI_API_KEY="your-key-here"
```

### Local Models (Ollama)

```python
class LocalAgent(LLMAgentBehavior):
    def __init__(self):
        super().__init__(
            backend="ollama",
            model="llama3.2",      # Meta's Llama
            # model="mistral",     # Mistral AI
            # model="codellama",   # Code-focused
        )
```

**Setup:**
```bash
# Install Ollama from https://ollama.ai
ollama pull llama3.2
ollama serve
```

## The Complete Method

The `complete` method sends a prompt to the LLM and returns the response:

```python
def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
    # Simple completion
    response = self.complete("What should I do next?")

    # With system prompt override
    response = self.complete(
        prompt="Analyze this situation...",
        system="You are a cautious agent that prioritizes safety."
    )

    # With temperature control
    response = self.complete(
        prompt="Choose an action",
        temperature=0.0  # 0 = deterministic, 1 = creative
    )
```

## Building Context

Structure your prompts to give the LLM the information it needs:

```python
def _build_context(self, obs: Observation, tools: list[ToolSchema]) -> str:
    # Format available tools
    tool_descriptions = []
    for tool in tools:
        params = ", ".join(f"{p.name}: {p.type}" for p in tool.parameters)
        tool_descriptions.append(f"- {tool.name}({params}): {tool.description}")

    # Format nearby resources
    resources = []
    for r in obs.nearby_resources[:5]:  # Limit to avoid token bloat
        resources.append(f"- {r.name} ({r.type}): {r.distance:.1f} units away")

    # Format hazards
    hazards = []
    for h in obs.nearby_hazards[:3]:
        hazards.append(f"- {h.name} ({h.type}): {h.distance:.1f} units, {h.damage} damage")

    return f"""
CURRENT STATE:
- Position: {obs.position}
- Health: {obs.health}/100
- Energy: {obs.energy}/100
- Inventory: {[item.name for item in obs.inventory]}

NEARBY RESOURCES:
{chr(10).join(resources) or "None visible"}

NEARBY HAZARDS:
{chr(10).join(hazards) or "None visible"}

AVAILABLE TOOLS:
{chr(10).join(tool_descriptions)}

Based on this information, choose a tool to use and explain your reasoning.
Respond in the format:
REASONING: <your analysis>
TOOL: <tool_name>
PARAMS: <json parameters>
"""
```

## Parsing LLM Responses

Extract structured decisions from LLM text:

```python
import json
import re

def _parse_response(self, response: str, tools: list[ToolSchema]) -> AgentDecision:
    """Parse LLM response into an AgentDecision."""
    # Extract reasoning
    reasoning_match = re.search(r'REASONING:\s*(.+?)(?=TOOL:|$)', response, re.DOTALL)
    reasoning = reasoning_match.group(1).strip() if reasoning_match else ""

    # Extract tool
    tool_match = re.search(r'TOOL:\s*(\w+)', response)
    if not tool_match:
        return AgentDecision.idle(reasoning="Could not parse tool from response")

    tool_name = tool_match.group(1)

    # Validate tool exists
    valid_tools = [t.name for t in tools]
    if tool_name not in valid_tools:
        return AgentDecision.idle(reasoning=f"Unknown tool: {tool_name}")

    # Extract parameters
    params = {}
    params_match = re.search(r'PARAMS:\s*(\{.+?\})', response, re.DOTALL)
    if params_match:
        try:
            params = json.loads(params_match.group(1))
        except json.JSONDecodeError:
            pass  # Use empty params

    return AgentDecision(
        tool=tool_name,
        params=params,
        reasoning=reasoning[:200]  # Truncate for logging
    )
```

## Cost and Latency Considerations

LLM calls have real costs and latency:

| Model | Cost per 1K tokens | Latency | Best For |
|-------|-------------------|---------|----------|
| claude-3-haiku | $0.00025 | ~200ms | Every tick |
| gpt-4o-mini | $0.00015 | ~300ms | Every tick |
| claude-3-sonnet | $0.003 | ~500ms | Planning |
| gpt-4o | $0.005 | ~800ms | Complex reasoning |
| Local (Ollama) | Free | Varies | Development |

**Tips for managing costs:**
- Use cheap/fast models for routine decisions
- Cache common situations
- Only call LLM when situation changes significantly
- Use local models during development

```python
class CostAwareAgent(LLMAgentBehavior):
    def __init__(self):
        super().__init__(backend="anthropic", model="claude-3-haiku-20240307")
        self._last_situation_hash = None
        self._cached_decision = None

    def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
        # Hash current situation
        situation_hash = self._hash_situation(observation)

        # Return cached decision if situation unchanged
        if situation_hash == self._last_situation_hash and self._cached_decision:
            return self._cached_decision

        # New situation - call LLM
        self._last_situation_hash = situation_hash
        self._cached_decision = self._llm_decide(observation, tools)
        return self._cached_decision

    def _hash_situation(self, obs: Observation) -> str:
        """Create a hash of the relevant situation aspects."""
        return f"{len(obs.nearby_resources)}:{len(obs.nearby_hazards)}:{obs.health//10}"
```

## Full Example: LLM Forager

```python
from agent_runtime import LLMAgentBehavior, Observation, AgentDecision, ToolSchema
from agent_runtime.memory import SlidingWindowMemory
import json
import re


class LLMForager(LLMAgentBehavior):
    """An LLM-powered foraging agent with memory."""

    def __init__(self):
        super().__init__(backend="anthropic", model="claude-3-haiku-20240307")
        self.memory = SlidingWindowMemory(capacity=10)
        self.system_prompt = """You are an intelligent foraging agent in a game world.
Your goal is to collect all resources while avoiding hazards.

Key behaviors:
- Prioritize safety (avoid hazards)
- Be efficient (minimize travel distance)
- Learn from past observations

When responding, always provide:
1. REASONING: Your analysis of the situation
2. TOOL: The tool to use (move_to, collect, or idle)
3. PARAMS: JSON parameters for the tool"""

    def on_episode_start(self):
        self.memory.clear()

    def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
        self.memory.store(observation)

        # Build context with memory
        context = self._build_context(observation, tools)

        # Get LLM decision
        response = self.complete(context)

        # Parse and return
        return self._parse_response(response, tools)

    def _build_context(self, obs: Observation, tools: list[ToolSchema]) -> str:
        # Get recent memory summary
        recent = self.memory.retrieve()
        memory_summary = f"Observations in memory: {len(recent)}"
        if recent:
            positions = [o.position for o in recent[-3:]]
            memory_summary += f"\nRecent positions: {positions}"

        # Format current state
        resources = [f"{r.name}: {r.distance:.1f}m" for r in obs.nearby_resources[:5]]
        hazards = [f"{h.name}: {h.distance:.1f}m ({h.damage} dmg)" for h in obs.nearby_hazards[:3]]

        return f"""
MEMORY:
{memory_summary}

CURRENT STATE:
Position: {obs.position}
Health: {obs.health}/100
Inventory: {len(obs.inventory)} items

NEARBY RESOURCES:
{chr(10).join(resources) or "None"}

HAZARDS:
{chr(10).join(hazards) or "None"}

What should I do?"""

    def _parse_response(self, response: str, tools: list[ToolSchema]) -> AgentDecision:
        # Extract parts
        reasoning = ""
        tool_name = "idle"
        params = {}

        if "REASONING:" in response:
            reasoning = response.split("REASONING:")[1].split("TOOL:")[0].strip()

        if "TOOL:" in response:
            tool_part = response.split("TOOL:")[1]
            tool_name = tool_part.split()[0].strip().lower()

        if "PARAMS:" in response:
            params_part = response.split("PARAMS:")[1].strip()
            try:
                # Find JSON object
                match = re.search(r'\{[^}]+\}', params_part)
                if match:
                    params = json.loads(match.group())
            except:
                pass

        # Validate tool
        valid_tools = {t.name for t in tools}
        if tool_name not in valid_tools:
            tool_name = "idle"
            reasoning = f"Invalid tool '{tool_name}', idling"

        return AgentDecision(
            tool=tool_name,
            params=params,
            reasoning=reasoning[:100]
        )
```

## Next Steps

- [Prompt Engineering](02_prompt_engineering.md) - Craft effective prompts for better decisions
- [Custom Memory](03_custom_memory.md) - Build sophisticated memory systems
- [Planning](04_planning.md) - Multi-step reasoning and goal decomposition
