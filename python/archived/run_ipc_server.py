"""
Startup script for the Agent Arena IPC server.

This script starts the FastAPI server that handles communication
between Godot and Python agents.
"""

import argparse
import logging
import sys

from agent_runtime.runtime import AgentRuntime
from ipc.server import create_server

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Agent Arena IPC Server - Communication bridge between Godot and Python"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host address to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port to listen on (default: 5000)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Maximum number of concurrent agent workers (default: 4)",
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
    logger.info("Agent Arena IPC Server")
    logger.info("=" * 60)
    logger.info(f"Host: {args.host}")
    logger.info(f"Port: {args.port}")
    logger.info(f"Max Workers: {args.workers}")
    logger.info("=" * 60)

    try:
        # Create runtime
        runtime = AgentRuntime(max_workers=args.workers)

        # Create and start server
        server = create_server(runtime=runtime, host=args.host, port=args.port)
        logger.info("Starting IPC server...")
        server.run()

    except KeyboardInterrupt:
        logger.info("\nShutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
