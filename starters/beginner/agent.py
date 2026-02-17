"""
Beginner Agent - Simple Priority-Based Decision Making

This is a simple agent that makes decisions based on immediate observations
without using memory or planning. It's perfect for learning the basics.

Key Concepts:
- Observation: What the agent sees each tick
- Decision: What the agent chooses to do
- Priority system: Handle most urgent situations first
"""

from agent_arena_sdk import Observation, Decision
import math


class Agent:
    """
    A simple priority-based agent.

    Decision priority:
    1. Escape danger (hazards too close)
    2. Pursue objectives (collect resources, etc.)
    3. Explore (when nothing else to do)
    """

    def decide(self, obs: Observation) -> Decision:
        """
        Make a decision based on current observation.

        Args:
            obs: Current observation from the game

        Returns:
            Decision: The action to take this tick
        """
        # Priority 1: Escape danger
        danger_decision = self.check_danger(obs)
        if danger_decision:
            return danger_decision

        # Priority 2: Collect nearby resources
        collect_decision = self.collect_resources(obs)
        if collect_decision:
            return collect_decision

        # Priority 3: Explore
        return self.explore(obs)

    def check_danger(self, obs: Observation) -> Decision | None:
        """
        Check for nearby hazards and escape if too close.

        Args:
            obs: Current observation

        Returns:
            Decision to escape, or None if safe
        """
        for hazard in obs.nearby_hazards:
            if hazard.distance < 3.0:
                # Calculate escape direction (away from hazard)
                safe_position = self.calculate_escape_position(
                    obs.position, hazard.position, distance=5.0
                )
                return Decision(
                    tool="move_to",
                    params={"target_position": safe_position},
                    reasoning=f"Escaping {hazard.type} hazard at distance {hazard.distance:.1f}",
                )
        return None

    def pursue_objective(self, obs: Observation) -> Decision | None:
        """
        Work toward the objective's success metrics.

        Args:
            obs: Current observation

        Returns:
            Decision to pursue objective, or None if no clear action
        """
        if not obs.objective:
            return None

        # Check which metrics need work
        for metric_name, metric_def in obs.objective.success_metrics.items():
            current = obs.current_progress.get(metric_name, 0)
            target = metric_def.target

            # Resources need collecting
            if metric_name == "resources_collected" and current < target:
                return self.collect_resources(obs)

            # Health is low
            if metric_name == "health_remaining" and obs.health < target:
                return self.seek_safety(obs)

        return None

    def collect_resources(self, obs: Observation) -> Decision | None:
        """
        Try to collect nearby resources.

        Args:
            obs: Current observation

        Returns:
            Decision to collect or move toward resource, or None
        """
        if not obs.nearby_resources:
            return None

        # Find closest resource
        closest = min(obs.nearby_resources, key=lambda r: r.distance)

        # Always move toward the resource — Godot auto-collects when close enough
        return Decision(
            tool="move_to",
            params={"target_position": list(closest.position)},
            reasoning=f"Moving toward {closest.type} at distance {closest.distance:.1f}",
        )

    def seek_safety(self, obs: Observation) -> Decision:
        """
        Find a safe spot away from hazards.

        Args:
            obs: Current observation

        Returns:
            Decision to move to safety
        """
        if obs.nearby_hazards:
            # Move away from nearest hazard
            nearest_hazard = min(obs.nearby_hazards, key=lambda h: h.distance)
            safe_position = self.calculate_escape_position(
                obs.position, nearest_hazard.position, distance=10.0
            )
            return Decision(
                tool="move_to",
                params={"target_position": safe_position},
                reasoning="Low health - seeking safety",
            )

        # If no hazards visible, just stay put to recover
        return Decision.idle("Recovering health")

    def explore(self, obs: Observation) -> Decision:
        """
        Explore the world when nothing urgent to do.

        Args:
            obs: Current observation

        Returns:
            Decision to explore
        """
        # Use exploration info if available
        if obs.exploration and obs.exploration.explore_targets:
            target = obs.exploration.explore_targets[0]
            return Decision(
                tool="move_to",
                params={"target_position": list(target.position)},
                reasoning=f"Exploring {target.direction}",
            )

        # Default: idle
        return Decision.idle("No immediate actions needed")

    def calculate_escape_position(
        self,
        agent_pos: tuple[float, float, float],
        danger_pos: tuple[float, float, float],
        distance: float = 5.0,
    ) -> list[float]:
        """
        Calculate a safe position away from danger.

        Args:
            agent_pos: Agent's current position
            danger_pos: Position of the hazard
            distance: How far to move away

        Returns:
            Safe position as [x, y, z]
        """
        # Vector from danger to agent
        dx = agent_pos[0] - danger_pos[0]
        dz = agent_pos[2] - danger_pos[2]

        # Normalize and scale
        length = math.sqrt(dx * dx + dz * dz)
        if length > 0:
            dx = (dx / length) * distance
            dz = (dz / length) * distance
        else:
            # If on top of danger, move in arbitrary direction
            dx, dz = distance, 0.0

        return [danger_pos[0] + dx, agent_pos[1], danger_pos[2] + dz]
