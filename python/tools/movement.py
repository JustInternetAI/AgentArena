"""
Movement and navigation tools.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def move_to(target_position: list[float], speed: float = 1.0) -> dict[str, Any]:
    """
    Move agent to target position.

    Args:
        target_position: [x, y, z] target position
        speed: Movement speed multiplier

    Returns:
        Success status and path information
    """
    # TODO: Integrate with Godot navigation
    logger.debug(f"Moving to {target_position} at speed {speed}")

    return {
        "success": True,
        "path": [],
        "estimated_time": 0.0,
    }


def navigate_to(target_position: list[float]) -> dict[str, Any]:
    """
    Navigate to target using pathfinding.

    Args:
        target_position: [x, y, z] target position

    Returns:
        Path waypoints and navigation status
    """
    # TODO: Use Godot NavigationServer
    logger.debug(f"Navigating to {target_position}")

    return {
        "success": True,
        "waypoints": [],
        "distance": 0.0,
    }


def stop_movement() -> dict[str, bool]:
    """
    Stop all current movement.

    Returns:
        Success status
    """
    logger.debug("Stopping movement")

    return {"success": True}


def rotate_to_face(target_position: list[float]) -> dict[str, Any]:
    """
    Rotate agent to face target position.

    Args:
        target_position: [x, y, z] position to face

    Returns:
        Success status and rotation angle
    """
    logger.debug(f"Rotating to face {target_position}")

    return {
        "success": True,
        "angle": 0.0,
    }


def register_movement_tools(dispatcher: Any) -> None:
    """Register movement tools with dispatcher."""
    dispatcher.register_tool(
        name="move_to",
        function=move_to,
        description="Move to a target position",
        parameters={
            "type": "object",
            "properties": {
                "target_position": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Target [x, y, z] position",
                },
                "speed": {
                    "type": "number",
                    "description": "Movement speed multiplier",
                    "default": 1.0,
                },
            },
            "required": ["target_position"],
        },
        returns={"type": "object"},
    )

    dispatcher.register_tool(
        name="navigate_to",
        function=navigate_to,
        description="Navigate to target using pathfinding",
        parameters={
            "type": "object",
            "properties": {
                "target_position": {
                    "type": "array",
                    "items": {"type": "number"},
                },
            },
            "required": ["target_position"],
        },
        returns={"type": "object"},
    )

    dispatcher.register_tool(
        name="stop_movement",
        function=stop_movement,
        description="Stop all movement",
        parameters={"type": "object", "properties": {}},
        returns={"type": "object"},
    )

    dispatcher.register_tool(
        name="rotate_to_face",
        function=rotate_to_face,
        description="Rotate to face a target position",
        parameters={
            "type": "object",
            "properties": {
                "target_position": {
                    "type": "array",
                    "items": {"type": "number"},
                },
            },
            "required": ["target_position"],
        },
        returns={"type": "object"},
    )

    logger.info("Registered movement tools")
