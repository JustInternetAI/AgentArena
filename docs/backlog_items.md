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

## Total Backlog Summary

- **High Priority**: 7 items
- **Medium Priority**: 15 items
- **Low Priority**: 8 items
- **Total**: 30 items

**Estimated Timeline**: 6-12 months for all items with 2 developers
