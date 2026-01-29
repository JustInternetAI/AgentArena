# Backlog Items for Agent Arena

This document contains backlog items organized by priority and category. Use these to populate your GitHub Project Board.

---

## High Priority Backlog

### Backend & LLM Integration

#### B-1: vLLM Backend Integration
**Priority**: High
**Component**: Backends
**Size**: L

Support vLLM for faster batch inference.

**Tasks**:
- [ ] Research vLLM API and requirements
- [ ] Create `python/backends/vllm_backend.py`
- [ ] Implement BaseBackend interface
- [ ] Add config file `configs/backend/vllm.yaml`
- [ ] Add support for batch processing multiple agents
- [ ] Test with Llama-2 or Mistral models
- [ ] Document setup and usage

**Acceptance Criteria**:
- Can load models via vLLM
- Supports batch inference (multiple agents)
- Performance better than sequential llama.cpp
- Config-driven model selection

---

#### B-2: TensorRT-LLM Backend
**Priority**: Medium
**Component**: Backends
**Size**: XL

Ultra-fast inference with TensorRT optimization.

**Tasks**:
- [ ] Install TensorRT-LLM dependencies
- [ ] Create `python/backends/tensorrt_backend.py`
- [ ] Implement engine building/loading
- [ ] Support function calling
- [ ] Benchmark vs other backends
- [ ] Document GPU requirements

**Acceptance Criteria**:
- <100ms inference on RTX 4090
- Supports quantized models
- Works with Godot IPC

---

#### B-3: Model Download & Management
**Priority**: High
**Component**: Tools
**Size**: M

Automated model downloading and version management.

**Tasks**:
- [ ] Create `python/tools/model_manager.py`
- [ ] Support Hugging Face Hub downloads
- [ ] Verify model checksums
- [ ] Cache models in `models/` directory
- [ ] CLI tool: `python -m tools.model_manager download phi-2`
- [ ] List compatible models in README

**Acceptance Criteria**:
- Can download GGUF models from HF
- Verifies file integrity
- Shows download progress
- Lists available models

---

### Memory Systems

#### B-4: Long-Term Memory (Vector Store)
**Priority**: High
**Component**: Memory
**Size**: L

Implement RAG-based long-term memory with FAISS.

**Tasks**:
- [ ] Create `python/memory/long_term_memory.py`
- [ ] Integrate FAISS for vector storage
- [ ] Use sentence-transformers for embeddings
- [ ] Implement similarity search
- [ ] Support memory insertion/retrieval
- [ ] Add memory persistence (save/load)
- [ ] Create unit tests

**Acceptance Criteria**:
- Can store episode memories
- Top-K retrieval works
- Persists across sessions
- <50ms retrieval time

---

#### B-5: Episode Memory System
**Priority**: Medium
**Component**: Memory
**Size**: M

Store and summarize episode trajectories for learning.

**Tasks**:
- [ ] Create `python/memory/episode_memory.py`
- [ ] Store full episode trajectories
- [ ] Generate LLM-based episode summaries
- [ ] Index by success/failure
- [ ] Support episode replay
- [ ] Link to long-term memory

**Acceptance Criteria**:
- Episodes stored with metadata
- Can retrieve similar episodes
- Summaries are coherent
- Supports filtering by metrics

---

### Agent Tools

#### B-6: Advanced Movement Tools
**Priority**: Medium
**Component**: Tools
**Size**: M

Navigation, pathfinding, and advanced movement.

**Tasks**:
- [ ] Implement A* pathfinding in Godot
- [ ] Add `navigate_to` tool (vs simple move_to)
- [ ] Support obstacle avoidance
- [ ] Add `follow_path` tool
- [ ] Test in complex scenes
- [ ] Update tool schemas

**Acceptance Criteria**:
- Agents can navigate around obstacles
- Pathfinding works in all scenes
- Performance acceptable (< 10ms)

---

#### B-7: Inventory Management Tools
**Priority**: Medium
**Component**: Tools
**Size**: S

