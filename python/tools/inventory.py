"""
Inventory and item interaction tools.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def pickup_item(item_id: str) -> dict[str, Any]:
    """
    Pick up an item from the world.

    Args:
        item_id: ID of item to pick up

    Returns:
        Success status and item info
    """
    logger.debug(f"Picking up item {item_id}")

    return {
        "success": True,
        "item": {"id": item_id, "type": "unknown"},
    }


def collect(target: str) -> dict[str, Any]:
    """
    Collect a resource from the world.

    This is the user-friendly version of pickup_item, using "target"
    to match the natural language in prompts.

    Args:
        target: Name of the resource to collect (e.g., "Berry1", "Stone")

    Returns:
        Success status and collected resource info
    """
    logger.debug(f"Collecting resource: {target}")

    return {
        "success": True,
        "collected": target,
        "message": f"Collected {target}",
    }


def drop_item(item_id: str) -> dict[str, bool]:
    """
    Drop an item from inventory.

    Args:
        item_id: ID of item to drop

    Returns:
        Success status
    """
    logger.debug(f"Dropping item {item_id}")

    return {"success": True}


def use_item(item_id: str, target: str | None = None) -> dict[str, Any]:
    """
    Use an item from inventory.

    Args:
        item_id: ID of item to use
        target: Optional target entity ID

    Returns:
        Success status and effect info
    """
    logger.debug(f"Using item {item_id} on target {target}")

    return {
        "success": True,
        "effect": {},
    }


def get_inventory() -> list[dict[str, Any]]:
    """
    Get current inventory contents.

    Returns:
        List of items in inventory
    """
    logger.debug("Getting inventory")

    return []


def craft_item(recipe: str, ingredients: list[str]) -> dict[str, Any]:
    """
    Craft an item using ingredients.

    Args:
        recipe: Recipe name/ID
        ingredients: List of ingredient item IDs

    Returns:
        Success status and crafted item info
    """
    logger.debug(f"Crafting {recipe} with {len(ingredients)} ingredients")

    return {
        "success": True,
        "item": {"id": "crafted_item", "type": recipe},
    }


def register_inventory_tools(dispatcher: Any) -> None:
    """Register inventory tools with dispatcher."""
    dispatcher.register_tool(
        name="collect",
        function=collect,
        description="Collect a resource from the world",
        parameters={
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Name of the resource to collect"},
            },
            "required": ["target"],
        },
        returns={"type": "object"},
    )

    dispatcher.register_tool(
        name="pickup_item",
        function=pickup_item,
        description="Pick up an item from the world",
        parameters={
            "type": "object",
            "properties": {
                "item_id": {"type": "string", "description": "Item ID to pick up"},
            },
            "required": ["item_id"],
        },
        returns={"type": "object"},
    )

    dispatcher.register_tool(
        name="drop_item",
        function=drop_item,
        description="Drop an item from inventory",
        parameters={
            "type": "object",
            "properties": {
                "item_id": {"type": "string", "description": "Item ID to drop"},
            },
            "required": ["item_id"],
        },
        returns={"type": "object"},
    )

    dispatcher.register_tool(
        name="use_item",
        function=use_item,
        description="Use an item from inventory",
        parameters={
            "type": "object",
            "properties": {
                "item_id": {"type": "string"},
                "target": {"type": "string", "description": "Optional target entity ID"},
            },
            "required": ["item_id"],
        },
        returns={"type": "object"},
    )

    dispatcher.register_tool(
        name="get_inventory",
        function=get_inventory,
        description="Get current inventory contents",
        parameters={"type": "object", "properties": {}},
        returns={"type": "array", "items": {"type": "object"}},
    )

    dispatcher.register_tool(
        name="craft_item",
        function=craft_item,
        description="Craft an item using a recipe",
        parameters={
            "type": "object",
            "properties": {
                "recipe": {"type": "string", "description": "Recipe name or ID"},
                "ingredients": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of ingredient item IDs",
                },
            },
            "required": ["recipe", "ingredients"],
        },
        returns={"type": "object"},
    )

    logger.info("Registered inventory tools")
