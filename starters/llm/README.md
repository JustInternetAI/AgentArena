# LLM Agent Starter

Agent powered by local language models for natural language reasoning.

## What's New vs Intermediate

| Feature | Intermediate | LLM |
|---------|--------------|-----|
| Reasoning | Hardcoded logic | Natural language |
| Adaptability | Fixed priorities | Learns from context |
| Complexity | Can handle moderate | Can handle complex |
| Explanations | Simple messages | Detailed reasoning |

## Files

```
llm/
├── agent.py          # LLM-powered agent
├── llm_client.py     # LLM interface (YOUR CODE!)
├── memory.py         # Sliding window memory
├── prompts/
│   ├── system.txt    # System prompt (MODIFY THIS!)
│   └── decision.txt  # Decision template (MODIFY THIS!)
├── run.py            # Entry point
└── requirements.txt  # Dependencies
```

## Requirements

### 1. Model

Download a model using the model manager:

```bash
cd ../../python
python -m tools.model_manager download llama-2-7b-chat --format gguf --quantization q4_k_m
```

### 2. GPU (Recommended)

For good performance, use a GPU with CUDA support. The agent will use all available GPU layers by default.

Can run on CPU but will be slower.

### 3. Dependencies

```bash
pip install -r requirements.txt
```

## Quick Start

```bash
# With default model
python run.py

# With custom model
python run.py --model path/to/your/model.gguf
```

Then connect from Agent Arena game.

## How It Works

### Prompt Construction

Every tick, the agent builds a prompt containing:
- System instructions (from `prompts/system.txt`)
- Current observation (position, health, nearby entities)
- Objective and progress
- Memory summary
- Decision template (from `prompts/decision.txt`)

### LLM Processing

The LLM receives this prompt and returns a JSON decision:

```json
{
    "tool": "move_to",
    "params": {"target_position": [10.0, 0.0, 5.0]},
    "reasoning": "Moving toward berry to collect resources for objective"
}
```

### Tool Execution

The decision is parsed and sent to the game for execution.

## Customization

### Modify Prompts

The easiest way to change behavior is to edit the prompts:

**`prompts/system.txt`** - Agent's personality and strategy:
```
You are a cautious agent that prioritizes safety over speed.
Always check for hazards before moving to new areas.
```

**`prompts/decision.txt`** - Decision format and context:
```
Think through:
1. What are the immediate threats?
2. What resources are most valuable?
3. What's the most efficient path?
```

### Adjust Temperature

In `agent.py`, change `temperature` to control creativity:
- `0.0` = Deterministic, conservative
- `0.7` = Balanced (default)
- `1.0` = Creative, exploratory

### Change Memory

Modify `capacity` to remember more or fewer observations:
```python
self.memory = SlidingWindowMemory(capacity=50)  # Remember more
```

### Add Few-Shot Examples

Add examples to `prompts/decision.txt`:
```
Example 1:
Observation: Berry at 2m, health 80
Decision: {"tool": "collect", "params": {"target_name": "berry_001"}}

Example 2:
Observation: Fire hazard at 1m, health 30
Decision: {"tool": "move_to", "params": {"target_position": [safe_x, safe_y, safe_z]}}
```

## Performance Tips

### GPU Usage

The agent uses all GPU layers by default (`n_gpu_layers=-1`). If you run out of VRAM:

```python
self.llm = LLMClient(
    model_path=model_path,
    n_gpu_layers=32,  # Use only 32 layers on GPU
)
```

### Model Selection

Smaller models are faster but less capable:
- **Llama 2 7B Q4**: Fast, good for simple scenarios
- **Llama 2 13B Q4**: Slower, better reasoning
- **Mistral 7B Q4**: Good balance of speed and quality

### Token Limits

Reduce `max_tokens` if generation is slow:
```python
self.llm = LLMClient(
    model_path=model_path,
    max_tokens=256,  # Shorter responses
)
```

## Debugging

### View Prompts

Add logging to see what's sent to the LLM:
```python
def _build_prompt(self, obs: Observation) -> str:
    prompt = ...
    print("=" * 60)
    print("PROMPT:")
    print(prompt)
    print("=" * 60)
    return prompt
```

### Check LLM Responses

Log the raw LLM output:
```python
response = self.llm.generate(prompt=prompt, tools=tools)
print("LLM Response:", response["text"])
```

### Test Prompts Offline

Test your prompts without running the game:
```python
from llm_client import LLMClient

client = LLMClient(model_path="path/to/model.gguf")
response = client.generate("Test prompt here")
print(response)
```

## Common Issues

### Model not found
- Check model path
- Run model manager to download: `python -m tools.model_manager list`

### Out of memory (GPU)
- Reduce `n_gpu_layers`
- Use smaller model (7B instead of 13B)
- Use more aggressive quantization (Q2 instead of Q4)

### Slow generation
- Use GPU if available
- Reduce `max_tokens`
- Use faster model (7B instead of 13B)

### Poor decisions
- Improve prompts (add examples, clearer instructions)
- Increase temperature for exploration
- Use larger/better model

## Advanced Modifications

### Multi-Step Planning

Add planning prompts to think ahead:
```
Before deciding, create a 3-step plan:
1. Immediate action (this tick)
2. Next action (next 1-2 ticks)
3. Long-term goal (next 5-10 ticks)
```

### Reflection

Add a reflection phase after decisions:
```python
# After decision, reflect on it
reflection_prompt = f"You decided to {decision.tool}. Was this wise?"
reflection = self.llm.generate(reflection_prompt)
```

### Semantic Memory

Replace `SlidingWindowMemory` with semantic search:
- Embed observations
- Retrieve similar past situations
- Use for few-shot examples

## Resources

- [Model Manager Guide](../../docs/model_manager.md)
- [Prompt Engineering](../../docs/prompt_engineering.md)
- [LLM Backends](../../python/backends/README.md)

---

**Note:** This starter requires a downloaded model and GPU for best performance. See model manager documentation for setup.
