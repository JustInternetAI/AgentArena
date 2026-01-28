# Crafting Challenge

Put your intermediate skills to the test with a multi-step planning challenge!

## The Scenario

The crafting scenario requires you to:
1. **Gather raw resources** (wood, stone, fiber)
2. **Craft intermediate items** (planks, rope)
3. **Craft the final item** (a shelter)

This tests memory, planning, and state management.

## Crafting Recipes

```
Raw Resources:
  - Wood (found in forest areas)
  - Stone (found near rocks)
  - Fiber (found in grasslands)

Intermediate Crafting:
  - Planks = Wood x2
  - Rope = Fiber x3

Final Crafting:
  - Shelter = Planks x4 + Rope x2 + Stone x3
```

## Required Skills

This challenge requires everything you've learned:

| Skill | Why It's Needed |
|-------|-----------------|
| **Full Observations** | Track inventory, find specific resources |
| **Explicit Parameters** | Specify what to craft, where to move |
| **Memory** | Remember resource locations, track progress |
| **State Tracking** | Manage crafting plan, goal progress |

## Starter Code

```python
from agent_runtime import AgentBehavior, Observation, AgentDecision, ToolSchema
from agent_runtime.memory import SlidingWindowMemory


class CraftingChallenger(AgentBehavior):
    """
    Your challenge: Craft a shelter!

    You need:
    - 8 Wood (for 4 Planks)
    - 9 Fiber (for 3 Rope... wait, recipe says 2 Rope needs 6 Fiber)
    - 3 Stone

    Crafting steps:
    1. Gather Wood x8
    2. Craft Planks x4
    3. Gather Fiber x6
    4. Craft Rope x2
    5. Gather Stone x3
    6. Craft Shelter
    """

    # Crafting recipes
    RECIPES = {
        "planks": {"wood": 2},
        "rope": {"fiber": 3},
        "shelter": {"planks": 4, "rope": 2, "stone": 3}
    }

    def __init__(self):
        self.memory = SlidingWindowMemory(capacity=50)
        self.crafting_plan = []
        self.current_step = 0
        self.inventory_cache = {}

    def on_episode_start(self):
        self.memory.clear()
        self.crafting_plan = self._create_crafting_plan()
        self.current_step = 0
        self.inventory_cache = {}
        print(f"Crafting plan: {self.crafting_plan}")

    def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
        self.memory.store(observation)
        self._update_inventory_cache(observation)

        # Check if done
        if self._has_item("shelter"):
            return AgentDecision.idle(reasoning="Shelter complete!")

        # Execute current plan step
        if self.current_step < len(self.crafting_plan):
            step = self.crafting_plan[self.current_step]
            result = self._execute_step(step, observation, tools)

            # Check if step is complete
            if self._is_step_complete(step):
                self.current_step += 1
                print(f"Step complete! Moving to step {self.current_step + 1}")

            return result

        return AgentDecision.idle(reasoning="Plan complete")

    def _create_crafting_plan(self) -> list[dict]:
        """Create the optimal crafting plan."""
        return [
            {"action": "gather", "item": "wood", "quantity": 8},
            {"action": "craft", "item": "planks", "quantity": 4},
            {"action": "gather", "item": "fiber", "quantity": 6},
            {"action": "craft", "item": "rope", "quantity": 2},
            {"action": "gather", "item": "stone", "quantity": 3},
            {"action": "craft", "item": "shelter", "quantity": 1},
        ]

    def _execute_step(self, step: dict, obs: Observation, tools: list[ToolSchema]) -> AgentDecision:
        """Execute a single plan step."""
        action = step["action"]

        if action == "gather":
            return self._gather(step["item"], step["quantity"], obs)
        elif action == "craft":
            return self._craft(step["item"], obs, tools)

        return AgentDecision.idle()

    def _gather(self, item_type: str, needed: int, obs: Observation) -> AgentDecision:
        """Gather resources of a specific type."""
        have = self._count_item(item_type)
        if have >= needed:
            return AgentDecision.idle(reasoning=f"Have enough {item_type}")

        # Find resource of this type
        target = None
        for resource in obs.nearby_resources:
            if resource.type.lower() == item_type.lower():
                target = resource
                break

        if target:
            if target.distance < 2.0:
                return AgentDecision(
                    tool="collect",
                    params={"resource_id": target.name},
                    reasoning=f"Collecting {target.name} ({have}/{needed} {item_type})"
                )
            else:
                return AgentDecision(
                    tool="move_to",
                    params={"target_position": list(target.position)},
                    reasoning=f"Moving to {target.name}"
                )

        # No target visible - explore
        return self._explore(obs)

    def _craft(self, item: str, obs: Observation, tools: list[ToolSchema]) -> AgentDecision:
        """Craft an item if we have the materials."""
        # Check if craft tool is available
        tool_names = [t.name for t in tools]
        if "craft" not in tool_names:
            return AgentDecision.idle(reasoning="Craft tool not available")

        # Check if we have materials
        recipe = self.RECIPES.get(item, {})
        for material, quantity in recipe.items():
            if self._count_item(material) < quantity:
                return AgentDecision.idle(reasoning=f"Need more {material}")

        return AgentDecision(
            tool="craft",
            params={"recipe": item},
            reasoning=f"Crafting {item}"
        )

    def _explore(self, obs: Observation) -> AgentDecision:
        """Explore to find more resources."""
        # TODO: Implement exploration logic
        # - Use memory to avoid revisiting
        # - Move toward unexplored areas
        import random
        angle = random.uniform(0, 6.28)
        pos = obs.position
        target = [
            pos[0] + 10 * __import__('math').cos(angle),
            pos[1],
            pos[2] + 10 * __import__('math').sin(angle)
        ]
        return AgentDecision(
            tool="move_to",
            params={"target_position": target},
            reasoning="Exploring for resources"
        )

    def _is_step_complete(self, step: dict) -> bool:
        """Check if current step is complete."""
        action = step["action"]
        if action == "gather":
            return self._count_item(step["item"]) >= step["quantity"]
        elif action == "craft":
            return self._has_item(step["item"])
        return False

    def _update_inventory_cache(self, obs: Observation):
        """Update inventory tracking."""
        self.inventory_cache = {}
        for item in obs.inventory:
            name = item.name.lower()
            self.inventory_cache[name] = self.inventory_cache.get(name, 0) + item.quantity

    def _count_item(self, item_type: str) -> int:
        """Count items of a type in inventory."""
        return self.inventory_cache.get(item_type.lower(), 0)

    def _has_item(self, item_name: str) -> bool:
        """Check if we have a specific item."""
        return self._count_item(item_name) > 0
```

