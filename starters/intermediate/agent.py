"""
Intermediate Agent - Memory + Planning + Crafting

This agent demonstrates:
- Memory: Remembering past observations, tracking collected resources
- Planning: Multi-step action plans (move → collect → move → craft)
- Crafting: Recipes with material gathering and station navigation
- Tool results: Replanning when actions fail
- Pattern detection: Finding productive areas from memory

This is more sophisticated than the beginner agent but still understandable!
"""

from agent_arena_sdk import Observation, Decision
from memory import SlidingWindowMemory
from planner import Planner, SubGoal, ActionStep
import math


# ---------------------------------------------------------------------------
#  Crafting recipes: { recipe_name: (station_type, {material: quantity}) }
# ---------------------------------------------------------------------------

RECIPES = {
    "torch": ("workbench", {"wood": 1, "stone": 1}),
    "meal": ("workbench", {"berry": 2}),
    "shelter": ("anvil", {"wood": 3, "stone": 2}),
}


class Agent:
    """
    An intermediate agent with memory, multi-step planning, and crafting.

    Decision priority:
    1. Handle tool result from previous tick (advance plan or replan)
    2. Escape immediate danger (hazards too close)
    3. Continue active multi-step plan
    4. Pursue objectives (collect, craft, maintain health)
    5. Explore using memory (productive areas, then frontiers)
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

        # Step 0: Handle tool result from last tick
        self._handle_tool_result(obs)

        # Priority 1: Immediate danger overrides everything (even active plans)
        danger_decision = self._check_danger(obs)
        if danger_decision:
            self.planner.cancel()  # Danger breaks any active plan
            return danger_decision

        # Priority 2: Continue active multi-step plan
        if self.planner.has_active_plan():
            step = self.planner.current_step()
            return Decision(
                tool=step.tool,
                params=step.params,
                reasoning=f"Plan step {self.planner._step_index + 1}/"
                f"{len(self.planner._steps)}: {step.description}",
            )

        # Priority 3: Work on objectives (create new plans)
        if obs.objective:
            objective_decision = self._pursue_objective(obs)
            if objective_decision:
                return objective_decision

        # Priority 4: Collect visible or remembered resources (even without objective)
        collect_decision = self._plan_resource_collection(obs)
        if collect_decision:
            return collect_decision

        # Priority 5: Opportunistic crafting (no objective required)
        craft_decision = self._try_opportunistic_craft(obs)
        if craft_decision:
            return craft_decision

        # Priority 6: Intelligent exploration
        return self._explore(obs)

    # -- Tool result handling -----------------------------------------------

    def _handle_tool_result(self, obs: Observation) -> None:
        """
        Process the result of the previous action.

        On success: advance the plan to the next step, track collections.
        On failure: cancel the plan so we replan next tick.
        """
        result = obs.last_tool_result
        if result is None:
            return

        if result.success:
            # If we collected something, mark it in memory
            if result.tool == "collect":
                collected_name = result.result.get("target_name", "")
                if collected_name:
                    self.memory.mark_collected(collected_name)

            # Advance multi-step plan
            if self.planner.has_active_plan():
                self.planner.advance()
        else:
            # Action failed — cancel plan and let the agent replan
            self.planner.cancel()

    # -- Danger check -------------------------------------------------------

    def _check_danger(self, obs: Observation) -> Decision | None:
        """
        Check for immediate danger using both visible and remembered hazards.
        """
        # Check visible hazards
        for hazard in obs.nearby_hazards:
            if hazard.distance < 3.0:
                safe_pos = self._escape_position(obs.position, hazard.position, 6.0)
                return Decision(
                    tool="move_to",
                    params={"target_position": safe_pos},
                    reasoning=f"Escaping {hazard.type} at distance {hazard.distance:.1f}",
                )

        # Check remembered hazards (might still be there)
        for name, pos in self.memory.find_hazard_zones(obs.tick, recency=20):
            distance = self._distance(obs.position, pos)
            if distance < 4.0:
                safe_pos = self._escape_position(obs.position, pos, 6.0)
                return Decision(
                    tool="move_to",
                    params={"target_position": safe_pos},
                    reasoning=f"Avoiding remembered hazard {name} at distance {distance:.1f}",
                )

        return None

    # -- Objective pursuit --------------------------------------------------

    def _pursue_objective(self, obs: Observation) -> Decision | None:
        """
        Decompose the objective into sub-goals and create a plan for the
        highest-priority goal.
        """
        sub_goals = self.planner.decompose(obs.objective, obs.current_progress)
        if not sub_goals:
            return None

        goal = self.planner.select_goal(sub_goals)
        if not goal:
            return None

        return self._execute_sub_goal(goal, obs)

    def _execute_sub_goal(self, goal: SubGoal, obs: Observation) -> Decision | None:
        """
        Create an action plan for a sub-goal. Each goal type gets its own
        strategy — no more falling through to the same function.
        """
        metric = goal.metric_name.lower()

        # --- Resource collection goals ---
        if "resources" in metric or "collected" in metric:
            return self._plan_resource_collection(obs)

        # --- Health maintenance goals ---
        if "health" in metric:
            if obs.health < goal.target:
                return self._seek_safety(obs)
            return None  # Health is fine, move on

        # --- Crafting / items goals ---
        if "craft" in metric or "items" in metric:
            return self._plan_crafting(obs)

        # --- Time efficiency goals ---
        if "time" in metric:
            # Optimize by collecting nearest resource as fast as possible
            return self._plan_resource_collection(obs)

        # --- Exploration goals ---
        if "exploration" in metric or "explore" in metric:
            return self._explore(obs)

        # Fallback: try collecting resources (most common objective)
        return self._plan_resource_collection(obs)

    # -- Resource collection ------------------------------------------------

    def _plan_resource_collection(self, obs: Observation) -> Decision | None:
        """
        Find the best resource to collect, using visible resources first,
        then falling back to remembered (uncollected) resources from memory.
        """
        # Option 1: Visible resources — go for the closest
        if obs.nearby_resources:
            closest = min(obs.nearby_resources, key=lambda r: r.distance)
            steps = self.planner.plan_collect(
                closest.name, closest.position, obs.position
            )
            self.planner.set_plan(steps)
            step = self.planner.current_step()
            return Decision(
                tool=step.tool,
                params=step.params,
                reasoning=f"Collecting {closest.type} at distance {closest.distance:.1f}",
            )

        # Option 2: Remembered resources we haven't collected yet
        uncollected = self.memory.find_uncollected_resources(obs.tick, recency=40)
        if uncollected:
            name, position, last_tick = uncollected[0]
            steps = self.planner.plan_collect(name, position, obs.position)
            self.planner.set_plan(steps)
            step = self.planner.current_step()
            return Decision(
                tool=step.tool,
                params=step.params,
                reasoning=f"Returning to {name} last seen at tick {last_tick}",
            )

        return None

    # -- Crafting -----------------------------------------------------------

    def _plan_crafting(self, obs: Observation) -> Decision | None:
        """
        Find a recipe we can craft and create a multi-step plan:
        gather missing materials → go to station → craft.
        """
        inventory = self._get_inventory_counts(obs)

        for recipe, (station_type, materials) in RECIPES.items():
            # Check what materials we're missing
            missing = {}
            for mat, needed in materials.items():
                have = inventory.get(mat, 0)
                if have < needed:
                    missing[mat] = needed - have

            # Find the right station (visible or from memory)
            station = self._find_station(obs, station_type)
            if station is None:
                continue

            station_name, station_pos = station

            # Find positions for missing materials
            missing_with_pos = []
            if missing:
                for mat_name in missing:
                    mat_pos = self._find_material(obs, mat_name)
                    if mat_pos is None:
                        break
                    missing_with_pos.append((mat_name, mat_pos))
                else:
                    # Found all materials — create crafting plan
                    steps = self.planner.plan_craft(
                        recipe, station_name, station_pos, missing_with_pos
                    )
                    self.planner.set_plan(steps)
                    step = self.planner.current_step()
                    return Decision(
                        tool=step.tool,
                        params=step.params,
                        reasoning=f"Crafting plan: {recipe} "
                        f"({self.planner.remaining_steps()} steps)",
                    )
                continue

            # Have all materials — just go to station and craft
            steps = self.planner.plan_craft(recipe, station_name, station_pos)
            self.planner.set_plan(steps)
            step = self.planner.current_step()
            return Decision(
                tool=step.tool,
                params=step.params,
                reasoning=f"Crafting {recipe} at {station_name}",
            )

        return None

    def _try_opportunistic_craft(self, obs: Observation) -> Decision | None:
        """
        Try crafting even without an explicit crafting objective.
        Only crafts if we're at a station with all required materials.
        """
        inventory = self._get_inventory_counts(obs)

        for station in obs.nearby_stations:
            if station.distance > 3.0:
                continue

            for recipe, (station_type, materials) in RECIPES.items():
                if station.type != station_type:
                    continue

                # Check if we have all materials
                if all(inventory.get(m, 0) >= q for m, q in materials.items()):
                    return Decision(
                        tool="craft_item",
                        params={"recipe": recipe},
                        reasoning=f"Opportunistic craft: {recipe} at {station.type}",
                    )

        return None

    def _find_station(
        self, obs: Observation, station_type: str
    ) -> tuple[str, tuple[float, float, float]] | None:
        """Find a station by type, checking visible stations first, then memory."""
        # Visible stations
        for station in obs.nearby_stations:
            if station.type == station_type:
                return (station.name, station.position)

        # Remembered stations (scan observations for station sightings)
        for past_obs in reversed(self.memory.get_all()):
            for station in past_obs.nearby_stations:
                if station.type == station_type:
                    return (station.name, station.position)

        return None

    def _find_material(
        self, obs: Observation, material_type: str
    ) -> tuple[float, float, float] | None:
        """Find a material resource by type, checking visible then memory."""
        # Visible resources
        for resource in obs.nearby_resources:
            if resource.type == material_type:
                return resource.position

        # Remembered uncollected resources
        for name, pos, tick in self.memory.find_uncollected_resources(obs.tick, recency=40):
            # Match by type prefix (e.g., "wood" matches "wood_001")
            if name.startswith(material_type) or material_type in name:
                return pos

        return None

    # -- Safety -------------------------------------------------------------

    def _seek_safety(self, obs: Observation) -> Decision:
        """Find a safe position away from all known hazards."""
        hazard_positions = [h.position for h in obs.nearby_hazards]

        # Add remembered hazards
        for _, pos in self.memory.find_hazard_zones(obs.tick, recency=30):
            hazard_positions.append(pos)

        if hazard_positions:
            center = self._center(hazard_positions)
            safe_pos = self._escape_position(obs.position, center, 10.0)
            return Decision(
                tool="move_to",
                params={"target_position": safe_pos},
                reasoning=f"Low health ({obs.health:.0f}) - seeking safety",
            )

        return Decision.idle("Recovering health")

    # -- Exploration --------------------------------------------------------

    def _explore(self, obs: Observation) -> Decision:
        """
        Explore intelligently using three strategies:
        1. Frontier targets from the exploration system (filtered by visited)
        2. Productive areas from memory (resource clusters)
        3. Random direction as last resort
        """
        # Strategy 1: Frontier exploration targets
        if obs.exploration and obs.exploration.explore_targets:
            unvisited = [
                t
                for t in obs.exploration.explore_targets
                if not self._recently_visited(t.position)
            ]
            if unvisited:
                target = unvisited[0]
                steps = self.planner.plan_explore(target.position, target.direction)
                self.planner.set_plan(steps)
                return Decision(
                    tool="move_to",
                    params={"target_position": list(target.position)},
                    reasoning=f"Exploring {target.direction} (frontier)",
                )

        # Strategy 2: Return to productive areas (pattern detection)
        productive = self.memory.find_productive_areas()
        for area in productive:
            if not self._recently_visited(area):
                return Decision(
                    tool="move_to",
                    params={"target_position": list(area)},
                    reasoning="Exploring productive area (resources cluster here)",
                )

        # Strategy 3: Move in an unexplored direction
        angle = (len(self.visited_positions) * 1.2) % (2 * math.pi)
        explore_pos = [
            obs.position[0] + math.cos(angle) * 10.0,
            obs.position[1],
            obs.position[2] + math.sin(angle) * 10.0,
        ]
        return Decision(
            tool="move_to",
            params={"target_position": explore_pos},
            reasoning="Exploring new direction",
        )

    # -- Helpers ------------------------------------------------------------

    def _get_inventory_counts(self, obs: Observation) -> dict[str, int]:
        """Get inventory as {item_name: quantity} from both sources."""
        counts: dict[str, int] = {}

        # From inventory items on the observation
        for item in obs.inventory:
            counts[item.name] = counts.get(item.name, 0) + item.quantity

        # From custom data (some scenes send inventory as a dict)
        if obs.custom and "inventory" in obs.custom:
            for name, qty in obs.custom["inventory"].items():
                counts[name] = counts.get(name, 0) + qty

        return counts

    def _recently_visited(
        self, position: tuple[float, float, float], threshold: float = 5.0
    ) -> bool:
        """Check if we've been near this position recently."""
        for visited in self.visited_positions[-20:]:
            if self._distance(visited, position) < threshold:
                return True
        return False

    @staticmethod
    def _distance(
        pos1: tuple[float, float, float], pos2: tuple[float, float, float]
    ) -> float:
        """Euclidean distance between two 3D positions."""
        return math.sqrt(
            (pos1[0] - pos2[0]) ** 2
            + (pos1[1] - pos2[1]) ** 2
            + (pos1[2] - pos2[2]) ** 2
        )

    @staticmethod
    def _center(
        positions: list[tuple[float, float, float]],
    ) -> tuple[float, float, float]:
        """Calculate the center point of multiple positions."""
        if not positions:
            return (0.0, 0.0, 0.0)
        n = len(positions)
        return (
            sum(p[0] for p in positions) / n,
            sum(p[1] for p in positions) / n,
            sum(p[2] for p in positions) / n,
        )

    @staticmethod
    def _escape_position(
        agent_pos: tuple[float, float, float],
        danger_pos: tuple[float, float, float],
        distance: float = 6.0,
    ) -> list[float]:
        """Calculate a safe position away from danger."""
        dx = agent_pos[0] - danger_pos[0]
        dz = agent_pos[2] - danger_pos[2]

        length = math.sqrt(dx * dx + dz * dz)
        if length > 0:
            dx = (dx / length) * distance
            dz = (dz / length) * distance
        else:
            dx, dz = distance, 0.0

        return [danger_pos[0] + dx, agent_pos[1], danger_pos[2] + dz]
