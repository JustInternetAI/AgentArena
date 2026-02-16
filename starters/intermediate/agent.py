"""
Intermediate Agent - Memory + Planning

This agent demonstrates:
- Memory: Remembering past observations
- Planning: Breaking objectives into sub-goals
- State tracking: Maintaining agent state between ticks

This is more sophisticated than the beginner agent but still understandable!
"""

from agent_arena_sdk import Observation, Decision
from memory import SlidingWindowMemory
from planner import Planner, SubGoal
import math


class Agent:
    """
    An intermediate agent with memory and planning.

    Features:
    - Remembers last 50 observations
    - Decomposes objectives into prioritized sub-goals
    - Tracks visited locations
    - Makes more informed decisions
    """

    def __init__(self):
        """Initialize the agent with memory and planner."""
        self.memory = SlidingWindowMemory(capacity=50)
        self.planner = Planner()
        self.visited_positions: list[tuple[float, float, float]] = []

    def decide(self, obs: Observation) -> Decision:
        """
        Make a decision based on observation, memory, and planning.

        Args:
            obs: Current observation

        Returns:
            Decision for this tick
        """
        # Store observation in memory
        self.memory.store(obs)

        # Track position
        self.visited_positions.append(obs.position)

        # Priority 1: Immediate danger
        danger_decision = self.check_danger(obs)
        if danger_decision:
            return danger_decision

        # Priority 2: Work on objectives (with planning)
        if obs.objective:
            objective_decision = self.pursue_objective_with_planning(obs)
            if objective_decision:
                return objective_decision

        # Priority 3: Intelligent exploration
        return self.explore_smartly(obs)

    def check_danger(self, obs: Observation) -> Decision | None:
        """
        Check for immediate danger using memory.

        Uses memory to remember hazard locations even when not visible.

        Args:
            obs: Current observation

        Returns:
            Decision to escape danger, or None if safe
        """
        # Check visible hazards
        for hazard in obs.nearby_hazards:
            if hazard.distance < 3.0:
                safe_position = self.calculate_escape_position(
                    obs.position, hazard.position, distance=6.0
                )
                return Decision(
                    tool="move_to",
                    params={"target_position": safe_position},
                    reasoning=f"Escaping {hazard.type} at distance {hazard.distance:.1f}",
                )

        # Check remembered hazards (they might still be there!)
        remembered_hazards = self.memory.find_hazards_seen()
        for hazard_name, hazard_pos, last_tick in remembered_hazards:
            # Only worry about recently seen hazards
            if obs.tick - last_tick < 20:
                distance = self._distance_to(obs.position, hazard_pos)
                if distance < 4.0:
                    safe_position = self.calculate_escape_position(
                        obs.position, hazard_pos, distance=6.0
                    )
                    return Decision(
                        tool="move_to",
                        params={"target_position": safe_position},
                        reasoning=f"Avoiding remembered hazard at {hazard_pos}",
                    )

        return None

    def pursue_objective_with_planning(self, obs: Observation) -> Decision | None:
        """
        Use planner to work toward objective systematically.

        Args:
            obs: Current observation

        Returns:
            Decision to work on highest priority sub-goal, or None
        """
        # Decompose objective into sub-goals
        sub_goals = self.planner.decompose(obs.objective, obs.current_progress)

        if not sub_goals:
            return None

        # Select highest priority goal
        current_goal = self.planner.select_goal(sub_goals)

        if not current_goal:
            return None

        # Execute the goal
        return self.execute_sub_goal(current_goal, obs)

    def execute_sub_goal(self, goal: SubGoal, obs: Observation) -> Decision | None:
        """
        Execute actions to achieve a sub-goal.

        Args:
            goal: The sub-goal to work on
            obs: Current observation

        Returns:
            Decision to work toward goal
        """
        # Resource collection goals
        if "resources" in goal.metric_name.lower() or "collected" in goal.metric_name.lower():
            return self.collect_resources_smartly(obs)

        # Health maintenance goals
        if "health" in goal.metric_name.lower():
            if obs.health < goal.target:
                return self.seek_safety(obs)
            # Health is good, continue other goals
            return None

        # Time-based goals - just work faster!
        if "time" in goal.metric_name.lower():
            # Prioritize efficiency
            return self.collect_resources_smartly(obs)

        return None

    def collect_resources_smartly(self, obs: Observation) -> Decision | None:
        """
        Collect resources using memory to find best targets.

        Args:
            obs: Current observation

        Returns:
            Decision to collect resources
        """
        # Check visible resources first
        if obs.nearby_resources:
            # Find closest uncollected resource
            closest = min(obs.nearby_resources, key=lambda r: r.distance)

            if closest.distance < 2.0:
                return Decision(
                    tool="collect",
                    params={"target_name": closest.name},
                    reasoning=f"Collecting {closest.type}",
                )

            return Decision(
                tool="move_to",
                params={"target_position": list(closest.position)},
                reasoning=f"Moving to {closest.type} at distance {closest.distance:.1f}",
            )

        # Use memory to find resources we saw recently
        remembered_resources = self.memory.find_resources_seen()
        if remembered_resources:
            # Find closest remembered resource
            closest_remembered = min(
                remembered_resources, key=lambda r: self._distance_to(obs.position, r[1])
            )
            name, position, last_tick = closest_remembered

            # Only go to recently seen resources (might still be there)
            if obs.tick - last_tick < 30:
                return Decision(
                    tool="move_to",
                    params={"target_position": list(position)},
                    reasoning=f"Returning to {name} last seen at tick {last_tick}",
                )

        return None

    def seek_safety(self, obs: Observation) -> Decision:
        """
        Find a safe location to recover health.

        Args:
            obs: Current observation

        Returns:
            Decision to move to safety
        """
        # Find position away from all known hazards
        hazards = obs.nearby_hazards + [
            (name, pos) for name, pos, _ in self.memory.find_hazards_seen()
        ]

        if hazards:
            # Calculate center of hazards
            if obs.nearby_hazards:
                hazard_center = self._calculate_center([h.position for h in obs.nearby_hazards])
            else:
                hazard_center = self.memory.find_hazards_seen()[0][1]

            safe_position = self.calculate_escape_position(
                obs.position, hazard_center, distance=10.0
            )

            return Decision(
                tool="move_to",
                params={"target_position": safe_position},
                reasoning=f"Low health ({obs.health:.0f}) - seeking safety",
            )

        # No hazards, just stay put
        return Decision.idle("Recovering health")

    def explore_smartly(self, obs: Observation) -> Decision:
        """
        Explore using memory to avoid revisiting areas.

        Args:
            obs: Current observation

        Returns:
            Decision to explore efficiently
        """
        # Use exploration system if available
        if obs.exploration and obs.exploration.explore_targets:
            # Filter out targets near visited positions
            unvisited_targets = []
            for target in obs.exploration.explore_targets:
                if not self._recently_visited(target.position):
                    unvisited_targets.append(target)

            if unvisited_targets:
                target = unvisited_targets[0]
                return Decision(
                    tool="move_to",
                    params={"target_position": list(target.position)},
                    reasoning=f"Exploring {target.direction}",
                )

        # Fallback: move to least visited direction
        return Decision.idle("Planning next move")

    def _recently_visited(self, position: tuple[float, float, float], threshold: float = 5.0) -> bool:
        """Check if we've been near this position recently."""
        # Check last 20 positions
        for visited in self.visited_positions[-20:]:
            if self._distance_to(visited, position) < threshold:
                return True
        return False

    def _distance_to(
        self, pos1: tuple[float, float, float], pos2: tuple[float, float, float]
    ) -> float:
        """Calculate distance between two positions."""
        return math.sqrt(
            (pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2 + (pos1[2] - pos2[2]) ** 2
        )

    def _calculate_center(self, positions: list[tuple[float, float, float]]) -> tuple[float, float, float]:
        """Calculate the center point of multiple positions."""
        if not positions:
            return (0.0, 0.0, 0.0)

        avg_x = sum(p[0] for p in positions) / len(positions)
        avg_y = sum(p[1] for p in positions) / len(positions)
        avg_z = sum(p[2] for p in positions) / len(positions)

        return (avg_x, avg_y, avg_z)

    def calculate_escape_position(
        self,
        agent_pos: tuple[float, float, float],
        danger_pos: tuple[float, float, float],
        distance: float = 6.0,
    ) -> list[float]:
        """
        Calculate a safe position away from danger.

        Args:
            agent_pos: Agent's current position
            danger_pos: Position of the danger
            distance: How far to move away

        Returns:
            Safe position as [x, y, z]
        """
        dx = agent_pos[0] - danger_pos[0]
        dz = agent_pos[2] - danger_pos[2]

        length = math.sqrt(dx * dx + dz * dz)
        if length > 0:
            dx = (dx / length) * distance
            dz = (dz / length) * distance
        else:
            dx, dz = distance, 0.0

        return [danger_pos[0] + dx, agent_pos[1], danger_pos[2] + dz]
