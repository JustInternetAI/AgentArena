"""
Foraging Scenario Definition

A Tier 1 (Beginner) scenario that teaches basic agent concepts:
- Perception and observation processing
- Tool use for movement
- Goal-directed behavior
- Hazard avoidance
"""

from agent_runtime.schemas import Constraint, Goal, Metric, ScenarioDefinition

FORAGING_SCENARIO = ScenarioDefinition(
    # Identity
    name="Foraging Challenge",
    id="foraging",
    tier=1,
    version="1.0.0",
    # Description
    description=(
        "Navigate a 3D environment to collect resources (berries, wood, stone) "
        "while avoiding hazards (fire pits, spike traps). Your agent receives "
        "observations about nearby objects and must decide where to move."
    ),
    backstory=(
        "You are a survival agent in a wilderness environment. Your camp needs "
        "resources to survive the coming winter. Gather as many resources as "
        "possible while staying safe from environmental hazards."
    ),
    # Goals
    goals=[
        Goal(
            name="Collect All Resources",
            description="Collect all 7 resources scattered around the environment.",
            success_condition="resources_collected >= 7",
            priority=1,
            optional=False,
        ),
        Goal(
            name="Minimize Damage",
            description="Avoid hazards to minimize damage taken.",
            success_condition="damage_taken == 0",
            priority=2,
            optional=True,
        ),
        Goal(
            name="Efficient Pathing",
            description="Collect resources using the shortest path possible.",
            success_condition="distance_traveled < optimal_distance * 1.5",
            priority=3,
            optional=True,
        ),
    ],
    # Constraints
    constraints=[
        Constraint(
            name="Movement Only",
            description="You can only interact with the world by moving. Resources are collected automatically when you are close enough.",
            penalty=None,
        ),
        Constraint(
            name="Limited Perception",
            description="You can only see objects within your perception radius (50 units) that are not blocked by obstacles.",
            penalty=None,
        ),
        Constraint(
            name="Hazard Damage",
            description="Touching hazards causes damage. Fire deals 10 damage, pits deal 25 damage.",
            penalty="Health reduction",
        ),
    ],
    # Available tools
    available_tools=[
        "move_to",
        "idle",
    ],
    # Success metrics
    metrics=[
        Metric(
            name="resources_collected",
            description="Number of resources successfully collected",
            unit="count",
            optimize="maximize",
        ),
        Metric(
            name="damage_taken",
            description="Total damage received from hazards",
            unit="HP",
            optimize="minimize",
        ),
        Metric(
            name="distance_traveled",
            description="Total distance moved by the agent",
            unit="meters",
            optimize="minimize",
        ),
        Metric(
            name="time_elapsed",
            description="Time taken to complete the scenario",
            unit="seconds",
            optimize="minimize",
        ),
        Metric(
            name="efficiency_score",
            description="Combined score based on resources, damage, and efficiency",
            unit="points",
            optimize="maximize",
        ),
    ],
    success_threshold={
        "resources_collected": 7,  # Must collect all
    },
    # Perception info
    perception_info={
        "perception_radius": "50 units - objects beyond this distance are not visible",
        "line_of_sight": "Obstacles (trees, rocks, bushes) block vision",
        "position": "Your current [x, y, z] coordinates",
        "nearby_resources": "List of visible resources with name, type, position, and distance",
        "nearby_hazards": "List of visible hazards with name, type, position, and distance",
        "resources_collected": "How many resources you've collected so far",
        "resources_remaining": "How many resources are left to collect",
        "damage_taken": "Total damage received",
    },
    # Resource types
    resource_types=[
        {
            "type": "berry",
            "name": "Berry Bush",
            "description": "A bush with edible berries. Easy to spot by its red color.",
        },
        {
            "type": "wood",
            "name": "Wood Pile",
            "description": "Fallen logs ready for collection.",
        },
        {
            "type": "stone",
            "name": "Stone Deposit",
            "description": "Rocks suitable for tools and building.",
        },
    ],
    # Hazard types
    hazard_types=[
        {
            "type": "fire",
            "name": "Fire Pit",
            "damage": 10,
            "description": "An open flame that causes burn damage on contact.",
        },
        {
            "type": "pit",
            "name": "Spike Pit",
            "damage": 25,
            "description": "A concealed pit trap that causes significant damage.",
        },
    ],
    # Hints for learners
    hints=[
        "Start by moving toward the nearest visible resource.",
        "Check for hazards between you and your target before moving.",
        "If no resources are visible, try exploring in a direction you haven't been.",
        "The move_to tool takes a target_position parameter as [x, y, z] coordinates.",
        "Resources are collected automatically when you're within 2 units of them.",
    ],
    # Learning objectives
    learning_objectives=[
        "How to process observation data (position, nearby objects)",
        "How to use the move_to tool with coordinate parameters",
        "Basic decision-making: choosing between multiple targets",
        "Hazard awareness: checking for dangers before moving",
        "Goal-directed behavior: prioritizing objectives",
    ],
)