## Challenges to Solve

The starter code is incomplete! You need to:

### Challenge 1: Smarter Exploration

The `_explore` method is random. Improve it to:
- Remember where you've been
- Systematically cover the map
- Return to known resource areas

### Challenge 2: Handle Hazards

The scenario has hazards! Add:
- Hazard detection in `_gather`
- Safe pathfinding around obstacles
- Emergency escape when needed

### Challenge 3: Optimize Resource Gathering

The current code gathers one resource at a time. Improve it to:
- Gather multiple resource types if nearby
- Plan efficient routes between resources
- Avoid backtracking

### Challenge 4: Handle Failures

What if crafting fails? What if a resource disappears?
- Add error handling in `on_tool_result`
- Replan when things go wrong
- Track crafting attempts

## Hints

<details>
<summary>Hint: Smarter Exploration</summary>

```python
def __init__(self):
    # Add exploration state
    self.explored_grid = set()
    self.grid_size = 5  # 5x5 unit grid cells

def _explore(self, obs: Observation) -> AgentDecision:
    # Mark current cell as explored
    pos = obs.position
    cell = (int(pos[0] // self.grid_size), int(pos[2] // self.grid_size))
    self.explored_grid.add(cell)

    # Find nearest unexplored cell
    for radius in range(1, 10):
        for dx in range(-radius, radius + 1):
            for dz in range(-radius, radius + 1):
                test_cell = (cell[0] + dx, cell[1] + dz)
                if test_cell not in self.explored_grid:
                    target = [
                        test_cell[0] * self.grid_size + self.grid_size / 2,
                        0,
                        test_cell[1] * self.grid_size + self.grid_size / 2
                    ]
                    return AgentDecision(
                        tool="move_to",
                        params={"target_position": target},
                        reasoning=f"Exploring cell {test_cell}"
                    )

    return AgentDecision.idle(reasoning="Fully explored")
```
</details>

<details>
<summary>Hint: Hazard Handling</summary>

```python
def _gather(self, item_type: str, needed: int, obs: Observation) -> AgentDecision:
    # Check for danger first!
    for hazard in obs.nearby_hazards:
        if hazard.distance < 3.0:
            return self._escape_hazard(hazard, obs)

    # ... rest of gathering logic
```
</details>

## Success Criteria

| Rating | Result | Time |
|--------|--------|------|
| **Gold** | Shelter crafted, 0 damage | < 200 ticks |
| **Silver** | Shelter crafted | < 300 ticks |
| **Bronze** | All materials gathered | Any |

## Next Steps

Once you've conquered this challenge:
- [Advanced: LLM Backends](../advanced/01_llm_backends.md) - Let an LLM do the planning
- [Advanced: Custom Memory](../advanced/03_custom_memory.md) - Build sophisticated memory systems
