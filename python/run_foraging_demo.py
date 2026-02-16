"""
Foraging Demo - Run agent in foraging scene using NEW SDK pattern.

This demo has been updated for the LDX refactor (Issue #60).
It demonstrates the new "learner owns the code" approach.

To run:
1. Start this script: python run_foraging_demo.py
2. Open Godot and load foraging.tscn
3. Press SPACE to start the simulation

NOTE: This demo uses the beginner starter as an example.
      For your own agents, copy a starter from starters/ directory.
"""

import logging
import sys
from pathlib import Path

# Add starters to path so we can import from them
sys.path.insert(0, str(Path(__file__).parent.parent / "starters" / "beginner"))

from agent import Agent  # noqa: E402
from agent_arena_sdk import AgentArena  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def main():
    """Run foraging demo with beginner starter agent."""
    logger.info("=" * 60)
    logger.info("Foraging Demo - NEW SDK Pattern")
    logger.info("=" * 60)
    logger.info("")
    logger.info("This demo uses the BEGINNER STARTER from starters/beginner/")
    logger.info("It demonstrates the new 'learner owns the code' approach.")
    logger.info("")
    logger.info("Steps:")
    logger.info("1. This script will start the IPC server")
    logger.info("2. Open Godot and load scenes/foraging.tscn")
    logger.info("3. Press SPACE in Godot to start the simulation")
    logger.info("4. Watch the agent collect resources!")
    logger.info("")
    logger.info("=" * 60)

    try:
        # Create agent (plain Python class, no base class!)
        logger.info("Creating beginner agent...")
        agent = Agent()
        logger.info("  ✓ Agent created (no framework, just plain Python!)")

        # Create arena connection
        logger.info("Starting IPC server...")
        arena = AgentArena(host="127.0.0.1", port=5000)
        logger.info("  ✓ IPC Server ready at http://127.0.0.1:5000")
        logger.info("")
        logger.info("✓ Waiting for observations from Godot...")
        logger.info("")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 60)
        logger.info("")

        # Run the arena with the agent's decide callback
        # This is the new pattern: arena.run(decide_callback)
        arena.run(agent.decide)

    except KeyboardInterrupt:
        logger.info("\n")
        logger.info("=" * 60)
        logger.info("Shutting down gracefully...")
        logger.info("=" * 60)
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
