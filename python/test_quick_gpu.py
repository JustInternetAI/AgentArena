"""
Quick GPU acceleration test.
"""

import time

from backends import BackendConfig, LlamaCppBackend

print("\n" + "=" * 60)
print("Quick GPU Test")
print("=" * 60 + "\n")

# Test with GPU
config_gpu = BackendConfig(
    model_path="../models/llama-2-7b-chat.Q4_K_M.gguf",
    temperature=0.7,
    max_tokens=50,
    n_gpu_layers=-1,  # All layers to GPU
)

print("Loading model with GPU acceleration...")
start = time.time()
backend = LlamaCppBackend(config_gpu)
load_time = time.time() - start
print(f"Load time: {load_time:.2f}s\n")

prompt = "[INST] What is 2+2? Answer in one sentence. [/INST]"

print("Generating response...")
start = time.time()
result = backend.generate(prompt, max_tokens=30)
gen_time = time.time() - start

tokens_per_sec = result.tokens_used / gen_time if gen_time > 0 else 0

print(f"\nPrompt: {prompt}")
print(f"Response: {result.text.strip()}\n")
print(f"Generation time: {gen_time:.2f}s")
print(f"Tokens: {result.tokens_used}")
print(f"Speed: {tokens_per_sec:.2f} tokens/sec")

if tokens_per_sec > 50:
    print("\nSUCCESS: GPU acceleration is WORKING! Excellent speed!")
elif tokens_per_sec > 20:
    print("\nSUCCESS: GPU acceleration appears to be working.")
else:
    print("\nWARNING: Speed seems slow - GPU may not be fully utilized.")

backend.unload()
print("\n" + "=" * 60)
