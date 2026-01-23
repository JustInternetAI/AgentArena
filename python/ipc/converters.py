"""
Converters between IPC messages and agent runtime schemas.
"""

from agent_runtime.schemas import (
    AgentDecision,
    EntityInfo,
    HazardInfo,
    ItemInfo,
    Observation,
    ResourceInfo,
    ToolSchema,
)

from .messages import ActionMessage, PerceptionMessage


def perception_to_observation(perception: PerceptionMessage) -> Observation:
    """
    Convert IPC PerceptionMessage to agent_runtime Observation.

    Args:
        perception: PerceptionMessage from Godot

    Returns:
        Observation object for agent behavior
    """
    # Convert position to tuple
    if isinstance(perception.position, list):
        pos_list = perception.position
        position: tuple[float, float, float] = (pos_list[0], pos_list[1], pos_list[2])
    else:
        position = perception.position

    # Convert rotation to tuple if present
    rotation: tuple[float, float, float] | None = None
    if perception.rotation:
        if isinstance(perception.rotation, list):
            rot_list = perception.rotation
            rotation = (rot_list[0], rot_list[1], rot_list[2])
        else:
            rotation = perception.rotation

    # Convert velocity to tuple if present
    velocity: tuple[float, float, float] | None = None
    if perception.velocity:
        if isinstance(perception.velocity, list):
            vel_list = perception.velocity
            velocity = (vel_list[0], vel_list[1], vel_list[2])
        else:
            velocity = perception.velocity

    # Parse visible entities
    visible_entities = []
    for entity_data in perception.visible_entities:
        entity_pos = entity_data.get("position", [0, 0, 0])
        if isinstance(entity_pos, list):
            entity_pos = tuple(entity_pos)

        visible_entities.append(
            EntityInfo(
                id=entity_data.get("id", ""),
                type=entity_data.get("type", "unknown"),
                position=entity_pos,
                distance=entity_data.get("distance", 0.0),
                metadata=entity_data.get("metadata", {}),
            )
        )

    # Parse nearby resources from custom_data
    nearby_resources = []
    resources_data = perception.custom_data.get("nearby_resources", [])
    for resource_data in resources_data:
        resource_pos = resource_data.get("position", [0, 0, 0])
        if isinstance(resource_pos, list):
            resource_pos = tuple(resource_pos)

        nearby_resources.append(
            ResourceInfo(
                name=resource_data.get("name", ""),
                type=resource_data.get("type", "unknown"),
                position=resource_pos,
                distance=resource_data.get("distance", 0.0),
            )
        )

    # Parse nearby hazards from custom_data
    nearby_hazards = []
    hazards_data = perception.custom_data.get("nearby_hazards", [])
    for hazard_data in hazards_data:
        hazard_pos = hazard_data.get("position", [0, 0, 0])
        if isinstance(hazard_pos, list):
            hazard_pos = tuple(hazard_pos)

        nearby_hazards.append(
            HazardInfo(
                name=hazard_data.get("name", ""),
                type=hazard_data.get("type", "unknown"),
                position=hazard_pos,
                distance=hazard_data.get("distance", 0.0),
                damage=hazard_data.get("damage", 0.0),
            )
        )

    # Parse inventory
    inventory = []
    for item_data in perception.inventory:
        inventory.append(
            ItemInfo(
                id=item_data.get("id", ""),
                name=item_data.get("name", ""),
                quantity=item_data.get("quantity", 1),
            )
        )

    # Extract custom data (excluding resources and hazards which we've already parsed)
    custom = {
        k: v
        for k, v in perception.custom_data.items()
        if k not in ["nearby_resources", "nearby_hazards"]
    }

    return Observation(
        agent_id=perception.agent_id,
        tick=perception.tick,
        position=position,
        rotation=rotation,
        velocity=velocity,
        visible_entities=visible_entities,
        nearby_resources=nearby_resources,
        nearby_hazards=nearby_hazards,
        inventory=inventory,
        health=perception.health,
        energy=perception.energy,
        custom=custom,
    )


def decision_to_action(decision: AgentDecision, agent_id: str, tick: int) -> ActionMessage:
    """
    Convert agent_runtime AgentDecision to IPC ActionMessage.

    Args:
        decision: AgentDecision from agent behavior
        agent_id: Agent identifier
        tick: Current tick number

    Returns:
        ActionMessage for Godot
    """
    return ActionMessage(
        agent_id=agent_id,
        tick=tick,
        tool=decision.tool,
        params=decision.params,
        reasoning=decision.reasoning or "",
    )


def tool_schema_to_dict(schema: ToolSchema) -> dict:
    """
    Convert ToolSchema to dictionary for IPC.

    Args:
        schema: ToolSchema object

    Returns:
        Dictionary representation
    """
    return {
        "name": schema.name,
        "description": schema.description,
        "parameters": schema.parameters,
    }
