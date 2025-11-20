# Model Management Guide

This guide explains how to download, manage, and use LLM models with Agent Arena.

## Overview

Agent Arena includes a Model Manager tool that automates downloading and managing models from Hugging Face Hub. The tool supports:

- **GGUF models** for llama.cpp backend (CPU and GPU)
- **PyTorch/safetensors models** for vLLM backend (GPU)
- **Automatic caching** to avoid re-downloading
- **Checksum verification** for model integrity
- **Multiple quantization levels** for size/quality tradeoffs

## Quick Start

### 1. Install Dependencies

First, ensure you have the LLM dependencies installed:

```bash
# Activate your virtual environment
cd python
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install LLM dependencies (includes huggingface-hub)
pip install -e ".[llm]"
```

**Note:** The model manager automatically finds the project root, so you can run commands from any directory within the project.

### 2. Download a Model

Download a model using the command-line interface:

```bash
# Download a small model for testing (TinyLlama 1.1B)
python -m tools.model_manager download tinyllama-1.1b-chat --format gguf --quant q4_k_m

# Download a production model (Mistral 7B)
python -m tools.model_manager download mistral-7b-instruct-v0.2 --format gguf --quant q4_k_m
```

### 3. List Downloaded Models

```bash
python -m tools.model_manager list
```

### 4. Use the Model

Update your backend configuration to point to the downloaded model:

```yaml
# configs/backend/llama_cpp.yaml
backend:
  type: llama_cpp
  model_path: "models/mistral-7b-instruct-v0.2/gguf/q4_k_m/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
  n_ctx: 4096
  n_gpu_layers: 0  # Set to -1 for full GPU offload
```

## Available Models

### Small Models (Development/Testing)

| Model | Size | RAM Required | Use Case |
|-------|------|--------------|----------|
| `tinyllama-1.1b-chat` | 1.1B | 2-4 GB | Testing, rapid iteration |
| `phi-2` | 2.7B | 4-8 GB | Development, good reasoning |

### Production Models (7-8B)

| Model | Size | RAM Required | Description |
|-------|------|--------------|-------------|
| `llama-2-7b-chat` | 7B | 8-16 GB | Balanced speed/quality, widely tested |
| `mistral-7b-instruct-v0.2` | 7B | 8-16 GB | High quality instruction following |
| `llama-3-8b-instruct` | 8B | 8-16 GB | Latest Llama, best quality in class |

### Large Models (High Quality)

| Model | Size | RAM Required | Description |
|-------|------|--------------|-------------|
| `llama-2-13b-chat` | 13B | 16-32 GB | Better reasoning than 7B |
| `mixtral-8x7b-instruct` | 47B | 32+ GB | Mixture of Experts, excellent quality |

## Quantization Levels

Quantization reduces model size with minimal quality loss. Choose based on your needs:

| Quantization | Quality | Speed | Size Factor | Recommended For |
|--------------|---------|-------|-------------|-----------------|
| `q4_k_m` | Medium | Fast | 25% | General use, good balance |
| `q5_k_m` | Medium-High | Medium-Fast | 31% | Better quality, still fast |
| `q8_0` | High | Medium | 50% | Near-original quality |

**Example:** A 7B model unquantized is ~14GB. With Q4_K_M quantization it's ~3.8GB.

## CLI Commands

### Download a Model

```bash
python -m tools.model_manager download <model_id> [options]

Options:
  --format FORMAT          Model format (default: gguf)
  --quant QUANTIZATION     Quantization type (e.g., q4_k_m, q5_k_m)
  --force                  Force re-download even if exists
```

**Examples:**

```bash
# Download default quantization
python -m tools.model_manager download llama-2-7b-chat --quant q4_k_m

# Download higher quality version
python -m tools.model_manager download llama-2-7b-chat --quant q8_0

# Force re-download
python -m tools.model_manager download mistral-7b-instruct-v0.2 --quant q4_k_m --force
```

### List Cached Models

```bash
python -m tools.model_manager list [--format FORMAT]

# List all models
python -m tools.model_manager list

# Filter by format
python -m tools.model_manager list --format gguf
```

Output example:
```
Cached Models:
================================================================================
llama-2-7b-chat          gguf      /q4_k_m          3.83 GB
mistral-7b-instruct-v0.2 gguf      /q5_k_m          5.13 GB
================================================================================
Total storage: 8.96 GB
```

### Verify a Model

Check if a downloaded model is valid:

```bash
python -m tools.model_manager verify <model_id> [options]

Options:
  --format FORMAT          Model format (default: gguf)
  --quant QUANTIZATION     Quantization type
```

**Example:**

```bash
python -m tools.model_manager verify llama-2-7b-chat --format gguf --quant q4_k_m
```

### Remove a Model

```bash
python -m tools.model_manager remove <model_id> [options]

Options:
  --format FORMAT          Remove specific format only
  --quant QUANTIZATION     Remove specific quantization only
```

**Examples:**

```bash
# Remove all versions of a model
python -m tools.model_manager remove llama-2-7b-chat

# Remove specific quantization
python -m tools.model_manager remove llama-2-7b-chat --format gguf --quant q4_k_m

# Remove all GGUF versions
python -m tools.model_manager remove llama-2-7b-chat --format gguf
```

### Show Model Information

```bash
python -m tools.model_manager info [model_id]

# List all available models
python -m tools.model_manager info

# Show details for specific model
python -m tools.model_manager info llama-2-7b-chat
```

## Model Storage Structure

Models are cached in the `models/` directory with this structure:

