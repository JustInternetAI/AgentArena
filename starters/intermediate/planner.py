"""
Goal Planner with Multi-Step Action Plans

This planner helps agents work toward complex objectives by:
1. Breaking objectives into manageable sub-goals
2. Prioritizing which sub-goal to pursue next
3. Generating multi-step action plans (move → collect → move → craft)
4. Tracking plan execution and replanning on failure

This is YOUR code - modify it to match your strategy!
"""

from agent_arena_sdk import Observation, Objective
from dataclasses import dataclass, field
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


@dataclass
class ActionStep:
    """
    A single step in a multi-step action plan.

    Example plan: [move_to berry, collect berry, move_to workbench, craft meal]

    Attributes:
        tool: Tool to execute ("move_to", "collect", "craft_item")
        params: Parameters for the tool
        description: Human-readable explanation
    """

    tool: str
    params: dict
    description: str


class Planner:
    """
    Planner that decomposes objectives into sub-goals AND generates
    multi-step action plans for each goal.

    The key difference from single-step planning: instead of choosing
    one action per tick, the planner creates a sequence of actions and
    tracks execution across ticks.

    Example:
        planner = Planner()

        # Check if we're mid-plan
        if planner.has_active_plan():
            step = planner.current_step()
            decision = Decision(tool=step.tool, params=step.params)
        else:
            # Create a new plan
            sub_goals = planner.decompose(obs.objective, obs.current_progress)
            goal = planner.select_goal(sub_goals)
            # ... generate plan based on goal type
    """

    def __init__(self):
        self._steps: list[ActionStep] = []
        self._step_index: int = 0

    # -- Multi-step plan management -----------------------------------------

    def has_active_plan(self) -> bool:
        """Check if there's a plan currently being executed."""
        return self._step_index < len(self._steps)

    def current_step(self) -> ActionStep | None:
        """Get the current step to execute, or None if plan is done."""
        if not self.has_active_plan():
            return None
        return self._steps[self._step_index]

    def advance(self) -> None:
        """Move to the next step after the current one succeeds."""
        self._step_index += 1

    def cancel(self) -> None:
        """Cancel the current plan (e.g., when a step fails)."""
        self._steps = []
        self._step_index = 0

    def set_plan(self, steps: list[ActionStep]) -> None:
        """Replace the current plan with a new sequence of steps."""
        self._steps = steps
        self._step_index = 0

    def remaining_steps(self) -> int:
        """How many steps are left in the current plan."""
        return max(0, len(self._steps) - self._step_index)

    # -- Plan generators ----------------------------------------------------

    def plan_collect(
        self,
        resource_name: str,
        resource_position: tuple[float, float, float],
        agent_position: tuple[float, float, float],
        collect_radius: float = 2.0,
    ) -> list[ActionStep]:
        """
        Generate a plan to collect a resource: move to it, then collect.

        Args:
            resource_name: Name of the resource
            resource_position: Where the resource is
            agent_position: Agent's current position
            collect_radius: How close you need to be to collect
        """
        import math

        dx = resource_position[0] - agent_position[0]
        dz = resource_position[2] - agent_position[2]
        dist = math.sqrt(dx * dx + dz * dz)

        steps = []
        if dist > collect_radius:
            steps.append(
                ActionStep(
                    tool="move_to",
                    params={"target_position": list(resource_position)},
                    description=f"Move to {resource_name}",
                )
            )
        steps.append(
            ActionStep(
                tool="collect",
                params={"target_name": resource_name},
                description=f"Collect {resource_name}",
            )
        )
        return steps

    def plan_craft(
        self,
        recipe: str,
        station_name: str,
        station_position: tuple[float, float, float],
        missing_materials: list[tuple[str, tuple[float, float, float]]] | None = None,
    ) -> list[ActionStep]:
        """
        Generate a multi-step crafting plan.

        If missing_materials is provided, gathers them first. Then moves
        to the crafting station and crafts the item.

        Args:
            recipe: What to craft (e.g., "torch")
            station_name: Name of the station to use
            station_position: Where the station is
            missing_materials: List of (resource_name, position) to gather first
        """
        steps = []

        # Step 1: Gather any missing materials
        if missing_materials:
            for mat_name, mat_pos in missing_materials:
                steps.append(
                    ActionStep(
                        tool="move_to",
                        params={"target_position": list(mat_pos)},
                        description=f"Move to {mat_name}",
                    )
                )
                steps.append(
                    ActionStep(
                        tool="collect",
                        params={"target_name": mat_name},
                        description=f"Collect {mat_name}",
                    )
                )

        # Step 2: Go to the crafting station
        steps.append(
            ActionStep(
                tool="move_to",
                params={"target_position": list(station_position)},
                description=f"Move to {station_name}",
            )
        )

        # Step 3: Craft
        steps.append(
            ActionStep(
                tool="craft_item",
                params={"recipe": recipe},
                description=f"Craft {recipe}",
            )
        )

        return steps

    def plan_explore(
        self, target_position: tuple[float, float, float], direction: str = ""
    ) -> list[ActionStep]:
        """Generate a simple exploration plan: move to a position."""
        desc = f"Explore {direction}" if direction else "Explore new area"
        return [
            ActionStep(
                tool="move_to",
                params={"target_position": list(target_position)},
                description=desc,
            )
        ]

    # -- Objective decomposition --------------------------------------------

    def decompose(
        self, objective: Objective | None, current_progress: dict[str, float]
    ) -> List[SubGoal]:
        """
        Break an objective into sub-goals.

        Args:
            objective: The objective to decompose
            current_progress: Current progress toward metrics

        Returns:
            List of sub-goals to pursue, sorted by priority (highest first)
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
        """Create a human-readable description for a sub-goal."""
        remaining = target - current

        if "resources" in metric_name.lower() or "collected" in metric_name.lower():
            return f"Collect {remaining:.0f} more resources (have {current:.0f}/{target:.0f})"

        if "health" in metric_name.lower():
            if current < target:
                return f"Recover {remaining:.0f} health (current: {current:.0f}/{target:.0f})"
            else:
                return f"Maintain health above {target:.0f}"

        if "time" in metric_name.lower():
            return f"Complete within {target - current:.0f} ticks"

        if "craft" in metric_name.lower() or "items" in metric_name.lower():
            return f"Craft {remaining:.0f} more items (have {current:.0f}/{target:.0f})"

        # Generic description
        return f"Reach {metric_name}={target:.0f} (currently {current:.0f})"

    def explain_plan(self, sub_goals: List[SubGoal] | None = None) -> str:
        """
        Create a human-readable explanation of the current state.

        Args:
            sub_goals: List of sub-goals (optional, for context)

        Returns:
            Multi-line string explaining the plan
        """
        lines = []

        # Show active action plan
        if self.has_active_plan():
            step = self.current_step()
            lines.append(
                f"Active plan: step {self._step_index + 1}/{len(self._steps)}"
            )
            for i, s in enumerate(self._steps):
                marker = ">>>" if i == self._step_index else "   "
                lines.append(f"  {marker} {i + 1}. {s.description} ({s.tool})")
        else:
            lines.append("No active plan.")

        # Show sub-goals
        if sub_goals:
            lines.append("\nSub-goals:")
            for i, goal in enumerate(sub_goals, 1):
                progress = goal.progress_percent()
                lines.append(
                    f"  {i}. {goal.description} "
                    f"(priority: {goal.priority:.1f}, progress: {progress:.0f}%)"
                )

        return "\n".join(lines)
