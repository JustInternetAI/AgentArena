# Team Challenge

Put all your advanced skills to the test with a multi-agent cooperative challenge!

## The Scenario

Your team of 3 agents must work together to:
1. **Explore** the map to find resources
2. **Gather** materials from different locations
3. **Build** a shelter before time runs out
4. **Protect** each other from hazards

No single agent can complete this alone - success requires coordination!

## The Map

```
┌─────────────────────────────────────────────────────────────┐
│                          FOREST                              │
│   🌲 Wood  🌲 Wood  🌲 Wood                                 │
│                                    ⚠️ Pit                    │
├─────────────────────────────────────────────────────────────┤
│              │                           │                   │
│   GRASSLAND  │      CENTER CLEARING      │     ROCKY AREA   │
│   🌿 Fiber   │                           │      🪨 Stone    │
│   🌿 Fiber   │      [Start Position]     │      🪨 Stone    │
│   🌿 Fiber   │                           │      🪨 Stone    │
│              │                           │  ⚠️ Pit           │
├─────────────────────────────────────────────────────────────┤
│                          SOUTH WOODS                         │
│                    🌲 Wood  🌲 Wood                          │
│         ⚠️ Pit                      ⚠️ Pit                  │
└─────────────────────────────────────────────────────────────┘
```

## Success Criteria

| Rating | Requirements |
|--------|-------------|
| **Platinum** | Shelter built, 0 damage, < 150 ticks |
| **Gold** | Shelter built, < 25 damage, < 200 ticks |
| **Silver** | Shelter built, < 50 damage, < 300 ticks |
| **Bronze** | All materials gathered |

## Required Materials

```
Shelter = 4 Planks + 2 Rope + 3 Stone

Planks (x4) = 8 Wood total
Rope (x2) = 6 Fiber total
Stone = 3 Stone

Total raw materials needed:
- 8 Wood (Forest areas)
- 6 Fiber (Grassland)
- 3 Stone (Rocky area)
```

## Starter Code

