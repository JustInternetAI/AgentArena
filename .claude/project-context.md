# Agent Arena - Project Context

Reference documentation for vision, design, and architecture. For actionable instructions (commands, structure, workflows), see `CLAUDE.md` in the project root.

---

## Vision & Purpose

### What is Agent Arena?

Agent Arena is an **educational framework for learning agentic AI programming** through interactive game scenarios. Rather than reading about agents in isolation, developers build and deploy AI agents into simulated environments where they can observe, debug, and iterate on agent behavior in real-time.

Think of it as a **"gym" for AI agents** - a place where developers can:
- Learn the fundamentals of agentic AI (perception, reasoning, tool use, memory)
- Experiment with different architectures and LLM backends
- Test agents against progressively challenging scenarios
- Compare approaches and share results

### Why Agent Arena?

**The Problem**: Agentic AI is becoming essential, but learning it is fragmented. Tutorials show toy examples. Real deployments are too complex. There's no middle ground where you can safely experiment and see immediate results.

**The Solution**: A game-like environment where:
1. **Scenarios are self-contained** - Clear objectives, measurable outcomes
2. **Feedback is immediate** - Watch your agent succeed or fail in real-time
3. **Debugging is possible** - Deterministic replay, step-through mode, prompt inspection
4. **Complexity is progressive** - Start simple, unlock harder challenges

### Core Educational Goals

1. **Tool Use** - Learn how agents call functions to interact with the world
2. **Observation Processing** - Understand how agents perceive and interpret their environment
3. **Memory Systems** - Implement short-term, long-term, and episodic memory
4. **Planning & Reasoning** - Build agents that decompose goals and execute multi-step plans
5. **Multi-Agent Coordination** - Design agents that communicate and cooperate

### Target Audience

- **AI/ML developers** wanting hands-on experience with agentic systems
- **Students** learning about autonomous agents and LLM applications
- **Researchers** needing reproducible benchmarks for agent evaluation
- **Hobbyists** who want to build and experiment with AI agents

---

## Design Principles

1. **Observability First** - Every agent decision should be inspectable (what it saw, what it thought, what it did)
2. **Deterministic Replay** - Any run can be replayed exactly for debugging and comparison
3. **Backend Agnostic** - Swap LLM backends without changing agent code (llama.cpp, vLLM, OpenAI, etc.)
4. **Scenario as Curriculum** - Scenarios teach specific skills, ordered by complexity
5. **Metrics Matter** - Every scenario has clear success metrics for objective comparison
6. **Layered Complexity** - Simple interface for beginners, full control for advanced users

---

## Scenario Progression (Learning Path)

### Tier 1: Foundations
| Scenario | Concepts Taught |
|----------|-----------------|
| **Simple Navigation** | Basic tool use, movement, observation handling |
| **Foraging** | Resource detection, goal-directed behavior, basic planning |
| **Obstacle Course** | Spatial reasoning, sequential decision-making |

### Tier 2: Memory & Planning
| Scenario | Concepts Taught |
|----------|-----------------|
| **Crafting Chain** | Multi-step planning, dependency resolution, inventory management |
| **Scavenger Hunt** | Long-term memory, revisiting locations, deferred goals |
| **Maze Exploration** | Map building, memory-augmented navigation |

### Tier 3: Adversarial & Dynamic
| Scenario | Concepts Taught |
|----------|-----------------|
| **Predator Evasion** | Reactive planning, risk assessment, dynamic re-planning |
| **Resource Competition** | Opponent modeling, strategic behavior |
| **Tower Defense** | Real-time decision-making under pressure |

### Tier 4: Multi-Agent Cooperation
| Scenario | Concepts Taught |
|----------|-----------------|
| **Team Capture** | Communication, role assignment, coordinated actions |
| **Collaborative Building** | Shared goals, task distribution, conflict resolution |
| **Relay Race** | Handoffs, timing, trust between agents |

---

## Three-Tier Agent Interface

The framework provides a **three-tier learning progression** so users can start simple and grow into full control. Learners do NOT need C++ or game development knowledge - all agent logic is written in Python.

### Tier 1: Beginner (SimpleAgentBehavior)
```python
from agent_runtime import SimpleAgentBehavior, SimpleContext

class MyAgent(SimpleAgentBehavior):
    system_prompt = "You are a foraging agent. Collect apples."

    def decide(self, context: SimpleContext) -> str:
        # Just return a tool name - framework infers parameters
        if context.nearby_resources:
            return "move_to"
        return "idle"
```
**Focus**: Understanding the perception -> decision -> action loop

