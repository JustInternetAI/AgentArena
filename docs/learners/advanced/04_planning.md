# Planning and Goal Decomposition

Advanced agents don't just react - they plan ahead. This guide covers techniques for multi-step reasoning and goal decomposition.

## The Planning Problem

Consider building a shelter. A reactive agent might:
1. See wood → collect wood
2. See more wood → collect more wood
3. Eventually stumble into having enough materials

A planning agent would:
1. Analyze goal: "Build shelter requires 4 planks, 2 rope, 3 stone"
2. Decompose: "Need 8 wood for planks, 6 fiber for rope, 3 stone"
3. Plan steps: "Gather wood first (nearest), then fiber, then stone"
4. Execute plan while adapting to obstacles

## Goal Decomposition

Break complex goals into actionable subgoals:

```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class GoalStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class Goal:
    """A goal with possible subgoals."""
    name: str
    description: str
    status: GoalStatus = GoalStatus.PENDING
    subgoals: list["Goal"] = None
    preconditions: list[str] = None  # Goals that must complete first
    success_condition: str = None     # How to check if complete

    def __post_init__(self):
        if self.subgoals is None:
            self.subgoals = []
        if self.preconditions is None:
            self.preconditions = []


class GoalDecomposer:
    """Decomposes high-level goals into actionable steps."""

    # Crafting recipes
    RECIPES = {
        "shelter": {"planks": 4, "rope": 2, "stone": 3},
        "planks": {"wood": 2},
        "rope": {"fiber": 3},
    }

    # Resource locations
    RESOURCE_LOCATIONS = {
        "wood": "forest",
        "stone": "rocks",
        "fiber": "grassland",
    }

    def decompose(self, goal_name: str) -> Goal:
        """Decompose a goal into a tree of subgoals."""
        if goal_name == "build_shelter":
            return self._decompose_crafting("shelter")
        elif goal_name.startswith("gather_"):
            resource = goal_name.replace("gather_", "")
            return self._decompose_gathering(resource)
        elif goal_name.startswith("craft_"):
            item = goal_name.replace("craft_", "")
            return self._decompose_crafting(item)
        else:
            return Goal(name=goal_name, description=f"Unknown goal: {goal_name}")

    def _decompose_crafting(self, item: str) -> Goal:
        """Decompose a crafting goal."""
        recipe = self.RECIPES.get(item, {})
        if not recipe:
            return Goal(name=f"craft_{item}", description=f"Craft {item}")

        # Create material gathering subgoals
        subgoals = []
        for material, quantity in recipe.items():
            if material in self.RECIPES:
                # Material is itself crafted
                subgoals.append(Goal(
                    name=f"craft_{material}_x{quantity}",
                    description=f"Craft {quantity}x {material}",
                    subgoals=[self._decompose_crafting(material) for _ in range(quantity)]
                ))
            else:
                # Raw material - need to gather
                subgoals.append(Goal(
                    name=f"gather_{material}_x{quantity}",
                    description=f"Gather {quantity}x {material}",
                    success_condition=f"inventory contains >= {quantity} {material}"
                ))

        # Create the crafting goal
        return Goal(
            name=f"craft_{item}",
            description=f"Craft {item}",
            subgoals=subgoals,
            preconditions=[sg.name for sg in subgoals],
            success_condition=f"inventory contains {item}"
        )

    def _decompose_gathering(self, resource: str) -> Goal:
        """Decompose a gathering goal."""
        location = self.RESOURCE_LOCATIONS.get(resource, "unknown")
        return Goal(
            name=f"gather_{resource}",
            description=f"Gather {resource} from {location}",
            subgoals=[
                Goal(name=f"find_{resource}", description=f"Locate {resource}"),
                Goal(name=f"collect_{resource}", description=f"Collect {resource}",
                     preconditions=[f"find_{resource}"])
            ]
        )
```

## Hierarchical Task Network (HTN) Planning

Structure plans as a hierarchy of tasks:

