"""
AgentArena - Main connection manager for the SDK.

This provides a simple API for learners to connect their agents to the game.
"""

import logging
from typing import Callable

from .schemas import Decision, Observation
from .server import MinimalIPCServer

logger = logging.getLogger(__name__)


class AgentArena:
    """
    Connection manager for Agent Arena game.

    This is the main entry point for learners. It handles:
    - Starting the IPC server
    - Calling your decide function each tick
    - Managing the connection to Godot

    Example:
        from agent_arena_sdk import AgentArena, Observation, Decision

        def my_decide(obs: Observation) -> Decision:
            if obs.nearby_resources:
                resource = obs.nearby_resources[0]
                return Decision(
                    tool="move_to",
                    params={"target_position": resource.position}
                )
            return Decision.idle()

        arena = AgentArena(host="127.0.0.1", port=5000)
        arena.run(my_decide)  # Blocks until stopped
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 5000,
        enable_debug: bool = False,
    ):
        """
        Initialize AgentArena connection.

        Args:
            host: IPC server host address (default: localhost)
            port: IPC server port (default: 5000)
            enable_debug: Enable /debug/* endpoints for observation tracking,
                trace inspection, and web-based trace viewer at /debug
        """
        self.host = host
        self.port = port
        self.enable_debug = enable_debug
        self.server: MinimalIPCServer | None = None

        logger.info(
            f"Initialized AgentArena for {host}:{port}"
            f"{' (debug enabled)' if enable_debug else ''}"
        )

    def run(self, decide_callback: Callable[[Observation], Decision]) -> None:
        """
        Run the agent server (blocking).

        This starts the IPC server and calls your decide function each tick.
        Blocks until the server is stopped (Ctrl+C).

        Args:
            decide_callback: Function that takes Observation and returns Decision

        Example:
            def decide(obs: Observation) -> Decision:
                return Decision.idle()

            arena = AgentArena()
            arena.run(decide)  # Blocks here
        """
        logger.info("Starting agent server...")
        logger.info("Waiting for connection from Godot...")

        self.server = MinimalIPCServer(
            decide_callback=decide_callback,
            host=self.host,
            port=self.port,
            enable_debug=self.enable_debug,
        )

        try:
            self.server.run()  # Blocks
        except KeyboardInterrupt:
            logger.info("Agent server stopped by user")
        finally:
            logger.info("Agent server shut down")

    async def run_async(self, decide_callback: Callable[[Observation], Decision]) -> None:
        """
        Run the agent server (async).

        This is an async version of run() that can be awaited.

        Args:
            decide_callback: Function that takes Observation and returns Decision

        Example:
            async def main():
                def decide(obs: Observation) -> Decision:
                    return Decision.idle()

                arena = AgentArena()
                await arena.run_async(decide)

            asyncio.run(main())
        """
        logger.info("Starting agent server (async)...")
        logger.info("Waiting for connection from Godot...")

        self.server = MinimalIPCServer(
            decide_callback=decide_callback,
            host=self.host,
            port=self.port,
            enable_debug=self.enable_debug,
        )

        await self.server.run_async()
