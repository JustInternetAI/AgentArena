"""
World query tools - vision rays, entity detection, distance calculations.
"""

from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


def raycast(
    origin: List[float],
    direction: List[float],
    max_distance: float = 100.0,
) -> Dict[str, Any]:
    """
    Cast a ray from origin in direction to detect objects.

    Args:
        origin: [x, y, z] starting position
        direction: [x, y, z] direction vector
        max_distance: Maximum ray distance

    Returns:
        Dictionary with hit information or None if no hit
    """
    # TODO: Integrate with Godot physics raycast
    logger.debug(f"Raycast from {origin} in direction {direction}")

    return {
        "hit": False,
        "distance": max_distance,
        "position": None,
        "normal": None,
        "collider": None,
    }


def get_nearby_entities(
    position: List[float],
    radius: float,
    entity_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Get all entities within radius of position.

    Args:
        position: [x, y, z] center position
        radius: Search radius
        entity_type: Optional filter by entity type

    Returns:
        List of entity dictionaries with id, type, position, etc.
    """
    # TODO: Query Godot scene for entities
    logger.debug(f"Querying entities near {position} within radius {radius}")

    return []


def get_visible_entities(
    agent_position: List[float],
    agent_forward: List[float],
    fov_degrees: float = 90.0,
    max_distance: float = 50.0,
) -> List[Dict[str, Any]]:
    """
    Get entities visible to the agent based on FOV cone.

    Args:
        agent_position: Agent's [x, y, z] position
        agent_forward: Agent's forward direction vector
        fov_degrees: Field of view in degrees
        max_distance: Maximum visibility distance

    Returns:
        List of visible entities
    """
    # TODO: Implement FOV-based visibility check
    logger.debug(f"Checking visible entities from {agent_position}")

    return []


def measure_distance(
    point_a: List[float],
    point_b: List[float],
) -> float:
    """
    Calculate Euclidean distance between two points.

    Args:
        point_a: First [x, y, z] point
        point_b: Second [x, y, z] point

    Returns:
        Distance between points
    """
    import math

    dx = point_b[0] - point_a[0]
    dy = point_b[1] - point_a[1]
    dz = point_b[2] - point_a[2]

    return math.sqrt(dx * dx + dy * dy + dz * dz)


def register_world_query_tools(dispatcher: Any) -> None:
    """
    Register all world query tools with the dispatcher.

    Args:
        dispatcher: ToolDispatcher instance
    """
    dispatcher.register_tool(
        name="raycast",
        function=raycast,
        description="Cast a ray to detect objects in the world",
        parameters={
            "type": "object",
            "properties": {
                "origin": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Ray origin [x, y, z]",
                },
                "direction": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Ray direction [x, y, z]",
                },
                "max_distance": {
                    "type": "number",
                    "description": "Maximum ray distance",
                    "default": 100.0,
                },
            },
            "required": ["origin", "direction"],
        },
        returns={
            "type": "object",
            "properties": {
                "hit": {"type": "boolean"},
                "distance": {"type": "number"},
                "position": {"type": "array"},
                "normal": {"type": "array"},
                "collider": {"type": "object"},
            },
        },
    )

    dispatcher.register_tool(
        name="get_nearby_entities",
        function=get_nearby_entities,
        description="Get all entities within radius",
        parameters={
            "type": "object",
            "properties": {
                "position": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Center position [x, y, z]",
                },
                "radius": {
                    "type": "number",
                    "description": "Search radius",
                },
                "entity_type": {
                    "type": "string",
                    "description": "Filter by entity type (optional)",
                },
            },
            "required": ["position", "radius"],
        },
        returns={
            "type": "array",
            "items": {"type": "object"},
        },
    )

    dispatcher.register_tool(
        name="get_visible_entities",
        function=get_visible_entities,
        description="Get entities visible within FOV cone",
        parameters={
            "type": "object",
            "properties": {
                "agent_position": {
                    "type": "array",
                    "items": {"type": "number"},
                },
                "agent_forward": {
                    "type": "array",
                    "items": {"type": "number"},
                },
                "fov_degrees": {
                    "type": "number",
                    "default": 90.0,
                },
                "max_distance": {
                    "type": "number",
                    "default": 50.0,
                },
            },
            "required": ["agent_position", "agent_forward"],
        },
        returns={
            "type": "array",
            "items": {"type": "object"},
        },
    )

    dispatcher.register_tool(
        name="measure_distance",
        function=measure_distance,
        description="Calculate distance between two points",
        parameters={
            "type": "object",
            "properties": {
                "point_a": {"type": "array", "items": {"type": "number"}},
                "point_b": {"type": "array", "items": {"type": "number"}},
            },
            "required": ["point_a", "point_b"],
        },
        returns={
            "type": "number",
        },
    )

    logger.info("Registered world query tools")
