"""
Navigation and exploration tools.

These tools help agents navigate the world and explore unknown areas.
They work with the VisibilityTracker in Godot to provide exploration-aware navigation.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def plan_path(target_position: list[float], avoid_hazards: bool = True) -> dict[str, Any]:
    """
    Plan a path from current position to target using Godot's navigation system.

    This is a query tool - it returns path information but doesn't move the agent.
    Use move_to to actually move along the path.

    Args:
        target_position: [x, y, z] target position
        avoid_hazards: If true, try to route around known hazards

    Returns:
        Path planning result:
        - success: bool
        - waypoints: List of [x, y, z] positions along the path
        - distance: Total path distance
        - blocked: True if no path exists
        - reason: Explanation if blocked
    """
    logger.debug(f"Planning path to {target_position}, avoid_hazards={avoid_hazards}")

    # This is handled by Godot's NavigationServer3D
    # The actual implementation is in SceneController/SimpleAgent
    return {
        "success": True,
        "waypoints": [target_position],  # Simplified - Godot will compute actual path
        "distance": 0.0,
        "blocked": False,
        "avoid_hazards": avoid_hazards,
    }


def explore_direction(direction: str) -> dict[str, Any]:
    """
    Get a target position for exploring in a specific direction.

    Use this when you want to explore unexplored areas. The tool returns
    a navigable position in the specified direction that leads to unexplored territory.

    Args:
        direction: One of "north", "south", "east", "west",
                   "northeast", "northwest", "southeast", "southwest"

    Returns:
        Exploration target:
        - success: bool
        - target_position: [x, y, z] position to move to
        - distance: Distance to the target
        - has_unexplored: True if there are unexplored areas in this direction
        - reason: Explanation if no unexplored areas found
    """
    valid_directions = [
        "north",
        "south",
        "east",
        "west",
        "northeast",
        "northwest",
        "southeast",
        "southwest",
    ]

    direction_lower = direction.lower()
    if direction_lower not in valid_directions:
        logger.warning(f"Invalid direction: {direction}")
        return {
            "success": False,
            "has_unexplored": False,
            "reason": f"Invalid direction. Use one of: {', '.join(valid_directions)}",
        }

    logger.debug(f"Getting exploration target for direction: {direction_lower}")

    # This is handled by Godot's VisibilityTracker
    # The actual implementation queries the tracker for frontier positions
    return {
        "success": True,
        "direction": direction_lower,
        "target_position": [0, 0, 0],  # Placeholder - Godot fills this in
        "distance": 0.0,
        "has_unexplored": True,
    }


def get_exploration_status() -> dict[str, Any]:
    """
    Get the current exploration status.

    Returns information about how much of the world has been explored
    and where unexplored frontiers are located.

    Returns:
        Exploration status:
        - exploration_percentage: Percentage of world explored (0-100)
        - frontiers: Dict mapping direction -> distance to nearest frontier
        - suggested_targets: List of {direction, position, distance} for exploration
    """
    logger.debug("Getting exploration status")

    # This is a query tool - Godot provides the actual data
    # The exploration info is typically included in observations already
    return {
        "success": True,
        "exploration_percentage": 0.0,  # Placeholder
        "frontiers": {},
        "suggested_targets": [],
    }


def register_navigation_tools(dispatcher: Any) -> None:
    """Register navigation tools with dispatcher."""
    dispatcher.register_tool(
        name="plan_path",
        function=plan_path,
        description=(
            "Plan a path to a target position. Returns waypoints and distance. "
            "Use this to check if a destination is reachable before moving."
        ),
        parameters={
            "type": "object",
            "properties": {
                "target_position": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Target [x, y, z] position to plan path to",
                },
                "avoid_hazards": {
                    "type": "boolean",
                    "description": "If true, try to route around known hazards",
                    "default": True,
                },
            },
            "required": ["target_position"],
        },
        returns={
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "waypoints": {"type": "array"},
                "distance": {"type": "number"},
                "blocked": {"type": "boolean"},
            },
        },
    )

    dispatcher.register_tool(
        name="explore_direction",
        function=explore_direction,
        description=(
            "Get a position to explore in a specific direction. "
            "Use this when you want to explore unexplored areas. "
            "Returns a target position at the frontier of explored territory."
        ),
        parameters={
            "type": "object",
            "properties": {
                "direction": {
                    "type": "string",
                    "enum": [
                        "north",
                        "south",
                        "east",
                        "west",
                        "northeast",
                        "northwest",
                        "southeast",
                        "southwest",
                    ],
                    "description": "Direction to explore",
                },
            },
            "required": ["direction"],
        },
        returns={
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "target_position": {"type": "array"},
                "distance": {"type": "number"},
                "has_unexplored": {"type": "boolean"},
            },
        },
    )

    dispatcher.register_tool(
        name="get_exploration_status",
        function=get_exploration_status,
        description=(
            "Get current exploration status including percentage explored "
            "and locations of unexplored frontiers."
        ),
        parameters={"type": "object", "properties": {}},
        returns={
            "type": "object",
            "properties": {
                "exploration_percentage": {"type": "number"},
                "frontiers": {"type": "object"},
                "suggested_targets": {"type": "array"},
            },
        },
    )

    logger.info("Registered navigation tools: plan_path, explore_direction, get_exploration_status")
