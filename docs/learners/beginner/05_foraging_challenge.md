# Foraging Challenge

Test your skills with this beginner challenge!

## The Scenario

Your agent is in a meadow with:
- **7 resources** to collect (apples, wood, stone)
- **2 hazards** to avoid (pits)
- **Unlimited time** but efficiency is tracked

## Success Criteria

| Rating | Resources | Damage | Notes |
|--------|-----------|--------|-------|
| **Gold** | 7/7 | 0 | Perfect run! |
| **Silver** | 7/7 | < 50 | Good, but took some hits |
| **Bronze** | 5+/7 | Any | Completed most objectives |

## The Challenge

Create an agent that:
1. Collects all 7 resources
2. Avoids falling into pits (25 damage each!)
3. Minimizes total distance traveled

## Starter Code

```python
from agent_runtime import SimpleAgentBehavior, SimpleContext


class ForagingChallenger(SimpleAgentBehavior):
    """
    Your challenge: Complete the foraging scenario with maximum efficiency!

    Tips:
    - Pits do 25 damage each
    - Collection range is about 2 units
    - Resources don't respawn once collected
    """

    system_prompt = "Efficient foraging agent."

    def decide(self, context: SimpleContext) -> str:
        # TODO: Implement your strategy!
        #
        # Hints:
        # 1. Always check for hazards first
        # 2. Consider resource distances when choosing targets
        # 3. Don't just go for the closest - think about paths
        #
        # Available info:
        # - context.position: Your current location
        # - context.nearby_resources: List of resources with distance
        # - context.nearby_hazards: List of hazards with distance
        # - context.inventory: Items you've collected
        # - context.tick: Current simulation tick

        # YOUR CODE HERE
        pass
```

## Hints (Try Without First!)

<details>
<summary>Hint 1: Basic Structure</summary>

```python
def decide(self, context: SimpleContext) -> str:
    # 1. Safety first
    if self._in_danger(context):
        return "move_to"

    # 2. Collect if possible
    if self._can_collect(context):
        return "collect"

    # 3. Move toward resources
    if context.nearby_resources:
        return "move_to"

    return "idle"
```
</details>

<details>
<summary>Hint 2: Danger Detection</summary>

```python
def _in_danger(self, context: SimpleContext) -> bool:
    """Check if any hazard is too close."""
    DANGER_THRESHOLD = 2.5
    for hazard in context.nearby_hazards:
        if hazard["distance"] < DANGER_THRESHOLD:
            return True
    return False
```
</details>

<details>
<summary>Hint 3: Smart Resource Selection</summary>

```python
def _best_resource(self, context: SimpleContext) -> dict | None:
    """Find the best resource to target."""
    if not context.nearby_resources:
        return None

    # Filter out resources near hazards
    safe_resources = []
    for resource in context.nearby_resources:
        is_safe = True
        for hazard in context.nearby_hazards:
            # Check if hazard is between us and resource
            if hazard["distance"] < resource["distance"]:
                is_safe = False
                break
        if is_safe:
            safe_resources.append(resource)

    if safe_resources:
        return min(safe_resources, key=lambda r: r["distance"])
    return min(context.nearby_resources, key=lambda r: r["distance"])
```
</details>

## Sample Solution

<details>
<summary>Full Solution (Try yourself first!)</summary>

```python
from agent_runtime import SimpleAgentBehavior, SimpleContext


class ForagingChallenger(SimpleAgentBehavior):
    """Efficient foraging agent for the challenge."""

    system_prompt = "Efficient foraging agent that avoids hazards."

    DANGER_DISTANCE = 2.5
    COLLECTION_RANGE = 2.0

    def decide(self, context: SimpleContext) -> str:
        # PRIORITY 1: Escape immediate danger
        closest_hazard = self._closest_hazard(context)
        if closest_hazard and closest_hazard["distance"] < self.DANGER_DISTANCE:
            return "move_to"

        # PRIORITY 2: Collect if in range
        closest_resource = self._closest_resource(context)
        if closest_resource and closest_resource["distance"] < self.COLLECTION_RANGE:
            return "collect"

        # PRIORITY 3: Move toward safe resource
        if closest_resource:
            return "move_to"

        # PRIORITY 4: All done!
        return "idle"

    def _closest_hazard(self, context: SimpleContext) -> dict | None:
        if not context.nearby_hazards:
            return None
        return min(context.nearby_hazards, key=lambda h: h["distance"])

    def _closest_resource(self, context: SimpleContext) -> dict | None:
        if not context.nearby_resources:
            return None

        # Prefer resources that don't require passing near hazards
        safe_resources = self._filter_safe_resources(context)
        if safe_resources:
            return min(safe_resources, key=lambda r: r["distance"])

        # Fall back to closest
        return min(context.nearby_resources, key=lambda r: r["distance"])

    def _filter_safe_resources(self, context: SimpleContext) -> list:
        """Filter resources that can be reached safely."""
        safe = []
        for resource in context.nearby_resources:
            is_safe = True
            for hazard in context.nearby_hazards:
                # Rough check: if hazard is closer than resource and nearby
                if hazard["distance"] < resource["distance"] and hazard["distance"] < 5.0:
                    is_safe = False
                    break
            if is_safe:
                safe.append(resource)
        return safe
```
</details>

## Metrics to Beat

The default `SimpleForager` agent achieves:
- Resources: 7/7
- Damage: ~25 (usually hits one pit)
- Time: ~60 ticks

Can you do better?

## Leaderboard

Track your progress:

| Agent | Resources | Damage | Ticks | Score |
|-------|-----------|--------|-------|-------|
| SimpleForager | 7/7 | 25 | 60 | 75 |
| YourAgent | ?/7 | ? | ? | ? |

**Score Formula:** `(resources/7 * 100) - damage`

## Next Steps

Once you've conquered this challenge:
- Try adding memory to remember explored areas
- Move to [Intermediate: Full Observations](../intermediate/01_full_observations.md)
- Learn about [Memory Systems](../intermediate/03_memory_systems.md)
