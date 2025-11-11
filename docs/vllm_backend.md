# vLLM Backend Integration

This document describes how to use the vLLM backend for high-throughput LLM inference in Agent Arena.

## Overview

vLLM is a high-performance inference engine optimized for serving large language models at scale. It provides:

- **High throughput**: PagedAttention and continuous batching
- **OpenAI-compatible API**: Drop-in replacement for OpenAI API
- **Multiple model support**: Llama, Mistral, Qwen, and more
- **Function calling**: Native support for tool/function calling
- **GPU acceleration**: Optimized CUDA kernels

## Requirements

### System Requirements

- **GPU**: NVIDIA GPU with CUDA support (8GB+ VRAM recommended)
- **CUDA**: Version 11.8 or 12.1
- **Python**: 3.8-3.11
- **OS**: Linux (recommended) or Windows with WSL2

### Installation

```bash
# Activate your virtual environment
cd python
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install vLLM (requires CUDA)
pip install vllm

# For specific CUDA version (e.g., CUDA 12.1)
pip install vllm-cuda121
```

**Note**: vLLM requires a CUDA-capable GPU. It does not support CPU-only inference.

## Starting the vLLM Server

### Option 1: Using the helper script

```bash
cd python
python run_vllm_server.py --model meta-llama/Llama-2-7b-chat-hf --port 8000
```

### Option 2: Direct command

```bash
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Llama-2-7b-chat-hf \
    --port 8000 \
    --gpu-memory-utilization 0.9 \
    --max-model-len 4096
```

### Common Arguments

- `--model`: Model name from HuggingFace or local path
- `--port`: Server port (default: 8000)
- `--tensor-parallel-size`: Number of GPUs to use
- `--gpu-memory-utilization`: GPU memory fraction (0.0-1.0)
- `--max-model-len`: Maximum context length
- `--dtype`: Data type (auto, half, float16, bfloat16, float32)

## Configuration

### Hydra Config File

Edit `configs/backend/vllm.yaml`:

```yaml
backend:
  type: vllm
  model: "meta-llama/Llama-2-7b-chat-hf"

  # Server settings
  host: "localhost"
  port: 8000
  api_base: "http://localhost:8000/v1"

  # Model parameters
  tensor_parallel_size: 1  # Number of GPUs
  dtype: "auto"
  max_model_len: 4096
  gpu_memory_utilization: 0.9

  # Generation
  temperature: 0.7
  top_p: 0.9
  max_tokens: 512

  # Function calling
  function_calling:
    enabled: true
    format: "json"
```

### Python Code

```python
from backends import VLLMBackend, VLLMBackendConfig

# Create configuration
config = VLLMBackendConfig(
    model_path="meta-llama/Llama-2-7b-chat-hf",
    api_base="http://localhost:8000/v1",
    temperature=0.7,
    max_tokens=512,
)

# Initialize backend
backend = VLLMBackend(config)

# Check availability
if backend.is_available():
    print("vLLM server is ready!")

# Generate text
result = backend.generate("Hello, my name is")
print(result.text)

# Generate with tools
tools = [
    {
        "name": "move_to",
        "description": "Move agent to coordinates",
        "parameters": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Target [x, y, z] coordinates"
                }
            },
            "required": ["target"]
        }
    }
]

result = backend.generate_with_tools(
    "I need to move to coordinates (10, 20, 5)",
    tools
)

if "tool_call" in result.metadata:
    print(f"Tool: {result.metadata['tool_call']['name']}")
    print(f"Arguments: {result.metadata['tool_call']['arguments']}")
```

## Supported Models

vLLM supports many model architectures. Popular choices:

### Llama Models
- `meta-llama/Llama-2-7b-chat-hf`
- `meta-llama/Llama-2-13b-chat-hf`
- `meta-llama/Meta-Llama-3-8B-Instruct`

### Mistral Models
- `mistralai/Mistral-7B-Instruct-v0.2`
- `mistralai/Mixtral-8x7B-Instruct-v0.1`

### Qwen Models
- `Qwen/Qwen2-7B-Instruct`
- `Qwen/Qwen2.5-7B-Instruct`

### Function Calling Models
For best function calling support, use models trained for tool use:
- `NousResearch/Hermes-2-Pro-Llama-3-8B`
- `gorilla-llm/gorilla-openfunctions-v2`

## Performance Tuning

### GPU Memory

Adjust `gpu_memory_utilization` based on your VRAM:

- **8GB GPU**: 0.7-0.8
- **16GB GPU**: 0.85-0.9
- **24GB+ GPU**: 0.9-0.95

### Multi-GPU

For multiple GPUs, use tensor parallelism:

```bash
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Llama-2-13b-chat-hf \
    --tensor-parallel-size 2  # Use 2 GPUs
```

### Context Length

Reduce `max_model_len` if running out of memory:

```yaml
max_model_len: 2048  # Instead of 4096
```

## Function Calling

vLLM supports OpenAI-style function calling for compatible models.

### Native Function Calling

```python
tools = [
    {
        "name": "get_weather",
        "description": "Get current weather",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string"}
            }
        }
    }
]

result = backend.generate_with_tools(
    "What's the weather in Paris?",
    tools
)

if "tool_call" in result.metadata:
    tool_call = result.metadata["tool_call"]
    print(f"Calling {tool_call['name']} with {tool_call['arguments']}")
```

### Fallback Method

If the model doesn't support native function calling, the backend automatically falls back to prompt-based tool calling.

## Troubleshooting

### Server Not Starting

```
Error: CUDA out of memory
```

**Solution**: Reduce `gpu_memory_utilization` or `max_model_len`

### Connection Refused

```
ConnectionError: Cannot connect to vLLM server
```

**Solution**:
1. Check if server is running: `curl http://localhost:8000/v1/models`
2. Verify port is correct
3. Check firewall settings

### Slow Generation

**Solutions**:
- Enable tensor parallelism for multi-GPU
- Reduce `max_model_len`
- Use quantized models (e.g., AWQ, GPTQ)
- Check GPU utilization with `nvidia-smi`

### Model Not Found

```
OSError: meta-llama/Llama-2-7b-chat-hf is not a local folder
```

**Solution**:
1. Model will be downloaded from HuggingFace on first run
2. Ensure you have a HuggingFace token for gated models
3. Or download manually and use local path

## Testing

Run the vLLM backend tests:

```bash
# Start vLLM server first
python run_vllm_server.py --model meta-llama/Llama-2-7b-chat-hf

# In another terminal
cd python
venv\Scripts\activate
pytest ../tests/test_vllm_backend.py -v
```

Tests will be skipped if the server is not available.

## Comparison with llama.cpp

| Feature | vLLM | llama.cpp |
|---------|------|-----------|
| **Performance** | High throughput, optimized for serving | Good single-request performance |
| **Hardware** | Requires CUDA GPU | CPU + optional GPU |
| **Memory** | Higher VRAM usage | Lower memory footprint |
| **Batching** | Continuous batching | Manual batching |
| **Setup** | Requires server | Direct library |
| **Use Case** | Production serving, multiple agents | Development, single agent |

## References

- [vLLM Documentation](https://docs.vllm.ai/)
- [vLLM GitHub](https://github.com/vllm-project/vllm)
- [OpenAI API Compatibility](https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html)
- [Supported Models](https://docs.vllm.ai/en/latest/models/supported_models.html)
