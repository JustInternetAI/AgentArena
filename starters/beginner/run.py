"""
Beginner Agent Runner

This script starts the agent server and connects it to Agent Arena.

Usage:
    python run.py

Then launch Agent Arena, connect to localhost:5000, and run a scenario.
"""

import logging
from agent_arena_sdk import AgentArena
from agent import Agent

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def main():
    """Run the beginner agent."""
    logger.info("Starting Beginner Agent...")
    logger.info("=" * 60)
    logger.info("Waiting for connection from Agent Arena game...")
    logger.info("Connect to: localhost:5000")
    logger.info("=" * 60)

    # Create agent
    agent = Agent()

    # Create arena connection
    arena = AgentArena(host="127.0.0.1", port=5000)

    # Run agent (blocks until Ctrl+C)
    try:
        arena.run(agent.decide)
    except KeyboardInterrupt:
        logger.info("\nAgent stopped by user")


if __name__ == "__main__":
    main()