```python
from typing import Callable


@dataclass
class Task:
    """A task that can be primitive (directly executable) or compound (decomposable)."""
    name: str
    is_primitive: bool
    action: str | None = None        # For primitive tasks
    params: dict | None = None       # For primitive tasks
    decomposition: list["Task"] | None = None  # For compound tasks
    precondition: Callable | None = None


class HTNPlanner:
    """Hierarchical Task Network planner."""

    def __init__(self):
        self.methods: dict[str, list[Callable]] = {}  # Decomposition methods

    def register_method(self, task_name: str, method: Callable):
        """Register a decomposition method for a compound task."""
        if task_name not in self.methods:
            self.methods[task_name] = []
        self.methods[task_name].append(method)

    def plan(self, goal: str, state: dict) -> list[Task]:
        """Generate a plan to achieve the goal."""
        initial_task = Task(name=goal, is_primitive=False)
        return self._decompose(initial_task, state)

    def _decompose(self, task: Task, state: dict) -> list[Task]:
        """Recursively decompose a task into primitive actions."""
        if task.is_primitive:
            return [task]

        # Try each method until one works
        methods = self.methods.get(task.name, [])
        for method in methods:
            try:
                subtasks = method(state)
                if subtasks:
                    plan = []
                    for subtask in subtasks:
                        plan.extend(self._decompose(subtask, state))
                    return plan
            except Exception:
                continue

        # No method worked
        return []


# Example usage
def setup_shelter_planner() -> HTNPlanner:
    """Set up an HTN planner for shelter building."""
    planner = HTNPlanner()

    def build_shelter_method(state: dict) -> list[Task]:
        """Decompose shelter building into material gathering and crafting."""
        return [
            Task("gather_materials", is_primitive=False),
            Task("craft_components", is_primitive=False),
            Task("assemble_shelter", is_primitive=True, action="craft", params={"recipe": "shelter"})
        ]

    def gather_materials_method(state: dict) -> list[Task]:
        """Decompose material gathering."""
        tasks = []
        needed = {"wood": 8, "fiber": 6, "stone": 3}
        for material, amount in needed.items():
            have = state.get("inventory", {}).get(material, 0)
            if have < amount:
                tasks.append(Task(
                    f"gather_{material}",
                    is_primitive=True,
                    action="gather",
                    params={"target": material, "quantity": amount - have}
                ))
        return tasks

    def craft_components_method(state: dict) -> list[Task]:
        """Decompose component crafting."""
        return [
            Task("craft_planks", is_primitive=True, action="craft", params={"recipe": "planks", "count": 4}),
            Task("craft_rope", is_primitive=True, action="craft", params={"recipe": "rope", "count": 2})
        ]

    planner.register_method("build_shelter", build_shelter_method)
    planner.register_method("gather_materials", gather_materials_method)
    planner.register_method("craft_components", craft_components_method)

    return planner
```

## LLM-Based Planning

Let the LLM do the planning:

```python
from agent_runtime import LLMAgentBehavior, Observation, AgentDecision, ToolSchema
import json


class LLMPlanningAgent(LLMAgentBehavior):
    """Agent that uses LLM for planning."""

    def __init__(self):
        super().__init__(backend="anthropic", model="claude-3-sonnet-20240229")
        self.current_plan: list[dict] = []
        self.plan_step = 0

    def on_episode_start(self) -> None:
        self.current_plan = []
        self.plan_step = 0

    def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
        # If no plan or plan complete, create new plan
        if not self.current_plan or self.plan_step >= len(self.current_plan):
            self.current_plan = self._create_plan(observation, tools)
            self.plan_step = 0

            if not self.current_plan:
                return AgentDecision.idle(reasoning="No plan needed")

        # Execute current step
        step = self.current_plan[self.plan_step]
        self.plan_step += 1

        return AgentDecision(
            tool=step["action"],
            params=step.get("params", {}),
            reasoning=f"Plan step {self.plan_step}/{len(self.current_plan)}: {step.get('reason', '')}"
        )

    def _create_plan(self, obs: Observation, tools: list[ToolSchema]) -> list[dict]:
        """Use LLM to create a plan."""
        context = self._build_planning_context(obs, tools)

        response = self.complete(
            prompt=context,
            system="""You are a planning agent. Given the current state and goal,
            create a step-by-step plan. Return ONLY a JSON array of steps.

            Each step should have:
            - "action": the tool to use
            - "params": parameters for the tool
            - "reason": why this step is needed

            Example:
            [
                {"action": "move_to", "params": {"target_position": [10, 0, 5]}, "reason": "Go to wood location"},
                {"action": "collect", "params": {"resource_id": "wood_001"}, "reason": "Collect wood"}
            ]""",
            temperature=0.2  # Low temperature for consistent planning
        )

        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

        return []

    def _build_planning_context(self, obs: Observation, tools: list[ToolSchema]) -> str:
        return f"""
CURRENT STATE:
Position: {obs.position}
Inventory: {[item.name for item in obs.inventory]}
Health: {obs.health}/100

VISIBLE RESOURCES:
{self._format_resources(obs.nearby_resources)}

HAZARDS:
{self._format_hazards(obs.nearby_hazards)}

GOAL: Collect all visible resources while avoiding hazards.

Create a plan to achieve this goal. Consider:
1. Order of resource collection (nearest first, or safest first?)
2. Paths that avoid hazards
3. Efficient movement (minimize backtracking)

Return your plan as a JSON array.
"""
```

