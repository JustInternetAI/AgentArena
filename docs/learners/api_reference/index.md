# API Reference

Complete reference for the Agent Arena Python API.

## Quick Links

- [Observations](observations.md) - Data your agent receives
- [Decisions](decisions.md) - How to respond to observations
- [Behaviors](behaviors.md) - Agent base classes
- [Memory](memory.md) - Built-in memory systems
- [Tools](tools.md) - Available actions

## Import Patterns

### Beginner Tier
```python
from agent_runtime import SimpleAgentBehavior, SimpleContext
```

### Intermediate Tier
```python
from agent_runtime import AgentBehavior, Observation, AgentDecision, ToolSchema
from agent_runtime.memory import SlidingWindowMemory
```

### Advanced Tier
```python
from agent_runtime import LLMAgentBehavior, Observation, AgentDecision, ToolSchema
from agent_runtime.memory import SlidingWindowMemory, Memory
```

## Type Summary

| Type | Tier | Purpose |
|------|------|---------|
| `SimpleContext` | Beginner | Simplified observation data |
| `Observation` | Intermediate+ | Full observation with all details |
| `AgentDecision` | Intermediate+ | Structured decision with parameters |
| `ToolSchema` | Intermediate+ | Tool metadata and parameter specs |
| `ResourceInfo` | Intermediate+ | Resource details |
| `HazardInfo` | Intermediate+ | Hazard details |
| `ItemInfo` | Intermediate+ | Inventory item details |
| `EntityInfo` | Intermediate+ | Visible entity details |
