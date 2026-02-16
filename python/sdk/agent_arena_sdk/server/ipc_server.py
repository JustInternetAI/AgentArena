"""
Minimal IPC Server for Agent Arena SDK.

This server provides a thin communication layer between Godot and Python agents.
It does NOT include behavior management, tool dispatching, or runtime complexity.
Those features are either handled by Godot (tools) or by learner code (behaviors).
"""

import logging
from typing import Any, Callable

import uvicorn
from fastapi import FastAPI, HTTPException

from ..schemas import Decision, Observation

logger = logging.getLogger(__name__)


class MinimalIPCServer:
    """
    Minimal IPC server for SDK.

    This server receives observations from Godot, calls a user-provided
    decision callback, and returns decisions to Godot.

    No behavior management, no tool execution, no runtime complexity.
    Just: observation in → callback → decision out.
    """

    def __init__(
        self,
        decide_callback: Callable[[Observation], Decision],
        host: str = "127.0.0.1",
        port: int = 5000,
    ):
        """
        Initialize the minimal IPC server.

        Args:
            decide_callback: Function that takes Observation and returns Decision
            host: Host address to bind to
            port: Port to listen on
        """
        self.decide_callback = decide_callback
        self.host = host
        self.port = port
        self.app: FastAPI | None = None
        self.metrics = {
            "total_ticks": 0,
            "total_observations": 0,
        }

    def create_app(self) -> FastAPI:
        """Create and configure the FastAPI application."""
        app = FastAPI(
            title="Agent Arena SDK Server",
            description="Minimal IPC server for Agent Arena",
            version="0.1.0",
        )

        @app.get("/")
        async def root():
            """Root endpoint."""
            return {
                "status": "running",
                "metrics": self.metrics,
            }

        @app.get("/health")
        async def health():
            """Health check endpoint."""
            return {"status": "ok"}

        @app.post("/tick")
        async def process_tick(request_data: dict[str, Any]) -> dict[str, Any]:
            """
            Process a simulation tick.

            Receives observation(s), calls decide callback, returns action(s).

            Args:
                request_data: Tick request with format:
                    {
                        "tick": int,
                        "agents": [
                            {
                                "agent_id": str,
                                "observations": {...observation data...}
                            }
                        ]
                    }

            Returns:
                Tick response with format:
                    {
                        "tick": int,
                        "actions": [
                            {
                                "agent_id": str,
                                "action": {...decision data...}
                            }
                        ]
                    }
            """
            try:
                tick = request_data.get("tick", 0)
                agents_data = request_data.get("agents", [])

                logger.debug(f"Processing tick {tick} with {len(agents_data)} agents")

                actions = []
                for agent_data in agents_data:
                    agent_id = agent_data.get("agent_id")
                    obs_data = agent_data.get("observations", {})

                    # Add agent_id and tick to observation data if not present
                    if "agent_id" not in obs_data:
                        obs_data["agent_id"] = agent_id
                    if "tick" not in obs_data:
                        obs_data["tick"] = tick

                    try:
                        # Parse observation
                        observation = Observation.from_dict(obs_data)

                        # Call user's decide callback
                        decision = self.decide_callback(observation)

                        # Convert decision to action format
                        action_data = {
                            "agent_id": agent_id,
                            "action": decision.to_dict(),
                        }
                        actions.append(action_data)

                        logger.debug(f"Agent {agent_id} decided: {decision.tool}")

                    except Exception as e:
                        logger.error(
                            f"Error processing agent {agent_id}: {e}",
                            exc_info=True,
                        )
                        # Fallback to idle
                        action_data = {
                            "agent_id": agent_id,
                            "action": Decision.idle(reasoning=f"Error: {str(e)}").to_dict(),
                        }
                        actions.append(action_data)

                # Update metrics
                self.metrics["total_ticks"] += 1
                self.metrics["total_observations"] += len(agents_data)

                response = {
                    "tick": tick,
                    "actions": actions,
                }

                return response

            except Exception as e:
                logger.error(f"Error processing tick: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))

        self.app = app
        return app

    def run(self) -> None:
        """
        Run the IPC server (blocking).

        This starts the FastAPI server and blocks until stopped.
        """
        if not self.app:
            self.create_app()

        logger.info(f"Starting SDK IPC server at {self.host}:{self.port}")

        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info",
        )

    async def run_async(self) -> None:
        """
        Run the IPC server (async).

        This is an async version that can be awaited.
        """
        if not self.app:
            self.create_app()

        logger.info(f"Starting SDK IPC server at {self.host}:{self.port}")

        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info",
        )
        server = uvicorn.Server(config)
        await server.serve()
