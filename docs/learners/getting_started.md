# Getting Started with Agent Arena

Welcome to Agent Arena! This guide will have you running your first AI agent in minutes.

## What is Agent Arena?

Agent Arena is an educational framework for learning **agentic AI** - building AI systems that can perceive, reason, and act autonomously. Instead of reading theory, you'll build and deploy agents into simulated environments where you can watch them succeed or fail in real-time.

## Prerequisites

- Python 3.11+
- Basic Python knowledge (if/else, classes, functions)
- No game development experience required!
- No C++ knowledge required!

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/JustInternetAI/AgentArena.git
cd AgentArena

# Setup Python environment
cd python
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

pip install -r requirements.txt
```

### 2. Run Your First Agent

```bash
python run_foraging_demo.py
```

You should see:
```
============================================================
Foraging Demo - SimpleForager Agent
============================================================
Registering SimpleForager agent...
  ✓ Registered SimpleForager for agent_id: foraging_agent_001
✓ IPC Server ready at http://127.0.0.1:5000
✓ Waiting for observations from Godot...
```

### 3. Open Godot and Watch

1. Open Godot Engine 4.5+
2. Open the Agent Arena project
3. Open `scenes/foraging.tscn`
4. Press F5 to run
5. Press SPACE to start the simulation
6. Watch your agent collect resources!

## What Just Happened?

Your agent is:
1. **Observing** - Receiving information about nearby resources and hazards
2. **Deciding** - Choosing what tool to use (move_to, collect, idle)
3. **Acting** - Executing the chosen action in the game world

This is the core **perception → reasoning → action** loop that all AI agents follow.

## Next Steps

Choose your learning path based on your experience:

### Beginner Path
Start here if you're new to agentic AI.
- [What is an Agent?](beginner/01_what_is_an_agent.md)
- [Understanding Observations](beginner/02_observations.md)
- [Available Tools](beginner/03_tools.md)
- [Build Your First Agent](beginner/04_your_first_agent.md)

### Intermediate Path
Start here if you understand the basics and want more control.
- [Full Observation Details](intermediate/01_full_observations.md)
- [Explicit Parameters](intermediate/02_explicit_parameters.md)
- [Memory Systems](intermediate/03_memory_systems.md)

### Advanced Path
Start here if you want to integrate LLMs and build sophisticated agents.
- [LLM Backends](advanced/01_llm_backends.md)
- [Prompt Engineering](advanced/02_prompt_engineering.md)
- [Custom Memory](advanced/03_custom_memory.md)

## The Three Tiers

Agent Arena has a layered learning system:

| Tier | You Write | Framework Handles | Focus |
|------|-----------|-------------------|-------|
| **Beginner** | Tool name (`"move_to"`) | Parameters, memory | Understanding the loop |
| **Intermediate** | Full decision + params | - | Memory, state tracking |
| **Advanced** | Everything + LLM | - | Planning, reasoning |

You can progress through tiers as you learn, or jump to whichever fits your experience.

## Getting Help

- Check the [API Reference](api_reference/) for detailed documentation
- Look at [Example Agents](../python/user_agents/examples/) for inspiration
- Open an issue on [GitHub](https://github.com/JustInternetAI/AgentArena/issues)
