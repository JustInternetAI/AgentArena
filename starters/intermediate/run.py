"""
Intermediate Agent Runner

This script starts the intermediate agent with memory and planning.

Usage:
    python run.py

Then launch Agent Arena, connect to localhost:5000, and run a scenario.
"""

import logging
from agent_arena_sdk import AgentArena
from agent import Agent

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def main():
    """Run the intermediate agent."""
    logger.info("Starting Intermediate Agent...")
    logger.info("Features: Memory + Planning")
    logger.info("=" * 60)
    logger.info("Waiting for connection from Agent Arena game...")
    logger.info("Connect to: localhost:5000")
    logger.info("=" * 60)

    # Create agent (with memory and planner)
    agent = Agent()

    # Create arena connection
    arena = AgentArena(host="127.0.0.1", port=5000)

    # Run agent (blocks until Ctrl+C)
    try:
        arena.run(agent.decide)
    except KeyboardInterrupt:
        logger.info("\nAgent stopped by user")
        logger.info(f"Final memory size: {agent.memory.count_observations()} observations")


if __name__ == "__main__":
    main()
