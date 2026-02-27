# Framework Integration Strategy

**Date:** 2026-02-22
**Status:** Proposed
**Authors:** Justin, Claude (architecture review session)

---

## Context

After a thorough review of Agent Arena's codebase, we assessed the project against three goals:

1. **Learning about AI** — developing real skills in agentic AI systems
2. **Building AI systems** — growing as engineers who can build AI products
3. **Benefiting others** — creating something the broader community can use

The review revealed that ~80% of development time has gone into infrastructure (C++ GDExtension, Godot scene logic, IPC protocols, GDScript) while ~20% has been AI-focused work. The infrastructure is now largely in place — the foraging scenario works end-to-end, the SDK is clean, and LLM integration is functional. But a significant portion of the Python-side AI code duplicates what mature agent frameworks (LangGraph, Claude Agent SDK, CrewAI, etc.) already provide.

This document captures the strategic shift: **stop building generic agent infrastructure, focus on what only Agent Arena can provide, and let frameworks handle the rest.**

---

## The Value Proposition

### What We're NOT

We're not a "bring your existing agent and test it here" platform. Nobody has a LangGraph agent sitting around that knows how to forage in a 3D world. That framing targets an audience that doesn't exist.

### What We ARE

**"Want to learn LangGraph? Build an AI agent that plays a game."**

Agent Arena is a **structured, visual environment for learning agent frameworks by building something real.** Every framework has "build a chatbot" or "build a RAG pipeline" tutorials. Those are text-in/text-out, stateless, toy-scale. Agent Arena gives learners:

- **Visual feedback** — watch your agent walk into fire and learn from it
- **Stateful decisions** — memory matters, planning matters
- **Progressive complexity** — foraging is easy, crafting chains require real planning
- **Measurable skill** — your score goes up as your agent gets smarter

The user journey:
1. "I want to learn LangGraph" — picks Agent Arena as their practice project
2. Opens the LangGraph starter — a tutorial that teaches LangGraph concepts
3. Learns tool definition, state management, prompting — all LangGraph skills
4. Iterates against the foraging scenario — sees the agent succeed or fail visually
5. Graduates to harder scenarios (crafting chains, multi-agent coordination)
6. Walks away knowing LangGraph from building something real, not reading docs

This means **framework starters are the product, not just adapters**. They need to be well-written tutorials with comments explaining framework concepts, not just boilerplate.

---

## The Core Insight

Agent Arena is trying to be both the **gym** (scenarios, physics, observations, scoring) and the **agent** (LLM calls, memory, prompts, tool calling). The gym is unique and valuable. The agent infrastructure is commodity code that frameworks do better.

### What We've Built vs. What Frameworks Provide

#### We Should Stop Building (Frameworks Handle This)

| Component | Our Code | Framework Equivalent |
|-----------|----------|---------------------|
| SlidingWindowMemory | `python/agent_runtime/memory/sliding_window.py` | LangChain ConversationBufferMemory, LangGraph checkpointers |
| LLM client wrappers | `starters/llm/llm_client.py` | LangChain LLM integrations (50+ providers) |
| Backend adapters | `python/backends/llama_cpp_backend.py`, `vllm_backend.py` | LangChain LlamaCpp, VLLM, LiteLLM |
| Tool registration + JSON schemas | `python/tools/__init__.py` | OpenAI function calling, LangChain @tool, Claude tool_use |
| Prompt templates | `starters/llm/prompts/` | LangChain PromptTemplate, framework prompt systems |
| Basic observability | TraceStore prompt/response logging | LangSmith, Anthropic Console, Helicone |

#### We Should Keep and Invest In (Only We Provide This)

| Component | Why It's Unique |
|-----------|----------------|
| **SpatialMemory** | Grid-based 3D spatial index with object lifecycle tracking, staleness, proximity queries. No agent framework has this. |
| **EpisodeMemoryManager** | Detects episode boundaries from tick resets, identifies key game events (resource clusters, damage), stores summaries with deduplication. Simulation-native. |
| **Observation schema** | `nearby_resources`, `nearby_hazards`, `nearby_stations`, `exploration` with frontiers, `perception_radius` — the game world's API to the agent. |
| **WorldObject / ExperienceEvent** | Object status tracking (active/collected/destroyed), collision events, damage history — game simulation primitives. |
| **ScenarioDefinition + Objectives** | Goals, constraints, weighted metrics, success criteria — game design tooling. |
| **Three-tier learning progression** | SimpleAgentBehavior → AgentBehavior → LLMAgentBehavior with parameter inference. Pedagogical framework. |
| **Game-specific tools** | `move_to`, `collect`, `craft_item`, `explore_direction` — the environment's action space. |
| **Game-side inspector** | Episode replay, spatial context, outcome tracking — what happened in the world. |