Complete inventory system for agents.

**Tasks**:
- [ ] Implement `pickup_item` tool
- [ ] Implement `drop_item` tool
- [ ] Implement `use_item` tool
- [ ] Add inventory capacity limits
- [ ] Track item properties (durability, etc.)
- [ ] Update perception with inventory state

**Acceptance Criteria**:
- Agents can manage inventory
- Capacity limits enforced
- Items have properties
- Works in crafting scene

---

#### B-8: Communication Tools
**Priority**: Medium
**Component**: Tools
**Size**: M

Enhanced agent-to-agent communication.

**Tasks**:
- [ ] Implement message broadcast
- [ ] Add message history
- [ ] Support team channels
- [ ] Add `query_messages` tool
- [ ] Track message metadata (sender, timestamp)
- [ ] Test in team capture scene

**Acceptance Criteria**:
- Agents can send/receive messages
- Messages persist in memory
- Team-based filtering works
- Demonstrates coordination

---

### Benchmark Scenes

#### B-9: Combat Arena Scene
**Priority**: Medium
**Component**: Scenes
**Size**: L

1v1 or team-based combat benchmark.

**Tasks**:
- [ ] Design combat mechanics
- [ ] Create scene in Godot
- [ ] Implement health/damage system
- [ ] Add weapon types
- [ ] Create combat tools (attack, defend, dodge)
- [ ] Track combat metrics
- [ ] Add GDScript logic

**Metrics**:
- Damage dealt/taken
- Win rate
- Survival time
- Hit accuracy

---

#### B-10: Navigation Maze Scene
**Priority**: Low
**Component**: Scenes
**Size**: M

Test pathfinding and exploration.

**Tasks**:
- [ ] Create maze layout
- [ ] Add waypoints/checkpoints
- [ ] Implement fog of war
- [ ] Track exploration metrics
- [ ] Add procedural generation (optional)

**Metrics**:
- Time to complete
- Exploration coverage
- Backtracking count
- Path efficiency

---

#### B-11: Multi-Agent Coordination Scene
**Priority**: High
**Component**: Scenes
**Size**: L

Complex task requiring tight coordination.

**Tasks**:
- [ ] Design coordination challenge (e.g., moving large objects)
- [ ] Implement synchronization requirements
- [ ] Add communication requirements
- [ ] Track coordination metrics
- [ ] Test with 3-5 agents

**Metrics**:
- Task completion time
- Communication frequency
- Individual contribution
- Synchronization score

---

### Evaluation & Metrics

#### B-12: Evaluation Harness
**Priority**: High
**Component**: Evals
**Size**: L

Automated benchmark running and metric collection.

**Tasks**:
- [ ] Create `python/evals/eval_harness.py`
- [ ] Support running multiple trials
- [ ] Collect metrics from all scenes
- [ ] Generate reports (JSON, CSV)
- [ ] Add visualization (plots, tables)
- [ ] Support comparison across models
- [ ] CLI: `python -m evals.run --scene foraging --trials 10`

**Acceptance Criteria**:
- Runs benchmarks automatically
- Collects all metrics
- Generates reports
- Supports multiple backends

---

#### B-13: Replay System
**Priority**: Medium
**Component**: Godot/C++
**Size**: M

Record and replay agent episodes deterministically.

**Tasks**:
- [ ] Implement replay recording in EventBus
- [ ] Export to MessagePack format
- [ ] Create replay loader
- [ ] Support playback in Godot
- [ ] Add replay viewer UI
- [ ] Test determinism

**Acceptance Criteria**:
- Episodes can be recorded
- Replays are deterministic
- Can view replays in Godot
- File format documented

---

### Performance & Optimization

#### B-14: Parallel Agent Processing
**Priority**: Medium
**Component**: Python/Runtime
**Size**: M

Process multiple agents in parallel for performance.

**Tasks**:
- [ ] Add async/await to AgentRuntime
- [ ] Implement thread pool for LLM inference
- [ ] Batch observations for multiple agents
- [ ] Optimize IPC for bulk messages
- [ ] Benchmark performance gains

