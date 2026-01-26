"""
Foraging Demo - Run SimpleForager agent in foraging scene.

This script demonstrates the complete observation-decision loop:
1. Godot foraging scene sends observations via IPC
2. Python SimpleForager agent makes decisions
3. Decisions are sent back to Godot for execution

To run:
1. Start this script: python run_foraging_demo.py
2. Open Godot and load foraging.tscn
3. Press SPACE to start the simulation
"""

import logging

from agent_runtime import AgentArena
from user_agents.examples import SimpleForager

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def main():
    """Run foraging demo with SimpleForager agent."""
    logger.info("=" * 60)
    logger.info("Foraging Demo - SimpleForager Agent")
    logger.info("=" * 60)
    logger.info("")
    logger.info("1. This script will start the IPC server")
    logger.info("2. Open Godot and load scenes/foraging.tscn")
    logger.info("3. Press SPACE in Godot to start the simulation")
    logger.info("4. Watch the agent collect resources!")
    logger.info("")
    logger.info("=" * 60)

    try:
        # Create and connect arena
        arena = AgentArena.connect(host="127.0.0.1", port=5000, max_workers=4)

        # Register SimpleForager for the foraging scene agent
        # The foraging scene has agent with id: "foraging_agent_001"
        logger.info("Registering SimpleForager agent...")

        agent_id = "foraging_agent_001"
        arena.register(agent_id, SimpleForager(memory_capacity=10))
        logger.info(f"  ✓ Registered SimpleForager for agent_id: {agent_id}")

        registered = arena.get_registered_agents()
        logger.info(f"Total registered agents: {len(registered)}")
        logger.info("")
        logger.info("✓ IPC Server ready at http://127.0.0.1:5000")
        logger.info("✓ Waiting for observations from Godot...")
        logger.info("")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 60)
        logger.info("")

        # Run the arena (blocks until stopped)
        arena.run()

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