---

## New Architecture

### Before (Monolithic)

```
Agent Arena owns everything:
  Godot ↔ IPC ↔ Python Agent Runtime ↔ LLM Backends
                     ↑
              (all our code)
```

### After (Layered with Three Categories)

```
┌─────────────────────────────────────────────────────────┐
│  FRAMEWORK LAYER (not our code)                         │
│  LangGraph, Claude SDK, CrewAI, OpenAI SDK              │
│  → LLM calls, prompts, basic memory, observability      │
├─────────────────────────────────────────────────────────┤
│  AGENT ARENA INTERFACE (our unique value)               │
│                                                         │
│  CONTEXT (injected into prompt — free, always present)  │
│  Position, health, energy, nearby resources/hazards,    │
│  inventory, exploration %, current objective             │
│                                                         │
│  QUERY TOOLS (resolved in Python — free, multiple OK)   │
│  query_spatial_memory    recall_location                 │
│  get_episode_summary     get_recipes                    │
│  get_experiences                                        │
│                                                         │
│  ACTION TOOLS (sent to Godot — costs a tick, pick ONE)  │
│  move_to    collect    craft_item    explore    idle     │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  GAME ENGINE (our infrastructure)                       │
│  Godot scenes, physics, IPC, observations,              │
│  scoring, episode management                            │
└─────────────────────────────────────────────────────────┘
```

### The Key Design Decision: Three Categories, Not One

Game information falls into three distinct categories with different costs and constraints. Treating them all as tools would confuse the LLM and waste tokens/latency. Instead:

**1. Context (injected into the prompt — not tools)**

The current tick's observation is formatted and pushed into the LLM's prompt automatically by the adapter. The agent always sees this for free, no tool call required. This is what the agent "perceives" each tick:

```
Position: (5.2, 0, 8.1)  |  Health: 80  |  Energy: 100
Nearby: berry at (10,0,5) dist=4.2, fire at (2,0,1) dist=3.0
Inventory: wood x2, stone x1
Explored: 45%  |  Frontier: north, east
Objective: collect 10 resources (current: 4/10)
```

Every framework can handle this — it's just text in the system message or user message.

**2. Query Tools (resolved in Python — lightweight, multiple per tick)**

Optional tools the agent can call to dig deeper before deciding. These resolve instantly in the Python process — no IPC round-trip to Godot. The agent can call as many as needed:

```python
query_spatial_memory(position=[10,0,5], radius=20)  → remembered objects near that area
recall_location("workbench")                         → last known position of a workbench
get_episode_summary()                                → key events from previous episodes
get_recipes()                                        → available crafting recipes
get_experiences()                                    → recent collision/damage events
```

**3. Action Tools (sent to Godot — heavyweight, exactly one per tick)**

The agent's final decision. Costs a tick. Pick exactly one. Goes to Godot via IPC:

```python
move_to(target_position=[10, 0, 5])
collect(target="berry")
craft_item(recipe="torch")
explore(direction="north")
idle()
```

### How This Plays Out Per Tick

```
Godot sends observation via IPC
        │
        ▼
┌─ PHASE 1: Context ──────────────────────────┐
│  Adapter formats observation into prompt.    │
│  Agent sees everything for free. No cost.    │
└──────────┬───────────────────────────────────┘
           ▼
┌─ PHASE 2: Reasoning (optional) ─────────────┐
│  LLM thinks, optionally calls query tools:   │
│    → query_spatial_memory(...)  → instant    │
│    → get_recipes()             → instant    │
│  Loops until LLM is ready to act.            │
│  (All resolved in Python, no Godot IPC)      │
└──────────┬───────────────────────────────────┘
           ▼
┌─ PHASE 3: Action (exactly one) ─────────────┐
│  LLM calls ONE action tool:                  │
│    → move_to([10, 0, 5])                    │
│  Adapter detects action tool, returns it     │
│  as the Decision. Tick ends.                 │
└──────────┬───────────────────────────────────┘
           ▼
SDK sends Decision to Godot via IPC
```

