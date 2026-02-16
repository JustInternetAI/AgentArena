"""
Simple Goal Planner - Break Down Objectives into Sub-Goals

This planner helps agents work toward complex objectives by:
1. Breaking objectives into manageable sub-goals
2. Prioritizing which sub-goal to pursue next
3. Tracking progress toward each goal

This is YOUR code - modify it to match your strategy!
"""

from agent_arena_sdk import Observation, Objective
from dataclasses import dataclass
from typing import List


@dataclass
class SubGoal:
    """
    A sub-goal that works toward an objective metric.

    Attributes:
        metric_name: Which metric this goal addresses
        description: What needs to be done
        priority: How urgent this goal is (higher = more urgent)
        target: Target value for the metric
        current: Current value for the metric
    """

    metric_name: str
    description: str
    priority: float
    target: float
    current: float

    def progress_percent(self) -> float:
        """Calculate progress as percentage."""
        if self.target == 0:
            return 100.0
        return min(100.0, (self.current / self.target) * 100.0)

    def is_complete(self) -> bool:
        """Check if this sub-goal is complete."""
        return self.current >= self.target


class Planner:
    """
    Simple planner that decomposes objectives into actionable sub-goals.

    Example:
        planner = Planner()

        # Each tick, decompose the objective
        sub_goals = planner.decompose(obs.objective, obs.current_progress)

        # Pick the highest priority goal
        current_goal = planner.select_goal(sub_goals)

        # Work on that goal
        decision = execute_goal(current_goal, obs)
    """

    def decompose(
        self, objective: Objective | None, current_progress: dict[str, float]
    ) -> List[SubGoal]:
        """
        Break an objective into sub-goals.

        Args:
            objective: The objective to decompose
            current_progress: Current progress toward metrics

        Returns:
            List of sub-goals to pursue
        """
        if not objective:
            return []

        sub_goals = []

        for metric_name, metric_def in objective.success_metrics.items():
            current = current_progress.get(metric_name, 0.0)
            target = metric_def.target

            # Skip if already complete
            if current >= target:
                continue

            # Calculate priority based on:
            # - Weight (how important)
            # - Progress (how far from target)
            # - Required (must complete)
            progress_ratio = current / target if target > 0 else 0
            urgency = 1.0 - progress_ratio  # More urgent if further from goal

            priority = metric_def.weight * urgency
            if metric_def.required:
                priority *= 2.0  # Required goals are much more important

            # Create sub-goal with descriptive name
            description = self._create_description(metric_name, current, target)

            sub_goals.append(
                SubGoal(
                    metric_name=metric_name,
                    description=description,
                    priority=priority,
                    target=target,
                    current=current,
                )
            )

        # Sort by priority (highest first)
        sub_goals.sort(key=lambda g: g.priority, reverse=True)

        return sub_goals

    def select_goal(self, sub_goals: List[SubGoal]) -> SubGoal | None:
        """
        Select which sub-goal to pursue next.

        Args:
            sub_goals: List of available sub-goals

        Returns:
            The highest priority sub-goal, or None if no goals
        """
        if not sub_goals:
            return None

        # Return highest priority (already sorted)
        return sub_goals[0]

    def _create_description(self, metric_name: str, current: float, target: float) -> str:
        """
        Create a human-readable description for a sub-goal.

        Args:
            metric_name: Name of the metric
            current: Current value
            target: Target value

        Returns:
            Description string
        """
        remaining = target - current

        # Customize description based on metric type
        if "resources" in metric_name.lower() or "collected" in metric_name.lower():
            return f"Collect {remaining:.0f} more resources (have {current:.0f}/{target:.0f})"

        if "health" in metric_name.lower():
            if current < target:
                return f"Recover {remaining:.0f} health (current: {current:.0f}/{target:.0f})"
            else:
                return f"Maintain health above {target:.0f}"

        if "time" in metric_name.lower():
            return f"Complete within {target - current:.0f} ticks"

        # Generic description
        return f"Reach {metric_name}={target:.0f} (currently {current:.0f})"

    def explain_plan(self, sub_goals: List[SubGoal]) -> str:
        """
        Create a human-readable explanation of the current plan.

        Args:
            sub_goals: List of sub-goals

        Returns:
            Multi-line string explaining the plan
        """
        if not sub_goals:
            return "No active goals."

        lines = ["Current Plan:"]
        for i, goal in enumerate(sub_goals, 1):
            progress = goal.progress_percent()
            lines.append(
                f"  {i}. {goal.description} (priority: {goal.priority:.1f}, progress: {progress:.0f}%)"
            )

        return "\n".join(lines)