## Reactive Replanning

Adapt plans when situations change:

```python
class ReactivePlanningAgent(LLMAgentBehavior):
    """Agent that replans when needed."""

    def __init__(self):
        super().__init__(backend="anthropic", model="claude-3-haiku-20240307")
        self.plan: list[dict] = []
        self.plan_step = 0
        self.last_observation_hash = ""

    def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
        # Check if we need to replan
        if self._should_replan(observation):
            print("Situation changed - replanning...")
            self.plan = self._create_plan(observation, tools)
            self.plan_step = 0

        # Execute plan
        if self.plan and self.plan_step < len(self.plan):
            step = self.plan[self.plan_step]

            # Verify step is still valid
            if self._is_step_valid(step, observation):
                self.plan_step += 1
                return AgentDecision(
                    tool=step["action"],
                    params=step["params"],
                    reasoning=step.get("reason", "Following plan")
                )
            else:
                # Step invalid - replan
                print(f"Step invalid: {step}")
                self.plan = self._create_plan(observation, tools)
                self.plan_step = 0

        return AgentDecision.idle(reasoning="Plan complete or empty")

    def _should_replan(self, obs: Observation) -> bool:
        """Check if situation has changed enough to warrant replanning."""
        current_hash = self._hash_situation(obs)

        # No plan yet
        if not self.plan:
            self.last_observation_hash = current_hash
            return True

        # Significant change detected
        if current_hash != self.last_observation_hash:
            self.last_observation_hash = current_hash
            # Only replan if change is significant
            if self._is_significant_change(obs):
                return True

        return False

    def _is_significant_change(self, obs: Observation) -> bool:
        """Determine if changes warrant replanning."""
        # New hazard appeared nearby
        for hazard in obs.nearby_hazards:
            if hazard.distance < 3.0:
                return True

        # Health dropped significantly
        if obs.health < 30:
            return True

        return False

    def _is_step_valid(self, step: dict, obs: Observation) -> bool:
        """Check if a plan step is still executable."""
        action = step["action"]

        if action == "collect":
            # Check if resource still exists
            resource_id = step["params"].get("resource_id")
            return any(r.name == resource_id for r in obs.nearby_resources)

        if action == "move_to":
            # Check if path is safe
            target = step["params"].get("target_position")
            # Could add hazard checking here
            return True

        return True

    def _hash_situation(self, obs: Observation) -> str:
        """Create a hash of the current situation."""
        return f"{len(obs.nearby_resources)}_{len(obs.nearby_hazards)}_{obs.health//10}"
```

## Plan Execution with Monitoring

Track plan progress and handle failures:

```python
@dataclass
class PlanStep:
    """A step in a plan with execution tracking."""
    action: str
    params: dict
    reason: str
    status: str = "pending"  # pending, executing, completed, failed
    attempts: int = 0
    max_attempts: int = 3


class MonitoredPlanExecutor:
    """Executes plans with monitoring and failure handling."""

    def __init__(self):
        self.steps: list[PlanStep] = []
        self.current_step_index = 0

    def set_plan(self, steps: list[dict]) -> None:
        """Set a new plan to execute."""
        self.steps = [
            PlanStep(
                action=s["action"],
                params=s.get("params", {}),
                reason=s.get("reason", "")
            )
            for s in steps
        ]
        self.current_step_index = 0

    def get_current_step(self) -> PlanStep | None:
        """Get the current step to execute."""
        if self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    def on_step_complete(self, success: bool) -> None:
        """Called when current step completes."""
        if self.current_step_index >= len(self.steps):
            return

        step = self.steps[self.current_step_index]

        if success:
            step.status = "completed"
            self.current_step_index += 1
        else:
            step.attempts += 1
            if step.attempts >= step.max_attempts:
                step.status = "failed"
                print(f"Step failed after {step.attempts} attempts: {step.action}")
                # Skip to next step
                self.current_step_index += 1
            else:
                step.status = "pending"
                print(f"Step failed, retrying ({step.attempts}/{step.max_attempts})")

    def is_plan_complete(self) -> bool:
        """Check if plan is complete."""
        return self.current_step_index >= len(self.steps)

    def get_progress(self) -> str:
        """Get plan progress summary."""
        completed = sum(1 for s in self.steps if s.status == "completed")
        failed = sum(1 for s in self.steps if s.status == "failed")
        return f"Progress: {completed}/{len(self.steps)} complete, {failed} failed"
```

## Next Steps

- [Multi-Agent](05_multi_agent.md) - Coordinate plans between multiple agents
- [Team Challenge](06_team_challenge.md) - Apply planning to a team scenario
