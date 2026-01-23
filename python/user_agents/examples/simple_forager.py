"""
Simple Foraging Agent - Full AgentBehavior Example.

This demonstrates the complete AgentBehavior interface with:
- Memory management
- Rule-based decision making
- Priority-based behavior
- Detailed reasoning
"""

from agent_runtime import AgentBehavior, AgentDecision, SlidingWindowMemory


class SimpleForager(AgentBehavior):
    """
    Simple rule-based foraging agent.

    Behavior Priority:
    1. Avoid hazards within 3 units (highest priority)
    2. Move to nearest resource within 10 units
    3. Idle if no resources nearby (default)

    This agent demonstrates:
    - Using SlidingWindowMemory to track recent observations
    - Making decisions based on observation data
    - Calculating escape positions from hazards
    - Providing reasoning for each decision
    """

    def __init__(self, memory_capacity: int = 5):
        """
        Initialize the simple forager.

        Args:
            memory_capacity: Number of recent observations to keep in memory
        """
        self.memory = SlidingWindowMemory(capacity=memory_capacity)

    def decide(self, observation, tools):
        """
        Decide what action to take based on current observation.

        Args:
            observation: Current observation from Godot
            tools: List of available tool schemas

        Returns:
            AgentDecision with tool, params, and reasoning
        """
        # Store observation in memory
        self.memory.store(observation)

        # Priority 1: Avoid nearby hazards
        for hazard in observation.nearby_hazards:
            if hazard.distance < 3.0:
                # Calculate safe position away from hazard
                safe_pos = self._calculate_escape_position(observation.position, hazard.position)
                return AgentDecision(
                    tool="move_to",
                    params={"target_position": safe_pos, "speed": 2.0},
                    reasoning=f"Avoiding {hazard.name} at distance {hazard.distance:.1f}",
                )

        # Priority 2: Move to nearest resource
        if observation.nearby_resources:
            nearest = min(observation.nearby_resources, key=lambda r: r.distance)
            if nearest.distance < 10.0:
                return AgentDecision(
                    tool="move_to",
                    params={"target_position": nearest.position, "speed": 1.5},
                    reasoning=f"Moving to {nearest.name} at distance {nearest.distance:.1f}",
                )

        # Default: Idle
        return AgentDecision.idle(reasoning="No resources nearby, waiting")

    def _calculate_escape_position(self, agent_pos, hazard_pos):
        """
        Calculate a safe position away from a hazard.

        Args:
            agent_pos: Agent's current position (x, y, z)
            hazard_pos: Hazard's position (x, y, z)

        Returns:
            Safe position tuple (x, y, z) 5 units away from hazard
        """
        # Vector from hazard to agent
        dx = agent_pos[0] - hazard_pos[0]
        dz = agent_pos[2] - hazard_pos[2]

        # Normalize and scale to move 5 units away
        length = (dx**2 + dz**2) ** 0.5
        if length > 0:
            dx = (dx / length) * 5.0
            dz = (dz / length) * 5.0
        else:
            # If on top of hazard, move in arbitrary direction
            dx, dz = 5.0, 0.0

        return (hazard_pos[0] + dx, agent_pos[1], hazard_pos[2] + dz)

    def on_episode_start(self):
        """Called when a new episode begins - clear memory."""
        self.memory.clear()

    def on_episode_end(self, success, metrics=None):
        """
        Called when an episode ends.

        Args:
            success: Whether the episode goal was achieved
            metrics: Optional metrics from the scenario
        """
        # Could log performance here
        pass
