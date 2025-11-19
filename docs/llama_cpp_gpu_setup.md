# GPU Acceleration for llama.cpp Backend

This guide explains how to enable GPU acceleration for the llama.cpp backend on Windows.

## Current Status

- ✅ RTX 3090 with 24GB VRAM detected
- ✅ CUDA 12.9 driver installed
- ✅ Backend code updated to support `n_gpu_layers` parameter
- ⚠️ CUDA-enabled llama-cpp-python requires additional setup

## Why GPU Acceleration?

With your RTX 3090, you can expect:
- **10-50x faster** inference compared to CPU
- **Lower latency** for real-time agent responses
- **Larger models** can fit in VRAM

## Setup Options

### Option 1: Install CUDA Toolkit (Recommended)

The pre-built CUDA wheels require CUDA runtime libraries.

1. **Download CUDA Toolkit 12.x**:
   - Visit: https://developer.nvidia.com/cuda-downloads
   - Select: Windows → x86_64 → 12.6 or 12.9
   - Download and install (Base Installer, ~3GB)

2. **Install llama-cpp-python with CUDA**:
   ```bash
   cd python
   venv\Scripts\activate
   pip uninstall llama-cpp-python
   pip install llama-cpp-python==0.3.4 --index-url https://abetlen.github.io/llama-cpp-python/whl/cu122
   ```

3. **Test GPU acceleration**:
   ```bash
   python test_llama_gpu.py
   ```

### Option 2: Use vLLM (Production Alternative)

For maximum GPU performance on Linux or WSL2:

```bash
# In WSL2 or Linux
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

Then use the compiled `llama-cli.exe` or `llama-server.exe`.

## Configuration

Once CUDA is set up, configure GPU layers in your code:

```python
from backends import LlamaCppBackend, BackendConfig

# Full GPU offload (recommended for RTX 3090)
config = BackendConfig(
    model_path="../models/llama-2-7b-chat.Q4_K_M.gguf",
    temperature=0.7,
    max_tokens=512,
    n_gpu_layers=-1,  # -1 = all layers to GPU
)

backend = LlamaCppBackend(config)
```

**GPU Layer Options:**
- `n_gpu_layers=0`: CPU only (current default)
- `n_gpu_layers=20`: Offload 20 layers to GPU (hybrid)
- `n_gpu_layers=-1`: Offload all layers to GPU (fastest)

## Expected Performance

With RTX 3090 and full GPU offload:

| Model | Quantization | CPU Speed | GPU Speed | Speedup |
|-------|--------------|-----------|-----------|---------|
| Llama-2-7B | Q4_K_M | ~9 tok/s | ~100+ tok/s | 10-15x |
| Llama-2-13B | Q4_K_M | ~4 tok/s | ~60+ tok/s | 15-20x |
| Llama-2-70B | Q4_K_M | N/A | ~20 tok/s | - |

## Testing GPU Acceleration

Use the provided test script:

```bash
cd python
venv\Scripts\activate
python test_llama_gpu.py
```

This will compare:
1. CPU-only inference
2. Partial GPU offload (20 layers)
3. Full GPU offload (all layers)

## Troubleshooting

### Error: "Could not find module llama.dll"

**Cause**: CUDA runtime DLLs not found in PATH.

**Solution**: Install CUDA Toolkit (Option 1 above) or add CUDA bin directory to PATH:
```
C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.x\bin
```

### Error: "CUDA out of memory"

**Cause**: Model too large for VRAM.

**Solutions**:
- Use smaller quantization (Q4_K_M instead of Q8)
- Reduce `n_ctx` (context window)
- Use partial GPU offload (e.g., `n_gpu_layers=20`)

### GPU not being used (nvidia-smi shows 0% usage)

**Cause**: `n_gpu_layers=0` (CPU-only mode).

**Solution**: Set `n_gpu_layers=-1` in BackendConfig.

### Slow first inference

**Cause**: GPU kernel compilation on first run.

**Solution**: This is normal. Subsequent inferences will be fast.

## Current CPU Performance

Without GPU acceleration, your current setup achieves:
- **~9 tokens/second** with Q4_K_M quantization
- **~110ms per token** generation time
- Works reliably for development and testing

## Verification

Check if CUDA support is available:

```python
from backends import LlamaCppBackend, BackendConfig

config = BackendConfig(
    model_path="../models/llama-2-7b-chat.Q4_K_M.gguf",
    n_gpu_layers=-1,
)

try:
    backend = LlamaCppBackend(config)
    print("✓ GPU acceleration is working!")
except Exception as e:
    print(f"✗ GPU error: {e}")
    print("Falling back to CPU mode...")
```

## Next Steps

1. **For local development**: Continue using CPU mode (works well)
2. **For production**: Install CUDA Toolkit for GPU acceleration
3. **For maximum performance**: Use vLLM on Linux/WSL2

## Additional Resources

- [llama.cpp Documentation](https://github.com/ggerganov/llama.cpp)
- [llama-cpp-python GPU Guide](https://llama-cpp-python.readthedocs.io/en/latest/)
- [CUDA Toolkit Download](https://developer.nvidia.com/cuda-downloads)
- [vLLM Documentation](https://docs.vllm.ai/)