```python
from agent_runtime import AgentBehavior, Observation, AgentDecision, ToolSchema
from agent_runtime.memory import SlidingWindowMemory
from enum import Enum
from dataclasses import dataclass


# ===== SHARED BLACKBOARD =====

class Blackboard:
    """Shared communication between agents."""
    _instance = None
    _data = {}

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def post(self, key: str, value, agent_id: str, tick: int, ttl: int = 20):
        self._data[key] = {
            "value": value,
            "posted_by": agent_id,
            "tick": tick,
            "expires": tick + ttl
        }

    def read(self, key: str, tick: int):
        entry = self._data.get(key)
        if entry and tick <= entry["expires"]:
            return entry["value"]
        return None

    def read_all(self, prefix: str, tick: int) -> dict:
        return {
            k: v["value"] for k, v in self._data.items()
            if k.startswith(prefix) and tick <= v["expires"]
        }

    def claim(self, resource_id: str, agent_id: str, tick: int) -> bool:
        key = f"claim:{resource_id}"
        existing = self.read(key, tick)
        if existing and existing != agent_id:
            return False
        self.post(key, agent_id, agent_id, tick, ttl=10)
        return True


# ===== ROLE DEFINITIONS =====

class Role(Enum):
    SCOUT = "scout"
    GATHERER = "gatherer"
    BUILDER = "builder"


# ===== BASE TEAM AGENT =====

class TeamAgent(AgentBehavior):
    """Base class for team agents."""

    def __init__(self, agent_id: str, role: Role):
        self.agent_id = agent_id
        self.role = role
        self.blackboard = Blackboard.get()
        self.memory = SlidingWindowMemory(capacity=30)

    def on_episode_start(self):
        self.memory.clear()

    def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
        self.memory.store(observation)
        self._update_status(observation)

        # Check for danger first (all roles)
        danger = self._check_danger(observation)
        if danger:
            return danger

        # Role-specific behavior
        return self._role_behavior(observation, tools)

    def _update_status(self, obs: Observation):
        """Update status on blackboard."""
        self.blackboard.post(
            f"agent:{self.agent_id}",
            {
                "position": obs.position,
                "health": obs.health,
                "role": self.role.value,
                "inventory": [item.name for item in obs.inventory]
            },
            self.agent_id,
            obs.tick
        )

    def _check_danger(self, obs: Observation) -> AgentDecision | None:
        """Check for immediate danger."""
        for hazard in obs.nearby_hazards:
            if hazard.distance < 2.5:
                # Warn others
                self.blackboard.post(
                    f"danger:{hazard.name}",
                    {"position": hazard.position, "damage": hazard.damage},
                    self.agent_id,
                    obs.tick
                )
                # Escape
                return self._escape_hazard(hazard, obs)
        return None

    def _escape_hazard(self, hazard, obs: Observation) -> AgentDecision:
        """Move away from hazard."""
        # Move opposite direction
        dx = obs.position[0] - hazard.position[0]
        dz = obs.position[2] - hazard.position[2]
        dist = (dx*dx + dz*dz) ** 0.5
        if dist > 0:
            target = [
                obs.position[0] + (dx / dist) * 5,
                obs.position[1],
                obs.position[2] + (dz / dist) * 5
            ]
        else:
            target = [obs.position[0] + 5, obs.position[1], obs.position[2]]

        return AgentDecision(
            tool="move_to",
            params={"target_position": target},
            reasoning="Escaping hazard!"
        )

    def _role_behavior(self, obs: Observation, tools: list[ToolSchema]) -> AgentDecision:
        """Override in subclass."""
        raise NotImplementedError


# ===== SCOUT AGENT =====

class ScoutAgent(TeamAgent):
    """Explores and reports resource locations."""

    def __init__(self, agent_id: str):
        super().__init__(agent_id, Role.SCOUT)
        self.explored_cells = set()
        self.grid_size = 10.0

    def _role_behavior(self, obs: Observation, tools: list[ToolSchema]) -> AgentDecision:
        # Report any resources found
        for resource in obs.nearby_resources:
            self.blackboard.post(
                f"resource:{resource.name}",
                {
                    "position": resource.position,
                    "type": resource.type,
                    "found_at_tick": obs.tick
                },
                self.agent_id,
                obs.tick,
                ttl=100
            )

        # Mark current area explored
        cell = (
            int(obs.position[0] // self.grid_size),
            int(obs.position[2] // self.grid_size)
        )
        self.explored_cells.add(cell)

        # Find unexplored area
        return self._explore_next(obs)

    def _explore_next(self, obs: Observation) -> AgentDecision:
        """Move to nearest unexplored cell."""
        current = (
            int(obs.position[0] // self.grid_size),
            int(obs.position[2] // self.grid_size)
        )

        # Check surrounding cells
        for radius in range(1, 6):
            for dx in range(-radius, radius + 1):
                for dz in range(-radius, radius + 1):
                    cell = (current[0] + dx, current[1] + dz)
                    if cell not in self.explored_cells:
                        target = [
                            cell[0] * self.grid_size + self.grid_size / 2,
                            0,
                            cell[1] * self.grid_size + self.grid_size / 2
                        ]
                        return AgentDecision(
                            tool="move_to",
                            params={"target_position": target},
                            reasoning=f"Exploring cell {cell}"
                        )

        return AgentDecision.idle(reasoning="Map fully explored")


# ===== GATHERER AGENT =====

class GathererAgent(TeamAgent):
    """Collects resources and delivers to builder."""

    RESOURCE_PRIORITY = {"stone": 3, "fiber": 2, "wood": 1}

    def __init__(self, agent_id: str):
        super().__init__(agent_id, Role.GATHERER)
        self.target_resource = None

    def _role_behavior(self, obs: Observation, tools: list[ToolSchema]) -> AgentDecision:
        # Check if we can collect something nearby
        for resource in obs.nearby_resources:
            if resource.distance < 2.0:
                if self.blackboard.claim(resource.name, self.agent_id, obs.tick):
                    return AgentDecision(
                        tool="collect",
                        params={"resource_id": resource.name},
                        reasoning=f"Collecting {resource.name}"
                    )

        # Find a resource from blackboard
        known = self.blackboard.read_all("resource:", obs.tick)
        if known:
            # Sort by priority
            prioritized = sorted(
                known.items(),
                key=lambda x: self.RESOURCE_PRIORITY.get(x[1]["type"], 0),
                reverse=True
            )

            for key, data in prioritized:
                resource_id = key.replace("resource:", "")
                if self.blackboard.claim(resource_id, self.agent_id, obs.tick):
                    return AgentDecision(
                        tool="move_to",
                        params={"target_position": list(data["position"])},
                        reasoning=f"Going to collect {resource_id}"
                    )

        # Nothing to collect - help explore
        return self._random_move(obs)

    def _random_move(self, obs: Observation) -> AgentDecision:
        import random
        import math
        angle = random.uniform(0, 2 * math.pi)
        target = [
            obs.position[0] + 8 * math.cos(angle),
            0,
            obs.position[2] + 8 * math.sin(angle)
        ]
        return AgentDecision(
            tool="move_to",
            params={"target_position": target},
            reasoning="Searching for resources"
        )


# ===== BUILDER AGENT =====

class BuilderAgent(TeamAgent):
    """Crafts items from gathered resources."""

    RECIPES = {
        "planks": {"wood": 2},
        "rope": {"fiber": 3},
        "shelter": {"planks": 4, "rope": 2, "stone": 3}
    }

    CRAFT_ORDER = ["planks", "planks", "planks", "planks", "rope", "rope", "shelter"]

    def __init__(self, agent_id: str):
        super().__init__(agent_id, Role.BUILDER)
        self.craft_index = 0

    def _role_behavior(self, obs: Observation, tools: list[ToolSchema]) -> AgentDecision:
        # Check what we can craft
        if "craft" not in [t.name for t in tools]:
            return AgentDecision.idle(reasoning="Craft not available")

        # Get team inventory
        team_inventory = self._get_team_inventory(obs)

        # Check current recipe
        if self.craft_index < len(self.CRAFT_ORDER):
            recipe_name = self.CRAFT_ORDER[self.craft_index]
            recipe = self.RECIPES[recipe_name]

            # Check if we have materials
            can_craft = all(
                team_inventory.get(mat, 0) >= qty
                for mat, qty in recipe.items()
            )

            if can_craft:
                self.craft_index += 1
                return AgentDecision(
                    tool="craft",
                    params={"recipe": recipe_name},
                    reasoning=f"Crafting {recipe_name}"
                )
            else:
                # Report what we need
                needed = {
                    mat: qty - team_inventory.get(mat, 0)
                    for mat, qty in recipe.items()
                    if team_inventory.get(mat, 0) < qty
                }
                self.blackboard.post(
                    "needed_materials",
                    needed,
                    self.agent_id,
                    obs.tick
                )
                return AgentDecision.idle(
                    reasoning=f"Waiting for materials: {needed}"
                )

        # All done!
        return AgentDecision.idle(reasoning="Shelter complete!")

    def _get_team_inventory(self, obs: Observation) -> dict[str, int]:
        """Aggregate inventory across team."""
        inventory = {}

        # Add own inventory
        for item in obs.inventory:
            name = item.name.lower()
            inventory[name] = inventory.get(name, 0) + item.quantity

        # Add other agents' inventory from blackboard
        for agent_status in self.blackboard.read_all("agent:", obs.tick).values():
            for item_name in agent_status.get("inventory", []):
                name = item_name.lower()
                inventory[name] = inventory.get(name, 0) + 1

        return inventory


# ===== TEAM COORDINATOR =====

def create_team():
    """Create the team of agents."""
    return {
        "scout_001": ScoutAgent("scout_001"),
        "gatherer_001": GathererAgent("gatherer_001"),
        "builder_001": BuilderAgent("builder_001"),
    }
```