This maps naturally to how every framework works — ReAct-style agents reason and call tools in a loop, then produce a final action. The adapter just needs to know which tools are "terminal" (actions) vs "informational" (queries).

### Why Not "Everything Is a Tool"?

Making observations into tools would mean:
- **Wasted latency**: LLM burns a round-trip calling `get_nearby_resources()` for info it could have been given for free in the prompt
- **Wasted tokens**: Every query tool call costs input/output tokens
- **Confused LLM**: No way to distinguish "call this to gather info" from "call this to act" without relying on descriptions alone
- **Slower ticks**: Multiple LLM round-trips per tick instead of one-shot for simple decisions

The three-category approach means simple agents (beginner) can read the context and return one action with zero tool calls. Advanced agents (LLM) can query memory and plan before acting. Both work efficiently.

### Framework Adapters

The adapter per framework handles all three categories:

```python
class FrameworkAdapter(ABC):
    def decide(self, observation: Observation) -> Decision:
        # 1. Format observation as context (prompt text — framework-specific)
        # 2. Register query tools (resolved locally in Python)
        # 3. Register action tools (descriptions say "this ends your turn")
        # 4. Run framework agent loop
        # 5. When an action tool is called, capture it as Decision and stop
```

Adapters are still thin (~50-100 lines) because the heavy logic (context formatting, tool resolution, action detection) is shared in a base class. Per-framework code is just wrapping tools in the right format:

```
LangGraph:  StructuredTool.from_function(...)     # ~10 lines
Claude SDK: {"name": ..., "input_schema": ...}    # ~5 lines
OpenAI SDK: Native function calling format        # ~3 lines
CrewAI:     Uses LangChain tools underneath        # Same as LangGraph
```

---

## Inspector Strategy

### Current State

The inspector (TraceStore/ReasoningTrace) captures the full LLM pipeline:
Observation → Prompt → LLM request → Response → Decision

### Problem

With framework adapters, we no longer control the LLM call. Frameworks own prompts, LLM requests, and responses.

### Solution: Split Into Two Layers

**Game-side inspector (ours):**
- What the agent perceived each tick
- Which tools were called, with what params, what result
- Episode boundaries and game events
- Outcomes (score, damage, resources)
- Spatial context ("remembered berries from 30 ticks ago")

