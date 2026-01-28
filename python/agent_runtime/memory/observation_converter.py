"""
Converter for Agent Observations to semantic memory.

This is Layer 3 (Domain-Specific) - converts agent observations
to/from the generic semantic memory format.
"""

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..schemas import Observation

from long_term_memory_module.semantic_memory import MemoryConverter

logger = logging.getLogger(__name__)


class ObservationConverter(MemoryConverter):
    """
    Converts Agent Observations to/from semantic memory format.

    This class encapsulates all the domain-specific logic for working
    with agent observations in the memory system.
    """

    def to_text(self, observation: "Observation") -> str:
        """
        Convert an observation to searchable text representation.

        Args:
            observation: Agent observation to convert

        Returns:
            Text representation suitable for semantic embedding

        Example:
            >>> converter = ObservationConverter()
            >>> text = converter.to_text(observation)
            >>> # "At position (10.0, 0.0, 5.0) with health 100 and energy 90. ..."
        """
        parts = []

        # Basic state
        parts.append(f"At position {observation.position}")
        parts.append(f"with health {observation.health:.0f} and energy {observation.energy:.0f}")

        # Resources
        if observation.nearby_resources:
            resource_desc = ", ".join(
                f"{r.name} at distance {r.distance:.1f}" for r in observation.nearby_resources
            )
            parts.append(f"Nearby resources: {resource_desc}")

        # Hazards
        if observation.nearby_hazards:
            hazard_desc = ", ".join(
                f"{h.name} (damage {h.damage:.0f}) at distance {h.distance:.1f}"
                for h in observation.nearby_hazards
            )
            parts.append(f"Nearby hazards: {hazard_desc}")

        # Inventory
        if observation.inventory:
            inventory_desc = ", ".join(
                f"{item.name} x{item.quantity}" for item in observation.inventory
            )
            parts.append(f"Inventory: {inventory_desc}")

        # Visible entities
        if observation.visible_entities:
            entity_desc = ", ".join(
                f"{e.type} at distance {e.distance:.1f}" for e in observation.visible_entities
            )
            parts.append(f"Visible entities: {entity_desc}")

        return ". ".join(parts) + "."

    def to_metadata(self, observation: "Observation") -> dict[str, Any]:
        """
        Extract structured metadata from observation.

        Args:
            observation: Agent observation

        Returns:
            Dictionary of metadata for filtering and retrieval

        Example:
            >>> metadata = converter.to_metadata(observation)
            >>> # {"agent_id": "agent_1", "tick": 42, ...}
        """
        metadata = {
            "agent_id": observation.agent_id,
            "tick": observation.tick,
            "position": observation.position,
            "health": observation.health,
            "energy": observation.energy,
        }

        # Add counts for quick filtering
        metadata["num_resources"] = len(observation.nearby_resources)
        metadata["num_hazards"] = len(observation.nearby_hazards)
        metadata["num_inventory"] = len(observation.inventory)
        metadata["num_entities"] = len(observation.visible_entities)

        # Add flags for quick boolean filtering
        metadata["has_resources"] = len(observation.nearby_resources) > 0
        metadata["has_hazards"] = len(observation.nearby_hazards) > 0
        metadata["has_inventory"] = len(observation.inventory) > 0

        # Add rotation if available
        if observation.rotation:
            metadata["rotation"] = observation.rotation

        # Add velocity if available
        if observation.velocity:
            metadata["velocity"] = observation.velocity

        return metadata

    def from_dict(self, data: dict[str, Any]) -> "Observation":
        """
        Reconstruct an Observation from stored memory data.

        Args:
            data: Dictionary from semantic memory (includes 'text', 'metadata', etc.)

        Returns:
            Reconstructed Observation object

        Note:
            This creates a minimal observation with core fields. Extended fields
            like nearby_resources, hazards, etc. are not preserved (they're in the
            text representation for semantic search, not for exact reconstruction).

        Example:
            >>> obs = converter.from_dict(memory_result)
            >>> print(obs.tick, obs.position)
        """
        from ..schemas import Observation

        metadata = data.get("metadata", {})

        # Create observation with core fields from metadata
        obs = Observation(
            agent_id=metadata.get("agent_id", "unknown"),
            tick=metadata.get("tick", 0),
            position=tuple(metadata.get("position", (0.0, 0.0, 0.0))),
            rotation=tuple(metadata["rotation"]) if "rotation" in metadata else None,
            velocity=tuple(metadata["velocity"]) if "velocity" in metadata else None,
            health=metadata.get("health", 100.0),
            energy=metadata.get("energy", 100.0),
        )

        # Note: We don't reconstruct nearby_resources, hazards, inventory, etc.
        # because they're in the text for semantic search but not needed for
        # exact reconstruction. If you need full reconstruction, store them
        # as additional metadata fields.

        return obs


# Global instance for convenience
observation_converter = ObservationConverter()