**Acceptance Criteria**:
- Multiple agents process concurrently
- 2x+ speedup for 3+ agents
- No race conditions
- Works with all backends

---

#### B-15: Response Caching
**Priority**: Low
**Component**: Backends
**Size**: S

Cache LLM responses for identical contexts.

**Tasks**:
- [ ] Implement cache key generation
- [ ] Add LRU cache to backends
- [ ] Support cache invalidation
- [ ] Add cache hit/miss metrics
- [ ] Make cache size configurable

**Acceptance Criteria**:
- Identical contexts use cached responses
- Cache hit rate >30% in repetitive scenarios
- Configurable cache size
- No memory leaks

---

#### B-16: Profiling & Benchmarking Tools
**Priority**: Medium
**Component**: Tools
**Size**: M

Tools for performance analysis.

**Tasks**:
- [ ] Add timing decorators
- [ ] Create profiling scripts
- [ ] Measure IPC latency
- [ ] Measure LLM inference time
- [ ] Generate performance reports
- [ ] Add flamegraphs

**Acceptance Criteria**:
- Can profile Python code
- Identifies bottlenecks
- Reports are readable
- Actionable insights

---

## Medium Priority Backlog

### Documentation & Tutorials

#### B-17: Video Tutorials
**Priority**: Low
**Component**: Documentation
**Size**: L

Create video walkthroughs.

**Content**:
- [ ] Installation and setup
- [ ] Creating a custom scene
- [ ] Adding a new tool
- [ ] Implementing a backend
- [ ] Running benchmarks

---

#### B-18: API Reference Documentation
**Priority**: Medium
**Component**: Documentation
**Size**: M

Auto-generated API docs.

**Tasks**:
- [ ] Set up Sphinx for Python
- [ ] Set up Doxygen for C++
- [ ] Auto-generate from docstrings
- [ ] Host on GitHub Pages
- [ ] Add examples to docs

---

#### B-19: Cookbook & Examples
**Priority**: Medium
**Component**: Documentation
**Size**: M

Practical examples and recipes.

**Examples**:
- [ ] Custom tool implementation
- [ ] Memory system usage
- [ ] Multi-agent coordination
- [ ] Custom scene creation
- [ ] Backend customization

---

### Testing & Quality

#### B-20: Integration Test Suite
**Priority**: High
**Component**: Testing
**Size**: L

Comprehensive integration tests.

**Tests**:
- [ ] Godot ↔ Python IPC
- [ ] Full agent decision loop
- [ ] All benchmark scenes
- [ ] Memory persistence
- [ ] Tool execution
- [ ] Error handling

---

#### B-21: CI/CD Pipeline
**Priority**: High
**Component**: DevOps
**Size**: L

Automated testing and deployment.

**Tasks**:
- [ ] Set up GitHub Actions
- [ ] Run Python tests on PR
- [ ] Build C++ module on PR
- [ ] Run integration tests
- [ ] Generate coverage reports
- [ ] Auto-deploy docs

---

#### B-22: Linting & Code Quality
**Priority**: Medium
**Component**: Quality
**Size**: S

Enforce code standards automatically.

**Tasks**:
- [ ] Add pre-commit hooks
- [ ] Configure Black, Ruff
- [ ] Add C++ clang-format
- [ ] Run in CI/CD
- [ ] Update CONTRIBUTING.md

---

### Advanced Features

#### B-23: Multi-Modal Support (Vision)
**Priority**: Low
**Component**: Features
**Size**: XL

Add vision encoder for visual observations.

**Tasks**:
- [ ] Integrate CLIP or similar
- [ ] Capture screenshots from Godot
- [ ] Process images in Python
- [ ] Pass to LLM as vision input
- [ ] Test with vision-capable models

---

#### B-24: RL Fine-Tuning Pipeline
**Priority**: Low
**Component**: Features
**Size**: XL

Reinforcement learning for agent improvement.