**LLM-side inspector (framework's):**
- Full prompts and responses
- Token counts, latency, cost
- Model reasoning / chain-of-thought
- Accessed via LangSmith, Anthropic Console, etc.

**Bridge between them:**
- Each tick in our inspector stores a link to the framework's trace
- Click a tick → opens the LLM reasoning for that exact decision
- Neither tool provides this cross-layer view alone

---

## Implementation Roadmap

### Phase 1: Enable Pure AI Development (Issues #70-73) — MOSTLY COMPLETE

| Issue | Title | Status |
|-------|-------|--------|
| #70 | Onboarding guide with screenshots | **Done** |
| #71 | Tool completion callbacks (Godot → Python) | **Done** |
| #72 | Mock observations for local testing | **Done** — `agent_arena_sdk.testing` module with mock factories, MockArena, and eval harness (`starters/llm/eval_agent.py`) |
| #73 | Complete intermediate starter | Open |

### Phase 2: Framework Starters (Issue #74) — IN PROGRESS

Each framework starter is a **tutorial for that framework**, not just a template. It teaches framework concepts (tool definition, state management, memory, prompting) through the lens of building a game-playing agent.

```
starters/
  beginner/          # No framework — raw decide(), learning fundamentals
  intermediate/      # No framework — manual memory + planning, learning patterns
  claude/            # Learn Claude tool_use by building a foraging agent (DONE)
  langchain/         # Learn LangGraph by building a foraging agent (planned)
  openai-sdk/        # Learn OpenAI function calling by building a foraging agent (planned)
```

| Step | Work | Status |
|------|------|--------|
| Define adapter interface | `FrameworkAdapter` ABC, tool schema export | **Done** (#74) |
| First framework starter | Claude starter with native tool_use | **Done** (#74) |
| Second framework starter | LangGraph (#84) | Open |

**Completed infrastructure:**
- `FrameworkAdapter` ABC in `python/sdk/agent_arena_sdk/adapters/base.py`
- Shared utilities: `format_observation()`, `get_action_tools()`, `fallback_decision()`
- `ToolSchema.to_anthropic_format()` and `to_openai_format()` for cross-framework tool definitions
- `python/backends/` directory deleted (#80) — frameworks handle LLM communication
- SDK schemas consolidated to single source of truth (#78)

### Phase 3: Refactor to New Architecture (Issue #75 + cleanup)

| Step | Work | Status |
|------|------|--------|
| Refactor inspector | Game-side only, add framework trace linking (#75) | Open |
| Build observation formatter | `format_observation()` in FrameworkAdapter base | **Done** |
| Expose SpatialMemory as query tool | `query_spatial_memory()`, `recall_location()` (#86) | Open |
| Expose EpisodeMemory as query tool | `get_episode_summary()`, `get_experiences()` (#86) | Open |
| Migrate SpatialMemory to SDK | Standalone module in SDK (#85) | Open |
| Tag action tools as terminal | Adapter base class detects action tools and stops the loop | Open |
| Remove redundant code | Delete backends/ | **Done** (#80) |

### Phase 4: Polish and Launch

| Step | Work | Status |
|------|------|--------|
| Additional framework starters | LangGraph (#84), OpenAI SDK | Open |
| Evaluation harness | Benchmark agents across frameworks — refactor eval_agent.py to test adapters directly | Open |
| Community docs | Contribution guide for new framework starters | Open |
| Package SDK for pip | pyproject.toml (#79) | Open |
| Episode lifecycle protocol | Start/end/restart/chaining (#81) | Open |

---

## What This Means for Justin and Andrew

### Justin (Infrastructure)
- Phases 1 and 2 are your focus — finish the infra, build adapters
- Phase 3 cleanup (removing old code, refactoring inspector)
- New scenes and scenarios

### Andrew (AI Development)
- After Phase 1: can focus purely on AI agent logic against foraging
- Phase 2: build framework starters — learn LangGraph/Claude SDK by writing the tutorials
- Phase 3: build out SpatialMemory and EpisodeMemory as rich, queryable tools
- Ongoing: prompt engineering, memory architectures, planning strategies, multi-agent coordination

### Both
- Evaluation harness — defining what "good" looks like across scenarios
- New scenarios that test specific AI capabilities (planning, memory, coordination)

---

## Success Criteria

1. A developer who wants to learn LangGraph can open the LangGraph starter and have an agent running in <15 minutes
2. Each framework starter teaches that framework's core concepts (tools, state, memory, prompting) through commented, tutorial-quality code
3. Agent Arena's unique tools (spatial memory, episode memory, game queries) work with any framework
4. The inspector shows game-side context that no framework provides, with links to framework traces
5. ~~The `python/backends/` directory is deleted — frameworks handle all LLM communication~~ **Done** (#80)
6. At least 2 framework starters with tutorial-quality documentation (1/2 — Claude starter done)

---

## Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Framework API breaking changes | High | Pin versions, keep adapters thin (<150 lines), community can contribute fixes |
| LLM calls too many query tools per tick (slow/expensive) | Medium | Context injection gives the agent most info for free; query tools are optional for deeper investigation. Starter tutorials teach when to use queries vs. rely on context. |
| Losing control over LLM interaction hurts debugging | Medium | Framework trace linking bridges the gap; LangSmith is actually more powerful than our inspector |
| LLM can't distinguish query vs action tools | Low | Action tool descriptions explicitly say "this ends your turn"; adapter enforces exactly-one-action constraint and stops the loop |
| Users don't want to learn a framework just to try Agent Arena | Low | Keep the beginner starter as-is (no framework required). Frameworks are opt-in for intermediate/advanced. |
| Framework starters become stale as frameworks evolve | Medium | Pin framework versions, keep starters focused on stable core APIs, community can submit updates |
| Tutorial quality is hard to maintain across frameworks | Medium | Start with 1-2 frameworks done well rather than 4 done poorly. Quality over breadth. |

---

## References

- Issue #70: Onboarding guide
- Issue #71: Tool completion callbacks
- Issue #72: Mock observations and local testing
- Issue #73: Complete intermediate starter
- Issue #74: Framework adapter system
- Issue #75: Inspector refactor
- Issue #76: Persistent cross-episode memory (agent learning across runs)
- Issue #60: LDX refactor (completed — established SDK pattern)
- Issue #61: Documentation update for LDX architecture
