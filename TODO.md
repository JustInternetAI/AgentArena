# Agent Arena - TODO & Roadmap

Track progress on major features and tasks.

## 🔥 Immediate Next Steps

- [ ] Clone and build godot-cpp dependency
  ```bash
  scripts\setup_godot_cpp.bat
  ```

- [ ] Build C++ module
  ```bash
  cd godot
  mkdir build
  cd build
  cmake ..
  cmake --build . --config Release
  ```

- [ ] Download LLM model
  - Get Llama 2 7B Q4 GGUF or similar
  - Place in `models/` directory
  - Update `configs/backend/llama_cpp.yaml`

- [ ] Test Python runtime
  ```bash
  cd python
  python -m venv venv
  venv\Scripts\activate
  pip install -r requirements.txt
  pytest ../tests/ -v
  ```

## 🚧 Phase 1: Foundation (Week 1-2)

### C++ Module
- [ ] Verify GDExtension compiles and loads in Godot
- [ ] Test SimulationManager tick loop
- [ ] Test EventBus recording/replay
- [ ] Add unit tests for C++ classes (if possible)

### Python Runtime
- [ ] Test Agent class with mock backend
- [ ] Test ToolDispatcher execution
- [ ] Verify llama.cpp backend loads model
- [ ] Test all tool functions

### Integration
- [ ] Design IPC protocol (gRPC vs HTTP vs shared memory)
- [ ] Implement Python → Godot communication
- [ ] Implement Godot → Python communication
- [ ] Test round-trip perception → action loop

## 🎮 Phase 2: First Scene (Week 3-4)

### Foraging Scene
- [ ] Create Godot scene with terrain
- [ ] Add resource spawning system
- [ ] Add agent spawning
- [ ] Implement perception (raycast, entity detection)
- [ ] Implement actions (move, pickup)
- [ ] Connect to Python agent runtime

### Evaluation
- [ ] Track resources collected
- [ ] Track time to completion
- [ ] Generate replay logs
- [ ] Create scorecard system

## 🧠 Phase 3: Memory System (Week 5-6)

- [ ] Implement short-term memory (FIFO queue)
- [ ] Integrate FAISS for vector store
- [ ] Add embedding generation (sentence-transformers)
- [ ] Implement RAG retrieval
- [ ] Test memory persistence
- [ ] Add episode summarization

## 🔌 Phase 4: Additional Backends (Week 7-8)

- [ ] Implement vLLM backend
- [ ] Implement TensorRT-LLM backend (stretch)
- [ ] Add backend switching tests
- [ ] Document backend configuration
- [ ] Performance benchmarks

## 🎯 Phase 5: More Scenes (Week 9-12)

### Crafting Chain Scene
- [ ] Design crafting recipes
- [ ] Implement resource gathering
- [ ] Implement crafting stations
- [ ] Test multi-step reasoning

### Team Capture Scene
- [ ] Implement team system
- [ ] Add capture points
- [ ] Test multi-agent coordination
- [ ] Add team communication

## 📊 Phase 6: Evaluation Infrastructure (Week 13-14)

- [ ] Complete eval harness
- [ ] Add metrics aggregation
- [ ] Create visualization dashboard
- [ ] Implement curriculum learning
- [ ] Add benchmark comparison tools

## 🚀 Phase 7: Advanced Features (Future)

### RL Fine-tuning
- [ ] Implement trajectory collection
- [ ] Add PPO/DPO training loop
- [ ] Create reward shaping system
- [ ] Test self-play scenarios

### Multi-modal
- [ ] Integrate CLIP or similar
- [ ] Add screenshot observations
- [ ] Test visual reasoning

### Performance
- [ ] Profile bottlenecks
- [ ] Optimize LLM inference
- [ ] Add response caching
- [ ] Implement speculative actions
- [ ] Add batch processing

## 📝 Documentation & Community

- [ ] Write "Creating Your First Agent" tutorial
- [ ] Create video walkthrough
- [ ] Add example agents
- [ ] Set up discussions on GitHub
- [ ] Create contributing guide for specific areas
- [ ] Add code of conduct

## 🐛 Known Issues

- Need to handle large files in git (models)
- Line ending warnings on Windows (harmless but noisy)
- Need CI/CD for automated testing

## 💡 Ideas / Backlog

- WebAssembly build for browser demos
- Docker containers for easy setup
- Jupyter notebook tutorials
- Integration with Godot's visual scripting
- Plugin for Godot asset library
- Discord bot for agent demos
- Benchmarking leaderboard

---

**Last Updated**: 2025-11-06
**Current Phase**: Foundation Setup
**Next Milestone**: Compile C++ module and test Python runtime