**Tasks**:
- [ ] Collect trajectory data
- [ ] Implement PPO/DPO
- [ ] Fine-tune on successful episodes
- [ ] Evaluate performance gains
- [ ] Document training process

---

#### B-25: Distributed Simulation
**Priority**: Low
**Component**: Infrastructure
**Size**: XL

Run multiple simulations in parallel.

**Tasks**:
- [ ] Design distributed architecture
- [ ] Support multiple Godot instances
- [ ] Aggregate results
- [ ] Scale evaluation throughput
- [ ] Deploy on cloud (optional)

---

## Low Priority / Future Ideas

#### B-26: Web Dashboard
**Priority**: Low
**Component**: UI
**Size**: L

Web interface for monitoring and control.

**Features**:
- Real-time metrics
- Agent visualization
- Benchmark results
- Configuration management

---

#### B-27: Custom Scene Builder
**Priority**: Low
**Component**: Tools
**Size**: XL

GUI tool for creating benchmark scenes.

**Features**:
- Drag-and-drop scene editor
- Resource placement
- Metric configuration
- Export to .tscn

---

#### B-28: Agent Behavior Trees
**Priority**: Low
**Component**: Features
**Size**: L

Alternative to LLM for deterministic behaviors.

**Features**:
- Behavior tree editor
- Hybrid LLM + BT agents
- Fallback behaviors

---

#### B-29: Competition Mode
**Priority**: Low
**Component**: Features
**Size**: M

Leaderboard and agent competition.

**Features**:
- Submit agent implementations
- Automated tournaments
- Global leaderboard
- Prize competitions (optional)

---

#### B-30: Mobile Support
**Priority**: Low
**Component**: Platform
**Size**: XL

Run benchmarks on mobile devices.

**Tasks**:
- [ ] Android/iOS Godot export
- [ ] Optimize for mobile
- [ ] On-device LLM inference
- [ ] Touch controls

---

---

#### B-31: LocalLLMBehavior - Bridge Local Backends to AgentBehavior API ✅ COMPLETE
**Priority**: High
**Component**: Agent Runtime / Backends
**Size**: M
**Blocking**: LLM agent integration with foraging scene
**Status**: Completed - see [python/agent_runtime/local_llm_behavior.py](../python/agent_runtime/local_llm_behavior.py)

**Problem Statement**:
The codebase has two separate agent systems that aren't connected:

1. **AgentBehavior system** (`python/agent_runtime/behavior.py`)
   - Classes: `AgentBehavior`, `SimpleAgentBehavior`, `LLMAgentBehavior`
   - Used by: IPC server's `/observe` endpoint via `server.behaviors` dict
   - Learner-facing API with three tiers (beginner/intermediate/advanced)

2. **Local LLM Backend system** (`python/backends/`)
   - Classes: `LlamaCppBackend`, `VLLMBackend`
   - Used by: `run_ipc_server_with_gpu.py` via `Agent` class
   - GPU-accelerated local inference

**Current Flow (Broken)**:
```
Godot foraging scene
    ↓ POST /observe (sends observation)
python/ipc/server.py line 424-475
    ↓ checks server.behaviors dict → EMPTY
    ↓ falls back to mock rule-based logic
    (LlamaCppBackend never gets called)
```

**Goal**: Create `LocalLLMBehavior` class that wraps local backends (LlamaCppBackend, VLLMBackend) and implements the `AgentBehavior` interface, so local LLMs can power agents via the `/observe` endpoint.

---

**Architecture Context**:

The IPC server (`python/ipc/server.py`) has a `behaviors` dict that maps `agent_id → AgentBehavior`. When `/observe` receives an observation:
- Line 424-426: Gets agent_id from observation
- Line 427: Checks `behavior = self.behaviors.get(agent_id)`
- Line 428-471: If behavior exists, calls `behavior.decide(observation, tools)`
- Line 472-475: If no behavior, falls back to `_make_mock_decision()`

