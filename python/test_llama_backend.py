"""
Test script for llama.cpp backend on Windows.

This script demonstrates how to use the llama.cpp backend
for local development with a GGUF model.
"""

import logging

from backends import BackendConfig, LlamaCppBackend

# Set up logging to see what's happening
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def main():
    logger.info("Starting llama.cpp backend test")

    # Configuration for the backend
    config = BackendConfig(
        model_path="../models/llama-2-7b-chat.Q4_K_M.gguf",  # Relative to python/ directory
        temperature=0.7,
        max_tokens=256,
        top_p=0.9,
        top_k=40,
    )

    logger.info(f"Loading model from: {config.model_path}")

    try:
        # Initialize the backend
        backend = LlamaCppBackend(config)

        # Check if backend is available
        if not backend.is_available():
            logger.error("Backend is not available!")
            return

        logger.info("Backend loaded successfully!")

        # Test 1: Basic text generation
        logger.info("\n" + "=" * 60)
        logger.info("Test 1: Basic Text Generation")
        logger.info("=" * 60)

        prompt = "Hello! My name is"
        logger.info(f"Prompt: '{prompt}'")

        result = backend.generate(prompt, max_tokens=50)

        logger.info(f"Generated text: {result.text}")
        logger.info(f"Tokens used: {result.tokens_used}")
        logger.info(f"Finish reason: {result.finish_reason}")

        # Test 2: Tool calling
        logger.info("\n" + "=" * 60)
        logger.info("Test 2: Tool Calling (Function Calling)")
        logger.info("=" * 60)

        tools = [
            {
                "name": "move_to",
                "description": "Move agent to target coordinates",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "Target [x, y, z] coordinates",
                        }
                    },
                    "required": ["target"],
                },
            },
            {
                "name": "pickup_item",
                "description": "Pick up an item from the world",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "item_name": {
                            "type": "string",
                            "description": "Name of the item to pick up",
                        }
                    },
                    "required": ["item_name"],
                },
            },
        ]

        prompt = "I need to pick up the sword and then move to coordinates (10, 20, 5)"
        logger.info(f"Prompt: '{prompt}'")

        result = backend.generate_with_tools(prompt, tools, temperature=0.5)

        logger.info(f"Generated text: {result.text}")
        logger.info(f"Tokens used: {result.tokens_used}")

        if "parsed_tool_call" in result.metadata:
            logger.info(f"Parsed tool call: {result.metadata['parsed_tool_call']}")
        elif "parse_error" in result.metadata:
            logger.warning("Failed to parse tool call from response")

        # Test 3: Different temperatures
        logger.info("\n" + "=" * 60)
        logger.info("Test 3: Temperature Comparison")
        logger.info("=" * 60)

        prompt = "The capital of France is"

        for temp in [0.1, 0.7, 1.0]:
            logger.info(f"\nTemperature: {temp}")
            result = backend.generate(prompt, temperature=temp, max_tokens=20)
            logger.info(f"Result: {result.text.strip()}")

        # Test 4: Conversation context
        logger.info("\n" + "=" * 60)
        logger.info("Test 4: Multi-turn Conversation")
        logger.info("=" * 60)

        conversation = """<s>[INST] You are a helpful AI assistant. [/INST] I understand. I'm here to help!</s>
[INST] What is the weather like today? [/INST]"""

        result = backend.generate(conversation, max_tokens=100)
        logger.info(f"Assistant: {result.text}")

        logger.info("\n" + "=" * 60)
        logger.info("All tests completed successfully!")
        logger.info("=" * 60)

        # Clean up
        backend.unload()
        logger.info("Backend unloaded")

    except Exception as e:
        logger.error(f"Error during testing: {e}", exc_info=True)
        return


if __name__ == "__main__":
    main()
