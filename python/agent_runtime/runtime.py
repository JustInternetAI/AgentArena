"""
Agent Runtime - orchestrates multiple agents and their interactions with the environment.
"""

from typing import Any, Dict, List, Optional
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from .agent import Agent, Action

logger = logging.getLogger(__name__)


class AgentRuntime:
    """
    Runtime environment for managing multiple agents and their execution.

    Handles agent lifecycle, scheduling, and communication with the Godot simulation.
    """

    def __init__(
        self,
        max_workers: int = 4,
        backend_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the agent runtime.

        Args:
            max_workers: Maximum number of concurrent agent workers
            backend_config: Configuration for LLM backend
        """
        self.agents: Dict[str, Agent] = {}
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.backend_config = backend_config or {}
        self.running = False

        logger.info(f"Initialized AgentRuntime with {max_workers} workers")

    def register_agent(self, agent: Agent) -> None:
        """
        Register an agent with the runtime.

        Args:
            agent: Agent instance to register
        """
        agent_id = agent.state.agent_id
        if agent_id in self.agents:
            logger.warning(f"Agent {agent_id} already registered, replacing")

        self.agents[agent_id] = agent
        logger.info(f"Registered agent {agent_id}")

    def unregister_agent(self, agent_id: str) -> None:
        """
        Unregister an agent from the runtime.

        Args:
            agent_id: ID of agent to unregister
        """
        if agent_id in self.agents:
            del self.agents[agent_id]
            logger.info(f"Unregistered agent {agent_id}")

    async def process_tick(self, tick: int, observations: Dict[str, Any]) -> Dict[str, Action]:
        """
        Process a single simulation tick for all agents.

        Args:
            tick: Current simulation tick number
            observations: Observations for each agent {agent_id: observation_data}

        Returns:
            Dictionary of actions {agent_id: Action}
        """
        logger.debug(f"Processing tick {tick} for {len(self.agents)} agents")

        # Distribute observations to agents
        for agent_id, obs_data in observations.items():
            if agent_id in self.agents:
                self.agents[agent_id].perceive(obs_data)

        # Gather decisions from all agents concurrently
        tasks = []
        for agent_id, agent in self.agents.items():
            task = asyncio.create_task(self._agent_decide(agent))
            tasks.append((agent_id, task))

        # Collect results
        actions = {}
        for agent_id, task in tasks:
            try:
                action = await task
                if action:
                    actions[agent_id] = action
            except Exception as e:
                logger.error(f"Error processing agent {agent_id} on tick {tick}: {e}")

        return actions

    async def _agent_decide(self, agent: Agent) -> Optional[Action]:
        """
        Execute agent decision-making asynchronously.

        Args:
            agent: Agent to make decision

        Returns:
            Action decided by agent, or None
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, agent.decide_action)

    def start(self) -> None:
        """Start the runtime."""
        self.running = True
        logger.info("AgentRuntime started")

    def stop(self) -> None:
        """Stop the runtime and cleanup resources."""
        self.running = False
        self.executor.shutdown(wait=True)
        logger.info("AgentRuntime stopped")

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get an agent by ID."""
        return self.agents.get(agent_id)

    def get_all_agents(self) -> List[Agent]:
        """Get all registered agents."""
        return list(self.agents.values())

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