The `LLMAgentBehavior` class (line 281-422 in behavior.py) already supports cloud LLMs (Anthropic, OpenAI, Ollama) but NOT the local backends (LlamaCppBackend, VLLMBackend).

---

**Files to Understand First**:

1. `python/agent_runtime/behavior.py` - Base classes, especially `LLMAgentBehavior`
2. `python/backends/base.py` - `BaseBackend` interface with `generate()` and `generate_with_tools()`
3. `python/backends/llama_cpp_backend.py` - Local GPU inference implementation
4. `python/backends/vllm_backend.py` - vLLM server client
5. `python/ipc/server.py` - See `/observe` endpoint (line 397-493) and `create_server()` function
6. `python/user_agents/examples/llm_forager.py` - Example of LLMAgentBehavior subclass
7. `python/scenarios/foraging.py` - Scenario definition with `to_system_prompt()` method

---

**Implementation Tasks**:

- [x] **Create `python/agent_runtime/local_llm_behavior.py`**

  ```python
  """
  Local LLM behavior adapter.

  Bridges the AgentBehavior interface to local LLM backends
  (LlamaCppBackend, VLLMBackend) for GPU-accelerated inference.
  """

  from agent_runtime.behavior import AgentBehavior
  from agent_runtime.schemas import AgentDecision, Observation, ToolSchema
  from backends.base import BaseBackend

  class LocalLLMBehavior(AgentBehavior):
      """
      AgentBehavior implementation using local LLM backends.

      This bridges the learner-facing AgentBehavior API to the
      high-performance local backends (llama.cpp, vLLM).

      Example:
          from backends import LlamaCppBackend, BackendConfig
          from agent_runtime.local_llm_behavior import LocalLLMBehavior

          config = BackendConfig(model_path="models/llama.gguf", n_gpu_layers=-1)
          backend = LlamaCppBackend(config)

          behavior = LocalLLMBehavior(
              backend=backend,
              system_prompt="You are a foraging agent..."
          )

          # Register with IPC server
          server = create_server(behaviors={"agent_001": behavior})
      """

      def __init__(
          self,
          backend: BaseBackend,
          system_prompt: str = "",
          temperature: float = 0.7,
          max_tokens: int = 256,
      ):
          self.backend = backend
          self.system_prompt = system_prompt
          self.temperature = temperature
          self.max_tokens = max_tokens
          self._memory: list[Observation] = []
          self._memory_capacity = 10

      def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
          """Use local LLM to decide next action."""
          # 1. Store observation in memory
          # 2. Build prompt from system_prompt + observation + tools
          # 3. Call backend.generate_with_tools() or backend.generate()
          # 4. Parse response into AgentDecision
          # 5. Handle errors gracefully (return idle on failure)
          pass

      def _build_prompt(self, observation: Observation, tools: list[ToolSchema]) -> str:
          """Build the prompt for the LLM."""
          # Include: system prompt, current observation, available tools, memory
          pass

      def _parse_response(self, response: str, tools: list[ToolSchema]) -> AgentDecision:
          """Parse LLM response into AgentDecision."""
          # Handle JSON parsing, validate tool names, extract params
          pass

      def on_episode_start(self) -> None:
          """Clear memory at episode start."""
          self._memory.clear()
  ```

- [x] **Add factory function for easy creation**

  ```python
  def create_local_llm_behavior(
      model_path: str,
      backend_type: str = "llama_cpp",  # or "vllm"
      n_gpu_layers: int = -1,
      system_prompt: str = "",
      **kwargs
  ) -> LocalLLMBehavior:
      """Factory to create LocalLLMBehavior with backend."""
      pass
  ```

- [x] **Update `python/ipc/server.py` `create_server()` function** (line 520-541)

  Add optional parameter to auto-create local LLM behavior:
  ```python
  def create_server(
      runtime: AgentRuntime | None = None,
      behaviors: dict | None = None,
      host: str = "127.0.0.1",
      port: int = 5000,
      default_behavior: AgentBehavior | None = None,  # NEW: fallback for unknown agents
  ) -> IPCServer:
  ```