```
models/
├── llama-2-7b-chat/
│   └── gguf/
│       ├── q4_k_m/
│       │   └── llama-2-7b-chat.Q4_K_M.gguf
│       └── q5_k_m/
│           └── llama-2-7b-chat.Q5_K_M.gguf
├── mistral-7b-instruct-v0.2/
│   └── gguf/
│       └── q4_k_m/
│           └── mistral-7b-instruct-v0.2.Q4_K_M.gguf
└── tinyllama-1.1b-chat/
    └── gguf/
        └── q4_k_m/
            └── tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf
```

## Adding Custom Models

To add a custom model to the registry:

1. Edit `configs/models.yaml`
2. Add your model following this template:

```yaml
models:
  your-model-name:
    huggingface_id: "author/model-repo-name"
    description: "Description of the model"
    size_class: "medium"  # tiny, small, medium, large, xlarge
    formats:
      gguf:
        q4_k_m:
          file: "model-filename.Q4_K_M.gguf"
          sha256: null  # Optional: add SHA256 for verification
        q5_k_m:
          file: "model-filename.Q5_K_M.gguf"
          sha256: null
```

3. Download the model:

```bash
python -m tools.model_manager download your-model-name --quant q4_k_m
```

## Storage Requirements

Plan your disk space based on models you'll use:

| Model Class | Q4_K_M Size | Q5_K_M Size | Q8_0 Size |
|-------------|-------------|-------------|-----------|
| Tiny (1B) | ~600 MB | ~750 MB | ~1.2 GB |
| Small (2-3B) | ~1.5 GB | ~2 GB | ~3 GB |
| Medium (7-8B) | ~3.8 GB | ~5 GB | ~7 GB |
| Large (13B) | ~7 GB | ~9 GB | ~13 GB |
| XLarge (47B) | ~26 GB | ~33 GB | ~47 GB |

**Recommendation:** Start with Q4_K_M quantization for best size/quality balance.

## Performance Characteristics

### Speed vs Quality Tradeoff

- **Q4_K_M**: Fastest, good quality, smallest size
- **Q5_K_M**: Slightly slower, better quality, medium size
- **Q8_0**: Slowest, best quality, largest size

### GPU Acceleration

For GPU acceleration with llama.cpp:

```yaml
# configs/backend/llama_cpp.yaml
backend:
  type: llama_cpp
  model_path: "models/mistral-7b-instruct-v0.2/gguf/q4_k_m/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
  n_ctx: 4096
  n_gpu_layers: -1  # -1 = offload all layers to GPU
```

**GPU Memory Requirements:**
- 7B Q4_K_M with full GPU offload: ~4-5 GB VRAM
- 7B Q5_K_M with full GPU offload: ~5-6 GB VRAM
- 13B Q4_K_M with full GPU offload: ~8-9 GB VRAM

## Troubleshooting

### Download Errors

**Problem:** `HTTP 401 Unauthorized`
**Solution:** Some models require authentication. Set your Hugging Face token:

```bash
# Windows
set HF_TOKEN=your_token_here

# Linux/Mac
export HF_TOKEN=your_token_here
```

**Problem:** Download interrupted
**Solution:** The tool supports resume. Just re-run the download command.

**Problem:** "Model not found in registry"
**Solution:** Check available models with `python -m tools.model_manager info`

### Checksum Verification Failed

**Problem:** Checksum mismatch after download
**Solution:**
1. Remove the corrupted model: `python -m tools.model_manager remove <model_id>`
2. Re-download: `python -m tools.model_manager download <model_id> --force`

### Out of Disk Space

**Problem:** Insufficient disk space
**Solution:**
1. Check current usage: `python -m tools.model_manager list`
2. Remove unused models: `python -m tools.model_manager remove <model_id>`
3. Use smaller quantization (Q4_K_M instead of Q8_0)

### Model Loading Errors

**Problem:** Backend fails to load model
**Solution:**
1. Verify model exists: `python -m tools.model_manager list`
2. Check path in config matches actual file path
3. Verify model integrity: `python -m tools.model_manager verify <model_id>`

## Python API

You can also use the ModelManager programmatically:

```python
from pathlib import Path
from tools.model_manager import ModelManager

# Initialize
manager = ModelManager(
    models_dir=Path("models"),
    config_path=Path("configs/models.yaml")
)

# Download a model
model_path = manager.download_model(
    model_id="mistral-7b-instruct-v0.2",
    format="gguf",
    quantization="q4_k_m"
)

if model_path:
    print(f"Model downloaded to: {model_path}")

# List cached models
models = manager.list_models()
for model in models:
    print(f"{model['model']}: {model['size_gb']:.2f} GB")

# Get path to existing model
model_path = manager.get_model_path(
    model_id="llama-2-7b-chat",
    format="gguf",
    quantization="q4_k_m"
)

# Verify model
is_valid = manager.verify_model(
    model_path,
    expected_sha256="abc123..."  # Optional
)

# Remove a model
manager.remove_model("old-model")
```

## Best Practices

1. **Start Small**: Begin with `tinyllama-1.1b-chat` for testing
2. **Monitor Storage**: Regularly check disk usage with `list` command
3. **Clean Up**: Remove unused models to free space
4. **Use Q4_K_M**: Best balance for most use cases
5. **Verify Downloads**: Run `verify` after downloading large models
6. **Plan GPU Usage**: Check VRAM requirements before downloading large models

## See Also

- [Backend Configuration](../configs/backend/)
- [LLM Backend Guide](llm_backends.md)
- [Hugging Face Hub](https://huggingface.co/models)
- [GGUF Format Info](https://github.com/ggerganov/llama.cpp#gguf)
