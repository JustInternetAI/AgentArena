"""
Test GPU-accelerated inference with llama.cpp backend.

This script compares CPU vs GPU performance.
"""

import logging
import time

from backends import BackendConfig, LlamaCppBackend

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def test_inference(config: BackendConfig, test_name: str):
    """Test inference with given config."""
    print(f"\n{'='*60}")
    print(f"{test_name}")
    print("=" * 60)

    start_time = time.time()
    backend = LlamaCppBackend(config)
    load_time = time.time() - start_time

    print(f"Load time: {load_time:.2f}s\n")

    # Test prompt
    prompt = "[INST] Write a short story about a robot exploring Mars in 3 sentences. [/INST]"

    # Generate
    start_time = time.time()
    result = backend.generate(prompt, max_tokens=100)
    gen_time = time.time() - start_time

    tokens_per_sec = result.tokens_used / gen_time if gen_time > 0 else 0

    print(f"Response: {result.text.strip()}\n")
    print(f"Generation time: {gen_time:.2f}s")
    print(f"Tokens: {result.tokens_used}")
    print(f"Speed: {tokens_per_sec:.2f} tokens/sec")

    backend.unload()
    return tokens_per_sec


def main():
    print("\n" + "=" * 60)
    print("GPU Acceleration Test for llama.cpp")
    print("=" * 60)

    model_path = "../models/llama-2-7b-chat.Q4_K_M.gguf"

    # Test 1: CPU only
    cpu_config = BackendConfig(
        model_path=model_path,
        temperature=0.7,
        max_tokens=100,
        n_gpu_layers=0,  # CPU only
    )

    cpu_speed = test_inference(cpu_config, "Test 1: CPU Only (0 GPU layers)")

    # Test 2: Partial GPU offload
    partial_gpu_config = BackendConfig(
        model_path=model_path,
        temperature=0.7,
        max_tokens=100,
        n_gpu_layers=20,  # Offload 20 layers to GPU
    )

    partial_speed = test_inference(partial_gpu_config, "Test 2: Partial GPU (20 layers)")

    # Test 3: Full GPU offload
    full_gpu_config = BackendConfig(
        model_path=model_path,
        temperature=0.7,
        max_tokens=100,
        n_gpu_layers=-1,  # Offload all layers to GPU
    )

    full_speed = test_inference(full_gpu_config, "Test 3: Full GPU (all layers)")

    # Summary
    print("\n" + "=" * 60)
    print("Performance Summary")
    print("=" * 60)
    print(f"CPU only:      {cpu_speed:.2f} tokens/sec (baseline)")
    print(f"Partial GPU:   {partial_speed:.2f} tokens/sec ({partial_speed/cpu_speed:.2f}x speedup)")
    print(f"Full GPU:      {full_speed:.2f} tokens/sec ({full_speed/cpu_speed:.2f}x speedup)")
    print("=" * 60)

    if full_speed > cpu_speed * 2:
        print("\n✓ GPU acceleration is working! Significant speedup achieved.")
    elif full_speed > cpu_speed:
        print("\n⚠ GPU acceleration is working but speedup is modest.")
    else:
        print("\n✗ GPU acceleration may not be working properly.")


if __name__ == "__main__":
    main()