- [x] **Create `python/run_local_llm_forager.py`** - Startup script

  ```python
  """
  Run foraging scene with local LLM agent.

  Usage:
      python run_local_llm_forager.py --model models/llama.gguf --gpu-layers -1
  """

  # 1. Load local backend (LlamaCppBackend or VLLMBackend)
  # 2. Create LocalLLMBehavior with foraging system prompt
  # 3. Register behavior for agent_id matching Godot scene
  # 4. Start IPC server
  ```

- [ ] **Integrate scenario system prompts** (deferred - optional enhancement)

  Use `python/scenarios/foraging.py` to generate system prompts:
  ```python
  from scenarios import get_scenario

  scenario = get_scenario("foraging")
  system_prompt = scenario.to_system_prompt(include_hints=True)
  behavior = LocalLLMBehavior(backend=backend, system_prompt=system_prompt)
  ```

- [x] **Add to `__init__.py` exports**

  Update `python/agent_runtime/__init__.py` to export `LocalLLMBehavior`

- [x] **Write tests**

  Create `tests/test_local_llm_behavior.py`:
  - Test prompt building
  - Test response parsing (valid JSON, invalid JSON, missing fields)
  - Test tool validation
  - Test memory management
  - Mock backend for unit tests

---

**Reference: How LLMAgentBehavior works** (for comparison):

```python
# From behavior.py lines 321-338
def complete(self, prompt: str, system: str | None = None, temperature: float = 0.7) -> str:
    if self._client is None:
        self._client = self._create_client()
    sys_prompt = system if system is not None else self.system_prompt
    return self._call_llm(prompt, sys_prompt, temperature)

# _call_llm handles Anthropic/OpenAI/Ollama APIs
```

LocalLLMBehavior should follow similar pattern but call:
```python
result = self.backend.generate_with_tools(prompt, tools_as_dicts, temperature)
# or
result = self.backend.generate(prompt, temperature, max_tokens)
```

---

**Reference: Backend API** (from `backends/base.py`):

```python
class BaseBackend(ABC):
    @abstractmethod
    def generate(self, prompt: str, temperature: float | None, max_tokens: int | None) -> GenerationResult:
        pass

    @abstractmethod
    def generate_with_tools(self, prompt: str, tools: list[dict], temperature: float | None) -> GenerationResult:
        pass

@dataclass
class GenerationResult:
    text: str
    tokens_used: int
    finish_reason: str
    metadata: dict[str, Any]
```

---

**Agent ID Matching**:

The Godot foraging scene uses `SimpleAgent` which has an `agent_id` property:
- If set in scene: uses that value
- If empty: auto-generates `"agent_" + timestamp`

For testing, either:
1. Set `agent_id = "forager_001"` in the Godot scene's SimpleAgent node
2. OR use a wildcard/default behavior in the server

Recommend option 1 for explicit control.

---

**Acceptance Criteria**:

- [ ] `LocalLLMBehavior` implements full `AgentBehavior` interface
- [ ] Works with both `LlamaCppBackend` and `VLLMBackend`
- [ ] Integrates with scenario system prompts (`to_system_prompt()`)
- [ ] `run_local_llm_forager.py` successfully runs foraging scene with local LLM
- [ ] Agent makes reasonable decisions (moves to resources, avoids hazards)
- [ ] Graceful error handling (returns idle on LLM failures)
- [ ] All tests pass
- [ ] Pre-commit hooks pass (black, ruff, mypy)

---

**Testing Instructions**:

1. Download a GGUF model (e.g., `llama-2-7b-chat.Q4_K_M.gguf`)
2. Run: `python run_local_llm_forager.py --model path/to/model.gguf`
3. Open Godot and run the foraging scene
4. Observe agent behavior in console logs
5. Verify decisions are LLM-generated (not mock logic)

---

**Related Files Summary**:

