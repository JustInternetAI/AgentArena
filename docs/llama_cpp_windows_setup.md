# llama.cpp Backend Setup for Windows

This guide shows how to set up and use the llama.cpp backend for local development on Windows.

## Overview

llama.cpp provides efficient CPU and GPU inference for LLaMA models using GGUF format. It's perfect for:
- Local development on Windows
- CPU-only inference (no CUDA required)
- Low memory usage with quantized models
- Quick prototyping

## Prerequisites

- ✅ Python 3.11 (already installed)
- ✅ llama-cpp-python (already installed)
- ✅ GGUF model file

## Model Setup

### 1. Download a GGUF Model

You've already downloaded: `llama-2-7b-chat.Q4_K_M.gguf` (3.9GB)

Place it in the `models/` directory:
```
AgentArena/
├── models/
│   └── llama-2-7b-chat.Q4_K_M.gguf
```

### 2. Model Quantization Levels

GGUF models come in different quantization levels:

| Quantization | File Size | Quality | Speed |
|--------------|-----------|---------|-------|
| Q2_K | ~2.5GB | Lower | Fastest |
| Q4_K_M | ~3.9GB | Good | Fast |
| Q5_K_M | ~4.8GB | Better | Medium |
| Q8_0 | ~7GB | Best | Slower |

**Q4_K_M** is the recommended balance for most use cases.

## Configuration

### Using Python Code

```python
from backends import LlamaCppBackend, BackendConfig

config = BackendConfig(
    model_path="models/llama-2-7b-chat.Q4_K_M.gguf",
    temperature=0.7,
    max_tokens=512,
    top_p=0.9,
    top_k=40,
)

backend = LlamaCppBackend(config)
```

### Using Hydra Config

Edit `configs/backend/llama_cpp.yaml`:

```yaml
backend:
  type: llama_cpp
  model_path: "models/llama-2-7b-chat.Q4_K_M.gguf"

  n_ctx: 4096  # Context window
  n_threads: 8  # CPU threads (adjust based on your CPU)
  n_gpu_layers: 0  # 0 = CPU only, 35 = full GPU offload

  temperature: 0.7
  max_tokens: 512
```

## Quick Start

### 1. Run the Test Script

```bash
cd python
venv\Scripts\activate
python test_llama_backend.py
```

This will test:
- Basic text generation
- Function/tool calling
- Different temperature settings
- Multi-turn conversations

### 2. Use in Your Code

```python
from backends import LlamaCppBackend, BackendConfig

# Initialize
config = BackendConfig(
    model_path="models/llama-2-7b-chat.Q4_K_M.gguf",
    temperature=0.7,
    max_tokens=256,
)
backend = LlamaCppBackend(config)

# Generate text
result = backend.generate("Hello! My name is")
print(result.text)

# Generate with tools
tools = [
    {
        "name": "move_to",
        "description": "Move to coordinates",
        "parameters": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "array",
                    "items": {"type": "number"}
                }
            }
        }
    }
]

result = backend.generate_with_tools(
    "Move to position (10, 20, 5)",
    tools
)

if "parsed_tool_call" in result.metadata:
    print(f"Tool: {result.metadata['parsed_tool_call']}")
```

## GPU Acceleration (Optional)

If you have an NVIDIA GPU with CUDA, you can offload layers to GPU:

### 1. Install CUDA-enabled llama-cpp-python

```bash
# Uninstall CPU version
pip uninstall llama-cpp-python

# Install with CUDA support (requires CUDA 11.x or 12.x)
set CMAKE_ARGS=-DLLAMA_CUBLAS=on
pip install llama-cpp-python --force-reinstall --no-cache-dir
```

### 2. Update Configuration

```python
config = BackendConfig(
    model_path="models/llama-2-7b-chat.Q4_K_M.gguf",
    # ... other settings ...
)

# When creating backend, enable GPU layers
from llama_cpp import Llama

llm = Llama(
    model_path=config.model_path,
    n_ctx=4096,
    n_threads=8,
    n_gpu_layers=35,  # Offload all layers to GPU
)
```

Or edit the backend code to support `n_gpu_layers` parameter.

## Performance Tuning

### CPU Threads

Adjust `n_threads` based on your CPU:
- **4-core CPU**: 4-6 threads
- **8-core CPU**: 8-12 threads
- **16-core CPU**: 12-16 threads

```python
# In llama_cpp_backend.py, line 30-34
self.llm = Llama(
    model_path=self.config.model_path,
    n_ctx=4096,
    n_threads=12,  # Adjust this
    n_gpu_layers=0,
)
```

### Context Window

Reduce `n_ctx` if running out of memory:
- **4096**: Full context (default)
- **2048**: Half context, less memory
- **1024**: Quarter context, minimal memory

### Batch Size

Adjust `n_batch` for prompt processing speed:
- **512**: Default, good balance
- **128**: Lower memory, slower
- **1024**: More memory, faster

## Troubleshooting

### Model Loading is Slow

**Expected behavior**: First load takes 10-30 seconds for Q4_K_M model.

**Solutions**:
- Use `use_mmap=true` (default) for faster loading
- Keep the model loaded between requests
- Use a smaller quantization (Q2_K)

### Out of Memory

```
RuntimeError: Failed to allocate memory
```

**Solutions**:
- Reduce `n_ctx` to 2048 or 1024
- Close other applications
- Use a smaller model or quantization

### Slow Generation

**Solutions**:
- Increase `n_threads` up to your CPU core count
- Enable GPU offload with `n_gpu_layers`
- Reduce `max_tokens`
- Use a smaller model

### Import Error

```
ModuleNotFoundError: No module named 'llama_cpp'
```

**Solution**:
```bash
cd python
venv\Scripts\activate
pip install llama-cpp-python
```

## Example Use Cases

### Agent Decision Making

```python
def get_agent_action(observation):
    prompt = f"""You are an AI agent in a game world.

Current observation: {observation}

Available actions:
- move_to(x, y, z): Move to coordinates
- pickup_item(name): Pick up an item
- use_item(name): Use an item from inventory

What action should you take? Respond with JSON:
{{"action": "action_name", "params": {{}}, "reasoning": "why"}}
"""

    result = backend.generate(prompt, temperature=0.5, max_tokens=200)
    return result.text
```

### Conversation System

```python
def chat_with_agent(messages):
    # Format conversation for Llama-2 chat format
    prompt = ""
    for msg in messages:
        if msg["role"] == "user":
            prompt += f"[INST] {msg['content']} [/INST]"
        else:
            prompt += f" {msg['content']}</s>"

    result = backend.generate(prompt, max_tokens=300)
    return result.text
```

## Next Steps

1. ✅ Test the backend with `python test_llama_backend.py`
2. Integrate with your agent runtime
3. Experiment with different prompts and temperatures
4. Consider GPU acceleration for production use

## Resources

- [llama.cpp GitHub](https://github.com/ggerganov/llama.cpp)
- [llama-cpp-python Documentation](https://llama-cpp-python.readthedocs.io/)
- [GGUF Model Download](https://huggingface.co/TheBloke)
- [Model Quantization Guide](https://github.com/ggerganov/llama.cpp#quantization)
