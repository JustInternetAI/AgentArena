"""
Simple test script for llama.cpp backend.

Demonstrates basic usage without complex tool calling.
"""

import logging

from backends import BackendConfig, LlamaCppBackend

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main():
    print("\n" + "=" * 60)
    print("Llama.cpp Backend - Simple Test")
    print("=" * 60 + "\n")

    # Initialize backend
    config = BackendConfig(
        model_path="../models/llama-2-7b-chat.Q4_K_M.gguf",
        temperature=0.7,
        max_tokens=150,
    )

    logger.info("Loading model (this may take 10-20 seconds)...")
    backend = LlamaCppBackend(config)

    if not backend.is_available():
        logger.error("Backend failed to load!")
        return

    logger.info("Model loaded successfully!\n")

    # Test 1: Simple completion
    print("Test 1: Text Completion")
    print("-" * 40)

    prompt = "The three primary colors are"
    print(f"Prompt: '{prompt}'")

    result = backend.generate(prompt, max_tokens=50)
    print(f"Response: {result.text.strip()}")
    print(f"Tokens: {result.tokens_used}\n")

    # Test 2: Question answering (using Llama-2 chat format)
    print("Test 2: Question Answering")
    print("-" * 40)

    # Llama-2 chat format: [INST] question [/INST]
    prompt = "[INST] What is the capital of France? Answer in one word. [/INST]"
    print("Question: What is the capital of France?")

    result = backend.generate(prompt, temperature=0.1, max_tokens=10)
    print(f"Answer: {result.text.strip()}\n")

    # Test 3: Creative writing
    print("Test 3: Creative Writing")
    print("-" * 40)

    prompt = "[INST] Write a single sentence about a robot exploring Mars. [/INST]"
    print("Task: Write about a robot on Mars")

    result = backend.generate(prompt, temperature=0.9, max_tokens=100)
    print(f"Story: {result.text.strip()}\n")

    # Test 4: Simple tool selection
    print("Test 4: Action Selection")
    print("-" * 40)

    prompt = """[INST] You are a game agent at position (0, 0, 0). You see a sword at position (5, 5, 0).

Available actions:
1. move_to(x, y, z) - Move to coordinates
2. pickup_item(name) - Pick up an item
3. wait() - Do nothing

What should you do FIRST? Reply with just the action name and parameters, like: move_to(5, 5, 0) [/INST]"""

    print("Scenario: Agent sees sword at (5, 5, 0)")

    result = backend.generate(prompt, temperature=0.3, max_tokens=50)
    print(f"Decision: {result.text.strip()}\n")

    # Test 5: Different temperatures
    print("Test 5: Temperature Comparison")
    print("-" * 40)

    base_prompt = (
        "[INST] Complete this sentence in a creative way: The robot opened the door and saw [/INST]"
    )

    for temp in [0.1, 0.5, 1.0]:
        result = backend.generate(base_prompt, temperature=temp, max_tokens=30)
        print(f"Temp {temp}: {result.text.strip()}")

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)

    backend.unload()


if __name__ == "__main__":
    main()
