# Agent Arena for Godot 4

A Godot-native framework for LLM-driven NPCs with tools, memory, and goal-oriented behavior in small simulation scenes. Focused on local models, reproducible evaluations, and pluggable inference backends.

nMaintained by [JustInternetAI](https://github.com/JustInternetAI)

**Founded by Andrew Madison and Justin Madison**

## Overview

**Agent Arena** combines a high-performance Godot 4 C++ module with a Python-based training and evaluation harness to create a testbed for multi-agent AI research. Agents interact in deterministic sandbox environments using function-calling tool APIs, episodic memory, and RAG-based retrieval.

## Features

### Core
- **Godot C++ Module**: Deterministic tick loop, event bus, navigation, sensors, stable replay logs
- **Agent Runtime**: Adapters for llama.cpp, TensorRT-LLM, vLLM with function-calling tool API
- **Model Management**: Automated LLM model downloading from Hugging Face Hub with caching and verification
- **Tool System**: World querying (vision rays, inventories), pathfinding, crafting actions via JSON schemas
- **Memory & RAG**: Short-term scratchpad + long-term vector store with episode summaries
- **Benchmark Scenes**: 3 sandbox environments (foraging, crafting chain, team capture) with metrics
- **Eval Harness**: Seedable scenarios, scorecards, replays, unit tests for agent APIs

### Stretch Goals
- Curriculum learning with increasing scene complexity
- Self-play RL fine-tuning (PPO on discrete action schemas)
- Multi-modal support with small vision encoders (CLIP-like) for visual observations

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Godot 4 Engine                       │
│  ┌──────────────────────────────────────────────────┐  │
│  │         Agent Arena C++ Module (GDExtension)     │  │
│  │  • Deterministic Simulation Loop                 │  │
│  │  • Event Bus & Sensors                           │  │
│  │  • Navigation & Pathfinding                      │  │
│  │  • Action Execution & World State                │  │
│  └──────────────────┬───────────────────────────────┘  │
└─────────────────────┼───────────────────────────────────┘
                      │ IPC / gRPC / HTTP
         ┌────────────┴────────────┐
         │   Python Agent Runtime  │
         │  • LLM Inference        │
         │  • Tool Dispatching     │
         │  • Memory Management    │
         │  • RAG Retrieval        │
         └─────────┬───────────────┘
                   │
      ┌────────────┼────────────┐
      │            │            │
   llama.cpp  TensorRT-LLM   vLLM
```

## Tech Stack

- **Game Engine**: Godot 4 with GDExtension (C++)
- **Languages**: C++ (module), Python 3.11 (runtime/evals)
- **LLM Backends**: llama.cpp, TensorRT-LLM, vLLM
- **ML Framework**: PyTorch (optional for training)
- **Vector Store**: Milvus/FAISS for memory
- **Serialization**: msgpack for replay logs
- **Config Management**: Hydra

## Project Structure

```
agent-arena/
├── godot/                      # Godot 4 C++ module
│   ├── src/                    # C++ source files
│   ├── include/                # Header files
│   ├── bindings/               # GDExtension bindings
│   └── CMakeLists.txt
├── python/                     # Python runtime and tools
│   ├── agent_runtime/          # Agent inference runtime
│   ├── memory/                 # Memory and RAG systems
│   ├── tools/                  # Tool implementations
│   ├── evals/                  # Evaluation harness
│   └── backends/               # LLM backend adapters
├── scenes/                     # Benchmark Godot scenes
│   ├── foraging/
│   ├── crafting_chain/
│   └── team_capture/
├── configs/                    # Hydra configuration files
├── tests/                      # Unit and integration tests
├── docs/                       # Documentation
└── scripts/                    # Build and utility scripts
```

## Getting Started

### Prerequisites

- Godot 4.2+ (with GDExtension support)
- CMake 3.20+
- C++17 compatible compiler (GCC 9+, Clang 10+, MSVC 2019+)
- Python 3.11+
- CUDA Toolkit 12+ (optional, for TensorRT-LLM)

### Build Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/JustInternetAI/AgentArena.git
   cd agent-arena
   ```

2. **Build the Godot module**
   ```bash
   cd godot
   mkdir build && cd build
   cmake ..
   cmake --build .
   ```

3. **Set up Python environment**
   ```bash
   cd ../../python
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Run tests**
   ```bash
   pytest tests/
   ```

### Quick Start

See [docs/quickstart.md](docs/quickstart.md) for a tutorial on creating your first agent-driven scene.

### Model Management

Agent Arena includes a built-in tool to download and manage LLM models from Hugging Face Hub:

```bash
# Download a model for testing
cd python
python -m tools.model_manager download tinyllama-1.1b-chat --format gguf --quant q4_k_m

# List available models in registry
python -m tools.model_manager info

# List downloaded models
python -m tools.model_manager list
```

Supported models include TinyLlama (1.1B), Phi-2 (2.7B), Llama-2 (7B/13B), Mistral (7B), Llama-3 (8B), and Mixtral (8x7B).

For detailed documentation on model management, see [docs/model_management.md](docs/model_management.md).

## Development Roadmap

- [ ] Phase 1: Core infrastructure (deterministic sim, event bus, basic tools)
- [ ] Phase 2: Agent runtime with llama.cpp integration
- [ ] Phase 3: Memory system (scratchpad + vector store)
- [ ] Phase 4: First benchmark scene (foraging)
- [ ] Phase 5: Eval harness and metrics
- [ ] Phase 6: Additional backends (TensorRT-LLM, vLLM)
- [ ] Phase 7: Advanced features (curriculum learning, RL fine-tuning)

## Contributing

Contributions are welcome! This project bridges gamedev and AI research, making it accessible to both communities. Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

## Citation

If you use Agent Arena in your research, please cite:

```bibtex
@software{agent_arena_2025,
  title={Agent Arena: A Godot Framework for LLM-Driven Multi-Agent Simulation},
  author={Madison, Andrew and Madison, Justin},
  year={2025},
  url={https://github.com/JustInternetAI/AgentArena}
}
```