| File | Purpose |
|------|---------|
| `python/agent_runtime/behavior.py` | Base classes to extend |
| `python/backends/llama_cpp_backend.py` | Local GPU backend |
| `python/backends/vllm_backend.py` | vLLM server backend |
| `python/backends/base.py` | Backend interface |
| `python/ipc/server.py` | IPC server with /observe endpoint |
| `python/scenarios/foraging.py` | System prompt source |
| `python/user_agents/examples/llm_forager.py` | Reference implementation |
| `scripts/simple_agent.gd` | Godot agent (sends agent_id) |
| `scripts/base_scene_controller.gd` | Sends observations to /observe |

---

#### B-32: Tier 3 Memory Inspection API
**Priority**: Medium
**Component**: Agent Runtime
**Size**: S
**Depends On**: B-31 (LocalLLMBehavior)

**Problem Statement**:
Advanced learners need to inspect and debug agent memory contents. Currently there's no standardized way to view what's stored in memory, query it externally, or export it for analysis.

**Goal**: Provide memory inspection tools for Tier 3 learners.

**Implementation Tasks**:
- [ ] Add `memory.dump()` method to `AgentMemory` interface
- [ ] Add `memory.query(query: str)` for semantic retrieval
- [ ] Create CLI tool: `python -m tools.inspect_agent --memory`
- [ ] Add memory export to JSON/CSV formats
- [ ] Document memory inspection in learner_tiers.md

**Acceptance Criteria**:
- [ ] Learners can view full memory contents
- [ ] Learners can search memory by query
- [ ] Export works for analysis in external tools

---

#### B-33: Tier 3 Reasoning Trace System
**Priority**: Medium
**Component**: Agent Runtime
**Size**: M
**Depends On**: B-31 (LocalLLMBehavior)

**Problem Statement**:
Advanced learners need to understand step-by-step how their agent made decisions. They need to see: what was retrieved from memory, what prompt was sent, what the LLM responded, and how that was parsed into a decision.

**Goal**: Provide a reasoning trace system that logs every step of the decision process.

**Implementation Tasks**:
- [ ] Add `ReasoningTrace` class to track decision steps
- [ ] Add `log_step(name, data)` method to AgentBehavior
- [ ] Store traces per-episode with timestamps
- [ ] Create CLI tool: `python -m tools.inspect_agent --last-decision`
- [ ] Create CLI tool: `python -m tools.inspect_agent --watch` (live mode)
- [ ] Add trace visualization (text-based tree view)
- [ ] Document in learner_tiers.md

**Acceptance Criteria**:
- [ ] Each decision step is logged with timestamp and data
- [ ] Learners can replay full decision traces
- [ ] Live watching mode shows decisions as they happen

---

#### B-34: Tier 3 Reflection Hooks
**Priority**: Medium
**Component**: Agent Runtime
**Size**: M
**Depends On**: B-31, B-32, B-33

**Problem Statement**:
Advanced learners want agents that learn from experience. They need hooks to reflect on episode outcomes, store insights, and use those insights in future decisions.

**Goal**: Provide reflection hooks that enable learning from past episodes.

**Implementation Tasks**:
- [ ] Add `on_episode_end(outcome: dict)` hook to AgentBehavior
- [ ] Add `reflect(outcome) -> str` method to LLMAgentBehavior
- [ ] Add `self.reflections` storage for past insights
- [ ] Integrate reflections into prompt building
- [ ] Create example: `ReflectiveForager` in user_agents/examples/
- [ ] Add reflection viewer to CLI tools
- [ ] Document reflection patterns in learner_tiers.md

**Acceptance Criteria**:
- [ ] Agents can reflect on episode outcomes using LLM
- [ ] Reflections are stored and can be retrieved
- [ ] Reflections improve future decision-making
- [ ] Clear documentation with examples

---

## Total Backlog Summary

- **High Priority**: 8 items
- **Medium Priority**: 18 items
- **Low Priority**: 8 items
- **Total**: 34 items

**Estimated Timeline**: 6-12 months for all items with 2 developers
