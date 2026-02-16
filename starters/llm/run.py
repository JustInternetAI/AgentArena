"""
LLM Agent Runner

This script starts an LLM-powered agent using a local language model.

Requirements:
- Model downloaded via model manager
- GPU with CUDA support (recommended, can run on CPU)

Usage:
    # With default model
    python run.py

    # With custom model
    python run.py --model path/to/model.gguf

Then launch Agent Arena, connect to localhost:5000, and run a scenario.
"""

import argparse
import logging
from agent_arena_sdk import AgentArena
from agent import Agent

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def main():
    """Run the LLM agent."""
    parser = argparse.ArgumentParser(description="Run LLM-powered agent")
    parser.add_argument(
        "--model",
        type=str,
        default="models/llama-2-7b/gguf/q4/model.gguf",
        help="Path to GGUF model file",
    )
    parser.add_argument("--port", type=int, default=5000, help="Port to listen on")

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Starting LLM Agent...")
    logger.info(f"Model: {args.model}")
    logger.info("Features: LLM Reasoning + Memory")
    logger.info("=" * 60)
    logger.info("Loading model (this may take a minute)...")

    try:
        # Create agent (loads LLM)
        agent = Agent(model_path=args.model)

        logger.info("=" * 60)
        logger.info("Model loaded! Waiting for connection from Agent Arena game...")
        logger.info(f"Connect to: localhost:{args.port}")
        logger.info("=" * 60)

        # Create arena connection
        arena = AgentArena(host="127.0.0.1", port=args.port)

        # Run agent (blocks until Ctrl+C)
        arena.run(agent.decide)

    except KeyboardInterrupt:
        logger.info("\nAgent stopped by user")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
    finally:
        # Unload model
        if "agent" in locals():
            logger.info("Unloading model...")
            agent.llm.unload()


if __name__ == "__main__":
    main()