## Challenges to Solve

The starter code provides the framework, but you need to improve:

### Challenge 1: Smarter Resource Prioritization

The gatherer collects resources in a basic priority order. Improve it to:
- Check what the builder actually needs next
- Avoid going for resources another gatherer is already targeting
- Consider distance and danger when choosing

### Challenge 2: Hazard Avoidance

The escape behavior is reactive. Improve it to:
- Remember hazard locations
- Plan paths that avoid known hazards
- Warn teammates about hazards proactively

### Challenge 3: Dynamic Role Switching

Sometimes the team would be more efficient if roles changed:
- If all resources are found, scout becomes gatherer
- If materials are ready, gatherers help protect builder
- If an agent is hurt, others cover their duties

### Challenge 4: Communication Efficiency

The blackboard can get cluttered. Improve communication:
- Prioritize important messages
- Clean up stale information
- Use targeted messages instead of broadcasts when appropriate

## Hints

<details>
<summary>Hint: Builder-Driven Gathering</summary>

```python
def _role_behavior(self, obs: Observation, tools: list[ToolSchema]) -> AgentDecision:
    # Check what builder needs
    needed = self.blackboard.read("needed_materials", obs.tick)
    if needed:
        # Prioritize gathering what's actually needed
        for material, quantity in needed.items():
            resources = [
                r for r in obs.nearby_resources
                if r.type.lower() == material
            ]
            if resources:
                target = min(resources, key=lambda r: r.distance)
                # ... go collect
```
</details>

