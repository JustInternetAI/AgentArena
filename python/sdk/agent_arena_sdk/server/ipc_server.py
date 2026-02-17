"""
Minimal IPC Server for Agent Arena SDK.

This server provides a thin communication layer between Godot and Python agents.
It does NOT include behavior management, tool dispatching, or runtime complexity.
Those features are either handled by Godot (tools) or by learner code (behaviors).
"""

import logging
from typing import Any, Callable

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse

from ..schemas import Decision, Observation

logger = logging.getLogger(__name__)


class MinimalIPCServer:
    """
    Minimal IPC server for SDK.

    This server receives observations from Godot, calls a user-provided
    decision callback, and returns decisions to Godot.

    No behavior management, no tool execution, no runtime complexity.
    Just: observation in → callback → decision out.

    When ``enable_debug`` is True, additional ``/debug/*`` endpoints are
    registered for observation tracking, trace inspection, and a web-based
    trace viewer UI.
    """

    def __init__(
        self,
        decide_callback: Callable[[Observation], Decision],
        host: str = "127.0.0.1",
        port: int = 5000,
        enable_debug: bool = False,
    ):
        """
        Initialize the minimal IPC server.

        Args:
            decide_callback: Function that takes Observation and returns Decision
            host: Host address to bind to
            port: Port to listen on
            enable_debug: Enable /debug/* endpoints for observation tracking,
                trace inspection, and web-based trace viewer
        """
        self.decide_callback = decide_callback
        self.host = host
        self.port = port
        self.enable_debug = enable_debug
        self.app: FastAPI | None = None
        self.metrics = {
            "total_ticks": 0,
            "total_observations": 0,
        }

        # Debug subsystems (created lazily in create_app when enabled)
        self.observation_tracker: Any = None
        self.debug_store: Any = None

    def _init_debug(self) -> None:
        """Initialize debug subsystems."""
        from .debug_middleware import ObservationTracker
        from .debug_store import DebugStore

        self.observation_tracker = ObservationTracker()
        self.debug_store = DebugStore()
        logger.info("Debug mode enabled — /debug/* endpoints available")

    def _track_observation(self, observation: dict[str, Any]) -> None:
        """Track an observation if debug mode is enabled (no-op otherwise)."""
        if self.observation_tracker is not None:
            self.observation_tracker.track_observation(observation)

    def _record_decision_trace(
        self, agent_id: str, obs: "Observation", decision: "Decision"
    ) -> None:
        """Record a reasoning trace for a decision (no-op when debug disabled).

        If the decide callback's agent exposes a ``last_trace`` dict (set by
        the LLM starter agent), the full chain-of-thought is recorded:
        system prompt → user prompt → raw LLM output → parsed JSON → decision.
        """
        if self.debug_store is None:
            return
        try:
            from .debug_store import DebugTrace

            trace = DebugTrace(agent_id=agent_id, tick=obs.tick)

            # Step 1: Observation summary
            trace.add_step("observation", {
                "position": list(obs.position) if obs.position else [],
                "health": obs.health,
                "energy": obs.energy,
                "nearby_resources": len(obs.nearby_resources) if obs.nearby_resources else 0,
                "nearby_hazards": len(obs.nearby_hazards) if obs.nearby_hazards else 0,
            })

            # Check if the agent exposed a chain-of-thought trace
            agent_trace = None
            cb = self.decide_callback
            agent_obj = getattr(cb, "__self__", None)
            if agent_obj is not None:
                agent_trace = getattr(agent_obj, "last_trace", None)

            if agent_trace:
                # Step 2: Prompt sent to LLM
                trace.add_step("prompt", {
                    "system_prompt": agent_trace.get("system_prompt", ""),
                    "user_prompt": agent_trace.get("user_prompt", ""),
                })

                # Step 3: Raw LLM response
                trace.add_step("llm_response", {
                    "raw_output": agent_trace.get("llm_raw_output", ""),
                    "tokens_used": agent_trace.get("tokens_used", 0),
                    "finish_reason": agent_trace.get("finish_reason"),
                })

                # Step 4: Parse result
                trace.add_step("parse", {
                    "method": agent_trace.get("parse_method", "unknown"),
                    "parsed_json": agent_trace.get("parsed_json"),
                })

            # Step 5: Final decision
            trace.add_step("decision", {
                "tool": decision.tool,
                "params": decision.params,
                "reasoning": decision.reasoning,
            })

            self.debug_store.record_trace(trace)
        except Exception as exc:
            logger.debug("Failed to record trace: %s", exc)

    def create_app(self) -> FastAPI:
        """Create and configure the FastAPI application."""
        app = FastAPI(
            title="Agent Arena SDK Server",
            description="Minimal IPC server for Agent Arena",
            version="0.1.0",
        )

        if self.enable_debug:
            self._init_debug()

        @app.get("/")
        async def root() -> dict[str, Any]:
            """Root endpoint."""
            return {
                "status": "running",
                "debug": self.enable_debug,
                "metrics": self.metrics,
            }

        @app.get("/health")
        async def health() -> dict[str, str]:
            """Health check endpoint."""
            return {"status": "ok"}

        @app.post("/observe")
        async def process_observation(observation: dict[str, Any]) -> dict[str, Any]:
            """
            Process a single observation from Godot and return a decision.

            This is the endpoint Godot calls each tick for each agent.
            """
            try:
                agent_id = observation.get("agent_id", "unknown")

                logger.debug(f"[/observe] Processing observation for agent '{agent_id}'")

                # Track observation for debug (no-op when disabled)
                self._track_observation(observation)

                # Parse observation
                obs = Observation.from_dict(observation)

                # Call user's decide callback
                decision = self.decide_callback(obs)

                # Record trace for debug (no-op when disabled)
                self._record_decision_trace(agent_id, obs, decision)

                # Update metrics
                self.metrics["total_ticks"] += 1
                self.metrics["total_observations"] += 1

                result = {
                    "agent_id": agent_id,
                    "tool": decision.tool,
                    "params": decision.params,
                    "reasoning": decision.reasoning or "Agent decision",
                }

                logger.debug(f"Agent {agent_id} decided: {decision.tool}")

                return result

            except Exception as e:
                logger.error(f"Error processing observation: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))

        @app.post("/tools/execute")
        async def execute_tool(request_data: dict[str, Any]) -> dict[str, Any]:
            """
            Acknowledge a tool execution request from Godot.

            In the new SDK architecture, Godot executes tools directly.
            This endpoint exists for backward compatibility so Godot doesn't
            get 404 errors while it still calls this endpoint.
            """
            tool_name = request_data.get("tool_name", "unknown")
            agent_id = request_data.get("agent_id", "unknown")
            logger.debug(
                f"[/tools/execute] Acknowledging tool '{tool_name}' " f"for agent '{agent_id}'"
            )
            return {
                "success": True,
                "result": None,
                "error": "",
            }

        @app.post("/tick")
        async def process_tick(request_data: dict[str, Any]) -> dict[str, Any]:
            """
            Process a simulation tick.

            Receives observation(s), calls decide callback, returns action(s).
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

                    # Track observation for debug (no-op when disabled)
                    self._track_observation(obs_data)

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

        # ---------------------------------------------------------------
        # Debug endpoints (only registered when enable_debug=True)
        # ---------------------------------------------------------------
        if self.enable_debug:
            self._register_debug_endpoints(app)

        self.app = app
        return app

    def _register_debug_endpoints(self, app: FastAPI) -> None:
        """Register all /debug/* endpoints on the FastAPI app."""

        # -- Web UI --

        @app.get("/debug", response_class=HTMLResponse)
        async def debug_viewer() -> str:
            """Serve the web-based trace viewer UI."""
            from .web_ui import get_debug_viewer_html

            return get_debug_viewer_html()

        # -- Observations --

        @app.get("/debug/observations")
        async def get_observations(
            limit: int = Query(50, ge=1, le=1000),
            agent_id: str | None = Query(None),
        ) -> dict[str, Any]:
            """Get recent observations with visibility tracking."""
            observations = self.observation_tracker.get_recent(limit, agent_id)
            return {"observations": observations, "count": len(observations)}

        @app.get("/debug/changes")
        async def get_changes(
            limit: int = Query(50, ge=1, le=1000),
            agent_id: str | None = Query(None),
        ) -> dict[str, Any]:
            """Get observations where visibility changed."""
            changes = self.observation_tracker.get_changes(limit, agent_id)
            return {"changes": changes, "count": len(changes)}

        @app.post("/debug/reset")
        async def reset_observations() -> dict[str, str]:
            """Clear observation tracking history."""
            self.observation_tracker.clear()
            return {"status": "reset"}

        # -- Traces --

        @app.get("/debug/traces")
        async def get_traces(
            limit: int = Query(50, ge=1, le=1000),
            agent_id: str | None = Query(None),
            tick_start: int | None = Query(None),
            tick_end: int | None = Query(None),
        ) -> dict[str, Any]:
            """Get recent reasoning traces from hybrid storage."""
            traces = self.debug_store.get_recent_traces(
                limit=limit,
                agent_id=agent_id,
                tick_start=tick_start,
                tick_end=tick_end,
            )
            return {"traces": traces, "count": len(traces)}

        @app.get("/debug/prompts")
        async def get_prompts(
            agent_id: str | None = Query(None),
            tick: int | None = Query(None),
            tick_start: int | None = Query(None),
            tick_end: int | None = Query(None),
        ) -> dict[str, Any]:
            """Get LLM prompt/response captures."""
            captures = self.debug_store.get_captures(
                agent_id=agent_id,
                tick=tick,
                tick_start=tick_start,
                tick_end=tick_end,
            )
            return {"captures": captures, "count": len(captures)}

        @app.get("/debug/agents")
        async def list_agents() -> dict[str, Any]:
            """List all agents seen in traces or observations."""
            agents_set = set(self.debug_store.list_agents())
            # Also include agents seen by the observation tracker
            if self.observation_tracker is not None:
                with self.observation_tracker._lock:
                    agents_set.update(self.observation_tracker._last_visible.keys())
            return {"agents": sorted(agents_set)}

        @app.get("/debug/episodes")
        async def list_episodes(
            agent_id: str = Query(..., description="Agent ID"),
        ) -> dict[str, Any]:
            """List episodes for an agent."""
            episodes = self.debug_store.list_episodes(agent_id)
            return {"agent_id": agent_id, "episodes": episodes}

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
