"""
Entry point for running user agents in Agent Arena.

Users can either:
1. Modify this file to import and register their agents
2. Copy this as a template for their own run scripts
"""

import argparse
import logging
import sys

from agent_runtime import AgentArena

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def main():
    """
    Main entry point for running agents.

    To use this script:
    1. Create your agent class in user_agents/
    2. Import it below
    3. Register it with arena.register()
    4. Run this script

    Example:
        from user_agents.my_agent import MyForagingAgent

        arena = AgentArena.connect(host='127.0.0.1', port=5000)
        arena.register('agent_001', MyForagingAgent())
        arena.run()
    """
    parser = argparse.ArgumentParser(description="Run user agents in Agent Arena simulation")
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Godot simulation host (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Godot simulation port (default: 5000)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Maximum concurrent agent workers (default: 4)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("=" * 60)
    logger.info("Agent Arena - User Agent Runner")
    logger.info("=" * 60)
    logger.info(f"Simulation: {args.host}:{args.port}")
    logger.info(f"Max Workers: {args.workers}")
    logger.info("=" * 60)

    try:
        # TODO: Import your agent here
        # Example agents are provided - uncomment one to use:
        # from user_agents.examples import SimpleForager
        # from user_agents.examples import SimpleForagerSimple

        # Or create your own:
        # from user_agents.my_agent import MyForagingAgent

        # Connect to simulation
        arena = AgentArena.connect(host=args.host, port=args.port, max_workers=args.workers)

        # TODO: Register your agents here
        # Example using provided agents:
        # arena.register('agent_001', SimpleForager())
        # arena.register('agent_001', SimpleForagerSimple())

        # Or use your own:
        # arena.register('agent_001', MyForagingAgent())
        # arena.register('agent_002', MyForagingAgent())

        # Check if any agents were registered
        registered = arena.get_registered_agents()
        if not registered:
            logger.error("No agents registered!")
            logger.error("")
            logger.error("To use this script:")
            logger.error("1. Uncomment one of the example agents above, OR")
            logger.error("2. Create your agent in user_agents/")
            logger.error("3. Import it and register it with arena.register()")
            logger.error("")
            logger.error("Quick start with example agents:")
            logger.error("  from user_agents.examples import SimpleForager")
            logger.error("  arena.register('agent_001', SimpleForager())")
            logger.error("")
            logger.error("Or create your own:")
            logger.error("  from user_agents.my_agent import MyAgent")
            logger.error("  arena.register('agent_001', MyAgent())")
            sys.exit(1)

        logger.info(f"Registered agents: {', '.join(registered)}")
        logger.info("Starting arena...")
        logger.info("")

        # Run the arena (blocks until stopped)
        arena.run()

    except KeyboardInterrupt:
        logger.info("\nShutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