### Tier 2: Intermediate (AgentBehavior)
```python
from agent_runtime import AgentBehavior, Observation, AgentDecision, ToolSchema
from agent_runtime.memory import SlidingWindowMemory

class MyAgent(AgentBehavior):
    def __init__(self):
        self.memory = SlidingWindowMemory(capacity=50)

    def on_episode_start(self):
        self.memory.clear()

    def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
        self.memory.store(observation)
        if observation.nearby_resources:
            target = observation.nearby_resources[0]
            return AgentDecision(
                tool="move_to",
                params={"target_position": list(target.position)},
                reasoning=f"Moving to {target.name}"
            )
        return AgentDecision.idle()
```
**Focus**: State tracking, explicit parameters, memory patterns

### Tier 3: Advanced (LLMAgentBehavior)
```python
from agent_runtime import LLMAgentBehavior, Observation, AgentDecision, ToolSchema

class MyAgent(LLMAgentBehavior):
    def __init__(self):
        super().__init__(backend="anthropic", model="claude-3-haiku-20240307")
        self.system_prompt = "You are an intelligent foraging agent."

    def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
        context = self._format_observation(observation)
        response = self.complete(context)
        return self._parse_response(response, tools)
```
**Focus**: LLM reasoning, planning, multi-agent coordination

### What Users Control vs Framework Handles

| Aspect | Beginner | Intermediate | Advanced |
|--------|----------|--------------|----------|
| Return Type | Tool name (str) | AgentDecision | AgentDecision |
| Parameters | Framework infers | User specifies | User specifies |
| Memory | Automatic | User manages built-in | User implements custom |
| LLM Integration | Not needed | Optional | Core feature |
| Lifecycle Hooks | Not needed | Optional | Optional |

---

## Built C++ Classes

### SimulationManager (Node)
- Deterministic tick-based simulation controller
- Methods: `start_simulation()`, `stop_simulation()`, `step_simulation()`, `reset_simulation()`
- Properties: `current_tick`, `tick_rate`, `is_running`
- Signals: `simulation_started`, `simulation_stopped`, `tick_advanced(tick)`

### Agent (Node)
- Base agent class with perception, memory, and actions
- Methods: `perceive()`, `decide_action()`, `execute_action()`, `call_tool()`
- Memory: `store_memory()`, `retrieve_memory()`, `clear_short_term_memory()`
- Properties: `agent_id`
- Signals: `action_decided`, `perception_received`

### EventBus (RefCounted)
- Event recording and replay system
- Methods: `emit_event()`, `get_events_for_tick()`, `clear_events()`
- Recording: `start_recording()`, `stop_recording()`, `export_recording()`, `load_recording()`

### ToolRegistry (RefCounted)
- Tool management system for agent actions
- Methods: `register_tool()`, `unregister_tool()`, `get_tool_schema()`, `execute_tool()`

### IPCClient (Node)
- HTTP client for Godot <-> Python communication
- Methods: `connect_to_server()`, `send_tick_request()`, `get_tick_response()`, `has_response()`
- Properties: `server_url`
- Signals: `response_received`, `connection_failed`

---

## Future Directions

### Near-Term
- Complete initial benchmark scenarios (foraging, crafting_chain, team_capture)
- Build debugging/inspection tools (prompt viewer, step-through mode)
- Create quickstart tutorials for building your first agent

### Medium-Term
- Public leaderboards for scenario benchmarks
- Community scenario sharing
- A/B comparison tools for agent implementations
- Support for visual/multimodal observations (screenshots, rendered views)

### Long-Term
- Curriculum learning system (automatic difficulty progression)
- RL fine-tuning pipeline for agents
- Distributed evaluation for large-scale benchmarking
- Integration with popular agent frameworks (LangChain, AutoGPT patterns)

---

## Current Status
- Foraging scene fully working with Python agents (observation-decision loop)
- Three-tier learning system documented with full tutorials
- LLMAgentBehavior implemented (Anthropic, OpenAI, Ollama backends)
- Comprehensive learner docs in `docs/learners/` (16+ tutorial files)
- Example agents for each tier: SimpleForagerSimple, SimpleForager, LLMForager
- Next: additional benchmark scenes, end-to-end LLM testing