<details>
<summary>Hint: Hazard Memory</summary>

```python
class SafetyAwareAgent(TeamAgent):
    def __init__(self, agent_id: str, role: Role):
        super().__init__(agent_id, role)
        self.known_hazards = {}  # name -> position

    def _check_danger(self, obs: Observation) -> AgentDecision | None:
        # Update hazard memory
        for hazard in obs.nearby_hazards:
            self.known_hazards[hazard.name] = hazard.position

        # Check if path to target crosses known hazard
        # ...
```
</details>

<details>
<summary>Hint: Role Switching</summary>

```python
def _should_switch_role(self, obs: Observation) -> Role | None:
    # Scout becomes gatherer when exploration complete
    if self.role == Role.SCOUT:
        explored = self.blackboard.read("exploration_complete", obs.tick)
        if explored:
            return Role.GATHERER

    # Gatherer becomes guard when materials gathered
    if self.role == Role.GATHERER:
        needed = self.blackboard.read("needed_materials", obs.tick)
        if not needed:
            return Role.GUARD

    return None
```
</details>

## Success Metrics

Track these during your run:

| Metric | Target |
|--------|--------|
| Exploration coverage | > 80% |
| Resources collected | 17/17 |
| Total team damage | < 25 |
| Ticks to completion | < 200 |
| Communication efficiency | < 50 messages |

## Leaderboard

| Team Strategy | Ticks | Damage | Rating |
|--------------|-------|--------|--------|
| Baseline | 280 | 50 | Silver |
| Optimized Gathering | 220 | 25 | Gold |
| Full Coordination | 150 | 0 | Platinum |
| Your Team | ? | ? | ? |

## What You've Learned

Completing this challenge means you've mastered:
- Multi-agent coordination patterns
- Shared memory and communication
- Role-based behavior design
- Dynamic replanning
- LLM-powered decision making
- Complex goal decomposition

## Next Steps

Congratulations on completing the advanced path! Consider:
- Building your own scenarios
- Creating new agent architectures
- Contributing to Agent Arena
- Exploring the [API Reference](../api_reference/) for deeper customization
