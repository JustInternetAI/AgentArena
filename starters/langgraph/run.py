"""
LangGraph Agent Runner

Starts a LangGraph-powered agent that connects to the Agent Arena game.

Prerequisites:
    export ANTHROPIC_API_KEY=sk-ant-...   # Your Anthropic API key
    pip install -r requirements.txt

Usage:
    python run.py                                    # Default (Sonnet)
    python run.py --model claude-haiku-4-5-20251001  # Fastest / cheapest
    python run.py --debug                            # Enable debug viewer
"""

import argparse
import logging

from agent_arena_sdk import AgentArena

from agent import LangGraphAdapter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Run LangGraph-powered agent")
    parser.add_argument(
        "--model",
        type=str,
        default="claude-sonnet-4-20250514",
        help="Model ID (default: claude-sonnet-4-20250514)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port to listen on (default: 5000)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable /debug/* endpoints and web trace viewer",
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("  LangGraph Agent for Agent Arena")
    logger.info(f"  Model : {args.model}")
    logger.info(f"  Port  : {args.port}")
    logger.info(f"  Debug : {'ON' if args.debug else 'OFF'}")
    logger.info("=" * 60)

    adapter = LangGraphAdapter(model=args.model)

    arena = AgentArena(
        host="127.0.0.1",
        port=args.port,
        enable_debug=args.debug,
    )

    try:
        arena.run(adapter)
    except KeyboardInterrupt:
        logger.info("\nAgent stopped by user")


if __name__ == "__main__":
    main()
