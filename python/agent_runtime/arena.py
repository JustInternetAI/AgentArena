"""
AgentArena - Main orchestrator for running agents in simulation.
"""

import logging
from typing import TYPE_CHECKING

from .runtime import AgentRuntime

if TYPE_CHECKING:
    from ipc.server import IPCServer

    from .behavior import AgentBehavior

logger = logging.getLogger(__name__)


class AgentArena:
    """
    Main orchestrator connecting user agents to Godot simulation.

    AgentArena provides a simple API for users to:
    - Register their agent behaviors
    - Connect to the Godot simulation
    - Run the agent decision loop

    Example:
        from agent_runtime import AgentArena
        from my_agents import ForagingAgent

        # Create arena and register agents
        arena = AgentArena()
        arena.register('agent_001', ForagingAgent())

        # Connect to simulation and run
        arena.connect(host='127.0.0.1', port=5000)
        arena.run()  # Blocks until simulation ends

    Example (class method):
        # Alternatively, connect first then register
        arena = AgentArena.connect(host='127.0.0.1', port=5000)
        arena.register('agent_001', ForagingAgent())
        arena.run()
    """

    def __init__(self, max_workers: int = 4):
        """
        Initialize AgentArena.

        Args:
            max_workers: Maximum number of concurrent agent workers
        """
        self.runtime = AgentRuntime(max_workers=max_workers)
        self.behaviors: dict[str, "AgentBehavior"] = {}
        self.ipc_server: "IPCServer | None" = None
        self._running = False

        logger.info(f"Initialized AgentArena with {max_workers} workers")

    @classmethod
    def connect(
        cls, host: str = "127.0.0.1", port: int = 5000, max_workers: int = 4
    ) -> "AgentArena":
        """
        Create arena and immediately connect to Godot simulation.

        Args:
            host: IPC server host address
            port: IPC server port
            max_workers: Maximum number of concurrent agent workers

        Returns:
            Connected AgentArena instance

        Example:
            arena = AgentArena.connect()
            arena.register('agent_001', MyAgent())
            arena.run()
        """
        arena = cls(max_workers=max_workers)
        arena._connect(host=host, port=port)
        return arena

    def _connect(self, host: str = "127.0.0.1", port: int = 5000) -> None:
        """
        Internal method to establish IPC connection.

        Args:
            host: IPC server host address
            port: IPC server port
        """
        from ipc.server import create_server

        logger.info(f"Connecting to Godot simulation at {host}:{port}")

        # Create IPC server with this arena's runtime and behaviors
        self.ipc_server = create_server(
            runtime=self.runtime, behaviors=self.behaviors, host=host, port=port
        )

        # Create FastAPI app
        self.ipc_server.create_app()

        logger.info("Connected to Godot simulation")

    def register(self, agent_id: str, behavior: "AgentBehavior") -> None:
        """
        Register an agent behavior for the given ID.

        The behavior will be called each tick to make decisions for this agent.

        Args:
            agent_id: Unique identifier for the agent (matches Godot agent ID)
            behavior: AgentBehavior instance implementing decide() method

        Example:
            arena.register('agent_001', MyForagingAgent())
            arena.register('agent_002', MyCombatAgent())
        """
        if agent_id in self.behaviors:
            logger.warning(f"Replacing existing behavior for agent {agent_id}")

        self.behaviors[agent_id] = behavior
        logger.info(f"Registered behavior for agent {agent_id}: {type(behavior).__name__}")

    def unregister(self, agent_id: str) -> None:
        """
        Unregister an agent.

        Args:
            agent_id: ID of agent to unregister
        """
        if agent_id in self.behaviors:
            del self.behaviors[agent_id]
            logger.info(f"Unregistered agent {agent_id}")
        else:
            logger.warning(f"Cannot unregister agent {agent_id}: not found")

    def run(self) -> None:
        """
        Run the main tick loop (blocking).

        This starts the IPC server and blocks until stopped.
        The server will handle incoming tick requests from Godot and
        call the registered agent behaviors to make decisions.

        Example:
            arena = AgentArena.connect()
            arena.register('agent_001', MyAgent())
            arena.run()  # Blocks here
        """
        if not self.ipc_server:
            raise RuntimeError(
                "Not connected to simulation. Call connect() or use AgentArena.connect() first."
            )

        if not self.behaviors:
            logger.warning("No agent behaviors registered. Did you forget to call register()?")

        logger.info(f"Starting arena with {len(self.behaviors)} registered agents")
        self._running = True

        try:
            # Run the IPC server (blocking)
            self.ipc_server.run()
        except KeyboardInterrupt:
            logger.info("Arena stopped by user")
        finally:
            self._running = False
            self.runtime.stop()

    async def run_async(self) -> None:
        """
        Run tick loop in background (async).

        This is an async version of run() that can be awaited.

        Example:
            arena = AgentArena.connect()
            arena.register('agent_001', MyAgent())
            await arena.run_async()
        """
        if not self.ipc_server:
            raise RuntimeError(
                "Not connected to simulation. Call connect() or use AgentArena.connect() first."
            )

        if not self.behaviors:
            logger.warning("No agent behaviors registered. Did you forget to call register()?")

        logger.info(f"Starting arena with {len(self.behaviors)} registered agents")
        self._running = True

        try:
            await self.ipc_server.run_async()
        finally:
            self._running = False
            self.runtime.stop()

    def stop(self) -> None:
        """
        Stop the tick loop.

        This can be called from another thread to stop a running arena.
        """
        logger.info("Stopping arena...")
        self._running = False
        if self.runtime:
            self.runtime.stop()

    def is_running(self) -> bool:
        """
        Check if arena is currently running.

        Returns:
            True if running, False otherwise
        """
        return self._running

    def get_registered_agents(self) -> list[str]:
        """
        Get list of registered agent IDs.

        Returns:
            List of agent IDs
        """
        return list(self.behaviors.keys())

    def get_behavior(self, agent_id: str) -> "AgentBehavior | None":
        """
        Get the behavior registered for an agent.

        Args:
            agent_id: Agent ID

        Returns:
            AgentBehavior instance or None if not found
        """
        return self.behaviors.get(agent_id)
