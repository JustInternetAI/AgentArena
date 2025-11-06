# Quick Start Guide

This guide will help you get Agent Arena up and running in minutes.

## Prerequisites

Before starting, ensure you have:

- **Godot 4.2+** installed ([download](https://godotengine.org/download))
- **Python 3.11+** ([download](https://www.python.org/downloads/))
- **CMake 3.20+** ([download](https://cmake.org/download/))
- **C++ compiler** (MSVC 2019+, GCC 9+, or Clang 10+)
- **Git** for cloning dependencies

## Step 1: Clone the Repository

```bash
git clone https://github.com/JustInternetAI/AgentArena.git
cd agent-arena
```

## Step 2: Set Up C++ Module

### 2.1 Install godot-cpp Dependency

**On Windows:**
```bash
scripts\setup_godot_cpp.bat
```

**On Linux/macOS:**
```bash
chmod +x scripts/setup_godot_cpp.sh
./scripts/setup_godot_cpp.sh
```

### 2.2 Build the GDExtension Module

```bash
cd godot
mkdir build
cd build
cmake ..
cmake --build . --config Release
```

The compiled library will be in `bin/[platform]/`.

## Step 3: Set Up Python Environment

### 3.1 Create Virtual Environment

```bash
cd ../../python
python -m venv venv
```

### 3.2 Activate Virtual Environment

**On Windows:**
```bash
venv\Scripts\activate
```

**On Linux/macOS:**
```bash
source venv/bin/activate
```

### 3.3 Install Dependencies

```bash
pip install -r requirements.txt
```

**Optional:** Install with specific feature sets:
```bash
# Development tools
pip install -e ".[dev]"

# LLM backends
pip install -e ".[llm]"

# Vector stores
pip install -e ".[vector]"

# Everything
pip install -e ".[dev,llm,vector]"
```

## Step 4: Download a Model

Agent Arena works with local LLM models. Download a compatible model:

### Using llama.cpp

1. Create a models directory:
   ```bash
   mkdir -p models
   cd models
   ```

2. Download a GGUF model (example - Llama 2 7B):
   ```bash
   # Using wget or curl
   wget https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf
   ```

3. Update the config to point to your model:
   ```yaml
   # In configs/backend/llama_cpp.yaml
   backend:
     model_path: "models/llama-2-7b-chat.Q4_K_M.gguf"
   ```

## Step 5: Run Your First Agent

### 5.1 Test Python Runtime

Create a test script `test_agent.py`:

```python
from agent_runtime import Agent, AgentRuntime, ToolDispatcher
from backends import LlamaCppBackend, BackendConfig
from tools import register_world_query_tools, register_movement_tools

# Initialize backend
config = BackendConfig(
    model_path="models/llama-2-7b-chat.Q4_K_M.gguf",
    temperature=0.7,
    max_tokens=256,
)
backend = LlamaCppBackend(config)

# Create tool dispatcher
dispatcher = ToolDispatcher()
register_world_query_tools(dispatcher)
register_movement_tools(dispatcher)

# Create agent
agent = Agent(
    agent_id="test_agent",
    backend=backend,
    tools=list(dispatcher.schemas.keys()),
    goals=["Explore the environment", "Collect resources"],
)

# Simulate perception
observation = {
    "position": [0.0, 0.0, 0.0],
    "visible_entities": [
        {"id": "tree_1", "type": "tree", "position": [5.0, 0.0, 3.0]},
        {"id": "rock_1", "type": "rock", "position": [8.0, 0.0, -2.0]},
    ],
}
agent.perceive(observation)

# Get decision
action = agent.decide_action()
print(f"Agent decided: {action}")

# Execute tool
if action and action.tool_name != "none":
    result = dispatcher.execute_tool(action.tool_name, action.parameters)
    print(f"Tool result: {result}")
```

Run it:
```bash
python test_agent.py
```

### 5.2 Open in Godot

1. Open Godot 4
2. Import the project (select the `agent-arena` folder)
3. Wait for initial import to complete
4. Open the test scene: `scenes/foraging/foraging.tscn`
5. Press F5 to run the scene

## Step 6: Verify Installation

Run the test suite:

```bash
cd tests
pytest -v
```

## Next Steps

### Create Your First Custom Agent

See [docs/creating_agents.md](creating_agents.md) for a detailed tutorial.

### Configure Your Simulation

Edit `configs/config.yaml` to customize:
- Tick rate and determinism
- Agent runtime settings
- Logging configuration
- Scene parameters

### Add Custom Tools

See [docs/adding_tools.md](adding_tools.md) for instructions on creating custom tools.

### Run Evaluations

```bash
cd python/evals
python run_eval.py --scene foraging --agents 5 --trials 10
```

## Troubleshooting

### Model Loading Errors

If you get "Failed to load model":
- Check that the model path is correct
- Ensure you have enough RAM (7B models need ~8GB)
- Try a smaller quantized model (Q4_K_S instead of Q4_K_M)

### Build Errors

If CMake fails:
- Ensure godot-cpp was cloned properly: `git submodule update --init --recursive`
- Check CMake version: `cmake --version` (need 3.20+)
- On Windows, use Visual Studio 2019+ or 2022

### Python Import Errors

If imports fail:
- Ensure virtual environment is activated
- Reinstall requirements: `pip install -r requirements.txt --force-reinstall`

### Godot Module Not Loading

If Godot doesn't recognize the module:
- Check that the `.gdextension` file is in the godot/ folder
- Verify the compiled library is in `bin/[platform]/`
- Restart Godot Editor

## Getting Help

- **Documentation**: [docs/](../docs/)
- **GitHub Issues**: [github.com/JustInternetAI/AgentArena/issues](https://github.com/JustInternetAI/AgentArena/issues)
- **Discussions**: [github.com/JustInternetAI/AgentArena/discussions](https://github.com/JustInternetAI/AgentArena/discussions)

## What's Next?

- Explore the [architecture documentation](architecture.md)
- Read about [agent design patterns](agent_patterns.md)
- Check out [example scenes](examples.md)
- Join the community!
