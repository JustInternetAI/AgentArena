# llama.cpp Backend Setup

Guide to setting up and using the llama.cpp backend for local LLM inference, including GPU acceleration.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Model Setup](#model-setup)
- [Configuration](#configuration)
- [Quick Start](#quick-start)
- [GPU Acceleration](#gpu-acceleration)
- [Performance Tuning](#performance-tuning)
- [Use Cases](#use-cases)
- [Troubleshooting](#troubleshooting)

---

## Overview

llama.cpp provides efficient CPU and GPU inference for LLaMA models using GGUF format. It's suitable for:
- Local development on Windows
- CPU-only inference (no CUDA required)
- Low memory usage with quantized models
- Quick prototyping

---

## Prerequisites

- Python 3.11+
- llama-cpp-python (`pip install llama-cpp-python`)
- A GGUF model file

---

## Model Setup

### Download a GGUF Model

Place models in the `models/` directory:
```
AgentArena/
  models/
    llama-2-7b-chat.Q4_K_M.gguf
```

### Quantization Levels

| Quantization | File Size | Quality | Speed |
|--------------|-----------|---------|-------|
| Q2_K | ~2.5GB | Lower | Fastest |
| Q4_K_M | ~3.9GB | Good | Fast |
| Q5_K_M | ~4.8GB | Better | Medium |
| Q8_0 | ~7GB | Best | Slower |

**Q4_K_M** is the recommended balance for most use cases.

---

## Configuration

### Python Code

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

### Hydra Config

Edit `configs/backend/llama_cpp.yaml`:

```yaml
backend:
  type: llama_cpp
  model_path: "models/llama-2-7b-chat.Q4_K_M.gguf"
  n_ctx: 4096       # Context window
  n_threads: 8      # CPU threads (adjust for your CPU)
  n_gpu_layers: 0   # 0 = CPU only, -1 = full GPU offload
  temperature: 0.7
  max_tokens: 512
```

---

## Quick Start

### Basic Text Generation

```python
from backends import LlamaCppBackend, BackendConfig

config = BackendConfig(
    model_path="models/llama-2-7b-chat.Q4_K_M.gguf",
    temperature=0.7,
    max_tokens=256,
)
backend = LlamaCppBackend(config)

result = backend.generate("Hello! My name is")
print(result.text)
```

### Tool/Function Calling

```python
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

result = backend.generate_with_tools("Move to position (10, 20, 5)", tools)

if "parsed_tool_call" in result.metadata:
    print(f"Tool: {result.metadata['parsed_tool_call']}")
```

---

## GPU Acceleration

### Expected Performance

With an NVIDIA GPU and full GPU offload:

| Model | Quantization | CPU Speed | GPU Speed | Speedup |
|-------|--------------|-----------|-----------|---------|
| Llama-2-7B | Q4_K_M | ~9 tok/s | ~100+ tok/s | 10-15x |
| Llama-2-13B | Q4_K_M | ~4 tok/s | ~60+ tok/s | 15-20x |
| Llama-2-70B | Q4_K_M | N/A | ~20 tok/s | - |

### Option 1: Install CUDA Toolkit (Recommended)

1. **Download CUDA Toolkit 12.x** from https://developer.nvidia.com/cuda-downloads
2. **Install llama-cpp-python with CUDA:**

```bash
cd python
venv\Scripts\activate
pip uninstall llama-cpp-python
pip install llama-cpp-python==0.3.4 --index-url https://abetlen.github.io/llama-cpp-python/whl/cu122
```

### Option 2: Use vLLM (Linux/WSL2)

For maximum GPU performance:

```bash
pip install vllm
python run_vllm_server.py --model meta-llama/Llama-2-7b-chat-hf

# Connect from Windows
from backends import VLLMBackend, VLLMBackendConfig
config = VLLMBackendConfig(api_base="http://localhost:8000/v1")
backend = VLLMBackend(config)
```

### Option 3: llama.cpp Standalone (Advanced)

Build llama.cpp with CUDA support directly:

```bash
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
cmake -B build -DGGML_CUDA=ON
cmake --build build --config Release
```

### GPU Configuration

```python
config = BackendConfig(
    model_path="../models/llama-2-7b-chat.Q4_K_M.gguf",
    temperature=0.7,
    max_tokens=512,
    n_gpu_layers=-1,  # -1 = all layers to GPU
)
backend = LlamaCppBackend(config)
```

**GPU Layer Options:**
- `n_gpu_layers=0`: CPU only (default)
- `n_gpu_layers=20`: Offload 20 layers to GPU (hybrid)
- `n_gpu_layers=-1`: Offload all layers to GPU (fastest)

---

## Performance Tuning

### CPU Threads

Adjust `n_threads` based on your CPU:
- **4-core**: 4-6 threads
- **8-core**: 8-12 threads
- **16-core**: 12-16 threads

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

---

## Use Cases

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

---

## Troubleshooting

### "Could not find module llama.dll"

CUDA runtime DLLs not found. Install CUDA Toolkit or add to PATH:
```
C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.x\bin
```

### "CUDA out of memory"

- Use smaller quantization (Q4_K_M instead of Q8)
- Reduce `n_ctx`
- Use partial GPU offload (`n_gpu_layers=20`)

### GPU Not Being Used (nvidia-smi shows 0%)

Set `n_gpu_layers=-1` in BackendConfig.

### Slow First Inference

Normal — GPU kernel compilation on first run. Subsequent calls will be fast.

### Model Loading is Slow

Expected: 10-30 seconds for Q4_K_M. Keep model loaded between requests.

### Out of Memory

- Reduce `n_ctx` to 2048 or 1024
- Close other applications
- Use a smaller model or quantization

### Import Error (`No module named 'llama_cpp'`)

```bash
cd python
venv\Scripts\activate
pip install llama-cpp-python
```

---

## Resources

- [llama.cpp GitHub](https://github.com/ggerganov/llama.cpp)
- [llama-cpp-python Documentation](https://llama-cpp-python.readthedocs.io/)
- [GGUF Models on HuggingFace](https://huggingface.co/TheBloke)
- [CUDA Toolkit Download](https://developer.nvidia.com/cuda-downloads)
- [vLLM Documentation](https://docs.vllm.ai/)
