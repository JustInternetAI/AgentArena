"""
IPC Server - FastAPI server for handling Godot <-> Python communication.

This server receives perception data from Godot, processes agent decisions,
and returns actions to execute in the simulation.
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException

from agent_runtime.behavior import AgentBehavior
from agent_runtime.runtime import AgentRuntime
from agent_runtime.schemas import ToolSchema
from agent_runtime.tool_dispatcher import ToolDispatcher
from tools import register_inventory_tools, register_movement_tools, register_world_query_tools

from .converters import decision_to_action, perception_to_observation
from .messages import (
    ActionMessage,
    TickRequest,
    TickResponse,
    ToolExecutionRequest,
    ToolExecutionResponse,
)

logger = logging.getLogger(__name__)


class IPCServer:
    """
    IPC Server for handling communication between Godot and Python.

    Runs a FastAPI server that receives tick requests and returns agent actions.
    """

    def __init__(
        self,
        runtime: AgentRuntime,
        behaviors: dict | None = None,
        default_behavior: "AgentBehavior | None" = None,
        host: str = "127.0.0.1",
        port: int = 5000,
    ):
        """
        Initialize the IPC server.

        Args:
            runtime: AgentRuntime instance to process agent decisions
            behaviors: Dictionary of agent_id -> AgentBehavior instances
            default_behavior: Default behavior to use for unregistered agents
            host: Host address to bind to
            port: Port to listen on
        """
        self.runtime = runtime
        self.behaviors = behaviors if behaviors is not None else {}
        self.default_behavior = default_behavior
        self.host = host
        self.port = port
        self.app: FastAPI | None = None
        self.tool_dispatcher = ToolDispatcher()
        self._register_all_tools()
        self.metrics = {
            "total_ticks": 0,
            "total_agents_processed": 0,
            "avg_tick_time_ms": 0.0,
            "total_tools_executed": 0,
            "total_observations_processed": 0,
        }

    def _register_all_tools(self) -> None:
        """Register all available tools with the dispatcher."""
        register_movement_tools(self.tool_dispatcher)
        register_inventory_tools(self.tool_dispatcher)
        register_world_query_tools(self.tool_dispatcher)
        logger.info(f"Registered {len(self.tool_dispatcher.tools)} tools")

    def _make_mock_decision(self, observation: dict[str, Any]) -> dict[str, Any]:
        """
        Generate a mock decision based on observation using rule-based logic.

        This is a simple decision-making system for testing the observation-decision
        loop without requiring LLM inference.

        Priority:
        1. Avoid nearby hazards (distance < 3.0)
        2. Move to nearest resource (distance < 5.0)
        3. Default to idle

        Args:
            observation: Observation dictionary with nearby_resources and nearby_hazards

        Returns:
            Decision dictionary with tool, params, and reasoning
        """
        nearby_resources = observation.get("nearby_resources", [])
        nearby_hazards = observation.get("nearby_hazards", [])

        # Priority 1: Avoid hazards that are too close
        for hazard in nearby_hazards:
            distance = hazard.get("distance", float("inf"))
            if distance < 3.0:
                hazard_pos = hazard.get("position", [0, 0, 0])
                hazard_type = hazard.get("type", "unknown")

                # Calculate a safe position away from the hazard using move_to
                agent_pos = observation.get("position", [0, 0, 0])

                # Vector from hazard to agent
                dx = agent_pos[0] - hazard_pos[0]
                dz = agent_pos[2] - hazard_pos[2]

                # Normalize and scale to move 5 units away from hazard
                length = (dx**2 + dz**2) ** 0.5
                if length > 0:
                    dx = (dx / length) * 5.0
                    dz = (dz / length) * 5.0
                else:
                    # If on top of hazard, move in arbitrary direction
                    dx, dz = 5.0, 0.0

                safe_position = [
                    hazard_pos[0] + dx,
                    agent_pos[1],  # Keep same Y
                    hazard_pos[2] + dz,
                ]

                return {
                    "tool": "move_to",
                    "params": {"target_position": safe_position, "speed": 2.0},
                    "reasoning": f"Avoiding nearby {hazard_type} hazard at distance {distance:.1f}",
                }

        # Priority 2: Move to nearest resource if within range
        if nearby_resources:
            # Find closest resource
            closest_resource = min(nearby_resources, key=lambda r: r.get("distance", float("inf")))
            distance = closest_resource.get("distance", float("inf"))

            if distance < 5.0:
                resource_pos = closest_resource.get("position", [0, 0, 0])
                resource_type = closest_resource.get("type", "unknown")
                resource_name = closest_resource.get("name", "resource")
                return {
                    "tool": "move_to",
                    "params": {"target_position": resource_pos, "speed": 1.5},
                    "reasoning": f"Moving to collect {resource_type} ({resource_name}) at distance {distance:.1f}",
                }

        # Default: Idle (no immediate actions needed)
        return {
            "tool": "idle",
            "params": {},
            "reasoning": "No immediate actions needed - exploring environment",
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

                logger.info(
                    f"[/tick] Processing tick {tick} with {len(tick_request.perceptions)} agents"
                )

                # Get tool schemas for agents
                tool_schemas = []
                for name, schema in self.tool_dispatcher.schemas.items():
                    tool_schemas.append(
                        ToolSchema(
                            name=schema.name,
                            description=schema.description,
                            parameters=schema.parameters,
                        )
                    )

                # Process each agent using registered behaviors
                action_messages = []
                for perception in tick_request.perceptions:
                    agent_id = perception.agent_id

                    # Convert perception to Observation
                    observation = perception_to_observation(perception)

                    # Get behavior for this agent (or use default)
                    behavior = self.behaviors.get(agent_id) or self.default_behavior

                    # If no specific behavior, check for default behavior
                    if behavior is None and "_default" in self.behaviors:
                        behavior = self.behaviors["_default"]
                        logger.debug(f"Using default behavior for agent {agent_id}")

                    if behavior:
                        # Call behavior.decide() with Observation and tools
                        try:
                            decision = behavior.decide(observation, tool_schemas)

                            # Convert decision to ActionMessage
                            action_msg = decision_to_action(decision, agent_id, tick)
                            action_messages.append(action_msg)

                            logger.info(
                                f"[/tick] Agent {agent_id} decided: {decision.tool} - {decision.reasoning}"
                            )
                        except Exception as e:
                            logger.error(
                                f"Error in behavior.decide() for agent {agent_id}: {e}",
                                exc_info=True,
                            )
                            # Fallback to idle
                            from agent_runtime.schemas import AgentDecision

                            decision = AgentDecision.idle(reasoning=f"Error: {str(e)}")
                            action_msg = decision_to_action(decision, agent_id, tick)
                            action_messages.append(action_msg)
                    else:
                        # No behavior registered, use mock decision
                        logger.warning(
                            f"No behavior registered for agent {agent_id}, using mock decision"
                        )
                        mock_obs = {
                            "agent_id": agent_id,
                            "position": perception.position,
                            "nearby_resources": perception.custom_data.get("nearby_resources", []),
                            "nearby_hazards": perception.custom_data.get("nearby_hazards", []),
                        }
                        decision_dict = self._make_mock_decision(mock_obs)
                        action_msg = ActionMessage(
                            agent_id=agent_id,
                            tick=tick,
                            tool=decision_dict["tool"],
                            params=decision_dict["params"],
                            reasoning=decision_dict["reasoning"],
                        )
                        action_messages.append(action_msg)

                # Calculate metrics
                elapsed_ms = (time.time() - start_time) * 1000
                self.metrics["total_ticks"] += 1
                self.metrics["total_agents_processed"] += len(tick_request.perceptions)
                self.metrics["avg_tick_time_ms"] = (
                    self.metrics["avg_tick_time_ms"] * 0.9 + elapsed_ms * 0.1
                )

                # Build response
                response = TickResponse(
                    tick=tick,
                    actions=action_messages,
                    metrics={
                        "tick_time_ms": elapsed_ms,
                        "agents_processed": len(tick_request.perceptions),
                        "actions_generated": len(action_messages),
                    },
                )

                logger.info(
                    f"[/tick] Tick {tick} processed in {elapsed_ms:.2f}ms, "
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

        @app.post("/tools/execute")
        async def execute_tool(request_data: dict[str, Any]) -> dict[str, Any]:
            """
            Execute a tool requested from Godot.

            Args:
                request_data: Tool execution request

            Returns:
                Tool execution response with result or error
            """
            try:
                # Parse request
                tool_request = ToolExecutionRequest.from_dict(request_data)

                logger.debug(
                    f"Executing tool '{tool_request.tool_name}' "
                    f"for agent '{tool_request.agent_id}' at tick {tool_request.tick}"
                )

                # Execute the tool through dispatcher
                result = self.tool_dispatcher.execute_tool(
                    tool_request.tool_name, tool_request.params
                )

                # Update metrics
                self.metrics["total_tools_executed"] += 1

                # Build response
                response = ToolExecutionResponse(
                    success=result.get("success", False),
                    result=result.get("result"),
                    error=result.get("error", ""),
                )

                logger.debug(
                    f"Tool '{tool_request.tool_name}' executed: success={response.success}"
                )

                return response.to_dict()

            except Exception as e:
                logger.error(f"Error executing tool: {e}", exc_info=True)
                return ToolExecutionResponse(success=False, error=str(e)).to_dict()

        @app.get("/tools/list")
        async def list_tools() -> dict[str, Any]:
            """Get list of available tools and their schemas."""
            logger.info("[/tools/list] Tools requested")
            schemas = {}
            for name, schema in self.tool_dispatcher.schemas.items():
                schemas[name] = {
                    "name": schema.name,
                    "description": schema.description,
                    "parameters": schema.parameters,
                    "returns": schema.returns,
                }
            logger.info(f"[/tools/list] Returning {len(schemas)} tools")
            return {"tools": schemas, "count": len(schemas)}

        @app.get("/metrics")
        async def get_metrics():
            """Get server performance metrics."""
            return self.metrics

        @app.post("/observe")
        async def process_observation(observation: dict[str, Any]) -> dict[str, Any]:
            """
            Process a single observation and return a decision.

            This endpoint supports both registered behaviors and mock logic:
            - If a behavior is registered for the agent_id, it will be used
            - Otherwise, falls back to rule-based mock logic

            Args:
                observation: Observation data containing:
                    - agent_id: Agent identifier
                    - position: [x, y, z] position
                    - nearby_resources: List of visible resources
                    - nearby_hazards: List of nearby hazards

            Returns:
                Decision dictionary with tool, params, and reasoning
            """
            try:
                agent_id = observation.get("agent_id", "unknown")

                logger.info(f"[/observe] Processing observation for agent '{agent_id}'")
                logger.debug(f"Position: {observation.get('position')}")
                logger.debug(f"Resources: {len(observation.get('nearby_resources', []))}")
                logger.debug(f"Hazards: {len(observation.get('nearby_hazards', []))}")

                # Check if we have a registered behavior for this agent (or use default)
                behavior = self.behaviors.get(agent_id) or self.default_behavior

                if behavior:
                    # Log which behavior type is being used
                    behavior_type = "registered" if agent_id in self.behaviors else "default"
                    logger.info(f"[/observe] Using {behavior_type} behavior for agent '{agent_id}'")
                    # Convert observation dict to Observation object
                    from ipc.messages import PerceptionMessage

                    from .converters import perception_to_observation

                    # Create PerceptionMessage from observation dict
                    perception = PerceptionMessage(
                        agent_id=agent_id,
                        tick=observation.get("tick", 0),
                        position=observation.get("position", [0, 0, 0]),
                        rotation=observation.get("rotation", [0, 0, 0]),
                        velocity=observation.get("velocity", [0, 0, 0]),
                        custom_data={
                            "nearby_resources": observation.get("nearby_resources", []),
                            "nearby_hazards": observation.get("nearby_hazards", []),
                            "inventory": observation.get("inventory", []),
                            "health": observation.get("health", 100.0),
                            "energy": observation.get("energy", 100.0),
                        },
                    )

                    obs = perception_to_observation(perception)

                    # Get tool schemas
                    tool_schemas = []
                    for name, schema in self.tool_dispatcher.schemas.items():
                        tool_schemas.append(
                            ToolSchema(
                                name=schema.name,
                                description=schema.description,
                                parameters=schema.parameters,
                            )
                        )

                    try:
                        # Call behavior.decide()
                        agent_decision = behavior.decide(obs, tool_schemas)

                        decision = {
                            "tool": agent_decision.tool,
                            "params": agent_decision.params,
                            "reasoning": agent_decision.reasoning or "Agent decision",
                        }
                    except Exception as e:
                        logger.error(f"Error in behavior.decide(): {e}", exc_info=True)
                        decision = {
                            "tool": "idle",
                            "params": {},
                            "reasoning": f"Error: {str(e)}",
                        }
                else:
                    # Generate mock decision using rule-based logic
                    decision = self._make_mock_decision(observation)

                # Update metrics
                self.metrics["total_observations_processed"] += 1

                logger.info(
                    f"Agent {agent_id} decision: {decision['tool']} - {decision['reasoning']}"
                )

                return {
                    "agent_id": agent_id,
                    "tool": decision["tool"],
                    "params": decision["params"],
                    "reasoning": decision["reasoning"],
                }

            except Exception as e:
                logger.error(f"Error processing observation: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))

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
    behaviors: dict | None = None,
    default_behavior: AgentBehavior | None = None,
    host: str = "127.0.0.1",
    port: int = 5000,
) -> IPCServer:
    """
    Factory function to create an IPC server.

    Args:
        runtime: AgentRuntime instance, or None to create a default one
        behaviors: Dictionary of agent_id -> AgentBehavior instances
        default_behavior: Default behavior to use for agents not in behaviors dict
        host: Host address to bind to
        port: Port to listen on

    Returns:
        Configured IPCServer instance

    Example:
        from agent_runtime import create_local_llm_behavior

        # Create a default LLM behavior for all agents
        default = create_local_llm_behavior(
            model_path="models/mistral-7b.gguf",
            system_prompt="You are a foraging agent."
        )

        server = create_server(default_behavior=default)
    """
    if runtime is None:
        runtime = AgentRuntime(max_workers=4)

    return IPCServer(
        runtime=runtime,
        behaviors=behaviors,
        default_behavior=default_behavior,
        host=host,
        port=port,
    )
