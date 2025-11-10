"""
IPC Server - FastAPI server for handling Godot <-> Python communication.

This server receives perception data from Godot, processes agent decisions,
and returns actions to execute in the simulation.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from agent_runtime.runtime import AgentRuntime
from .messages import ActionMessage, TickRequest, TickResponse

logger = logging.getLogger(__name__)


class IPCServer:
    """
    IPC Server for handling communication between Godot and Python.

    Runs a FastAPI server that receives tick requests and returns agent actions.
    """

    def __init__(
        self,
        runtime: AgentRuntime,
        host: str = "127.0.0.1",
        port: int = 5000,
    ):
        """
        Initialize the IPC server.

        Args:
            runtime: AgentRuntime instance to process agent decisions
            host: Host address to bind to
            port: Port to listen on
        """
        self.runtime = runtime
        self.host = host
        self.port = port
        self.app: FastAPI | None = None
        self.metrics = {
            "total_ticks": 0,
            "total_agents_processed": 0,
            "avg_tick_time_ms": 0.0,
        }

    def create_app(self) -> FastAPI:
        """Create and configure the FastAPI application."""

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            """Lifespan context manager for startup/shutdown."""
            logger.info("Starting IPC server...")
            self.runtime.start()
            yield
            logger.info("Shutting down IPC server...")
            self.runtime.stop()

        app = FastAPI(
            title="Agent Arena IPC Server",
            description="Communication bridge between Godot simulation and Python agents",
            version="0.1.0",
            lifespan=lifespan,
        )

        @app.get("/")
        async def root():
            """Health check endpoint."""
            return {
                "status": "running",
                "agents": len(self.runtime.agents),
                "metrics": self.metrics,
            }

        @app.get("/health")
        async def health():
            """Health check endpoint."""
            return {"status": "ok", "agents": len(self.runtime.agents)}

        @app.post("/tick")
        async def process_tick(request_data: dict[str, Any]) -> dict[str, Any]:
            """
            Process a simulation tick.

            Receives perception data for all agents, processes decisions,
            and returns actions to execute.

            Args:
                request_data: Tick request containing agent perceptions

            Returns:
                Tick response containing agent actions
            """
            start_time = time.time()

            try:
                # Parse request
                tick_request = TickRequest.from_dict(request_data)
                tick = tick_request.tick

                logger.debug(f"Processing tick {tick} with {len(tick_request.perceptions)} agents")

                # Build observations dict for runtime
                observations = {}
                for perception in tick_request.perceptions:
                    observations[perception.agent_id] = {
                        "tick": perception.tick,
                        "position": perception.position,
                        "rotation": perception.rotation,
                        "velocity": perception.velocity,
                        "visible_entities": perception.visible_entities,
                        "inventory": perception.inventory,
                        "health": perception.health,
                        "energy": perception.energy,
                        "custom_data": perception.custom_data,
                    }

                # Process agents and get actions
                actions_dict = await self.runtime.process_tick(tick, observations)

                # Convert actions to response format
                action_messages = []
                for agent_id, action in actions_dict.items():
                    action_msg = ActionMessage(
                        agent_id=agent_id,
                        tick=tick,
                        tool=action.tool,
                        params=action.params,
                        reasoning=action.reasoning,
                    )
                    action_messages.append(action_msg)

                # Calculate metrics
                elapsed_ms = (time.time() - start_time) * 1000
                self.metrics["total_ticks"] += 1
                self.metrics["total_agents_processed"] += len(observations)
                self.metrics["avg_tick_time_ms"] = (
                    self.metrics["avg_tick_time_ms"] * 0.9 + elapsed_ms * 0.1
                )

                # Build response
                response = TickResponse(
                    tick=tick,
                    actions=action_messages,
                    metrics={
                        "tick_time_ms": elapsed_ms,
                        "agents_processed": len(observations),
                        "actions_generated": len(action_messages),
                    },
                )

                logger.debug(
                    f"Tick {tick} processed in {elapsed_ms:.2f}ms, "
                    f"{len(action_messages)} actions generated"
                )

                return response.to_dict()

            except Exception as e:
                logger.error(f"Error processing tick: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))

        @app.post("/agents/register")
        async def register_agent(agent_data: dict[str, Any]) -> dict[str, str]:
            """
            Register a new agent with the runtime.

            Args:
                agent_data: Agent configuration data

            Returns:
                Success message with agent ID
            """
            try:
                agent_id = agent_data.get("agent_id")
                if not agent_id:
                    raise HTTPException(status_code=400, detail="agent_id is required")

                # Note: Agent instantiation would happen here
                # For now, we'll just acknowledge the registration
                logger.info(f"Agent registration request received for {agent_id}")

                return {"status": "success", "agent_id": agent_id}

            except Exception as e:
                logger.error(f"Error registering agent: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @app.get("/metrics")
        async def get_metrics():
            """Get server performance metrics."""
            return self.metrics

        self.app = app
        return app

    def run(self):
        """Run the IPC server (blocking)."""
        import uvicorn

        if not self.app:
            self.create_app()

        logger.info(f"Starting IPC server on {self.host}:{self.port}")
        uvicorn.run(self.app, host=self.host, port=self.port, log_level="info")

    async def run_async(self):
        """Run the IPC server asynchronously."""
        import uvicorn

        if not self.app:
            self.create_app()

        config = uvicorn.Config(self.app, host=self.host, port=self.port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()


def create_server(
    runtime: AgentRuntime | None = None,
    host: str = "127.0.0.1",
    port: int = 5000,
) -> IPCServer:
    """
    Factory function to create an IPC server.

    Args:
        runtime: AgentRuntime instance, or None to create a default one
        host: Host address to bind to
        port: Port to listen on

    Returns:
        Configured IPCServer instance
    """
    if runtime is None:
        runtime = AgentRuntime(max_workers=4)

    return IPCServer(runtime=runtime, host=host, port=port)
