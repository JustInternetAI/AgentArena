"""
Spatial Memory for world mapping.

This module provides a memory system that tracks objects (resources, hazards, entities)
by their position in the world, allowing agents to build a "mental map" of their
environment and remember where things are even when out of line-of-sight.

Example:
    >>> from agent_runtime.memory import SpatialMemory
    >>> from agent_runtime.schemas import WorldObject
    >>>
    >>> memory = SpatialMemory()
    >>>
    >>> # Store objects from observations
    >>> memory.update_from_observation(observation)
    >>>
    >>> # Query by position
    >>> nearby = memory.query_near_position((10, 0, 5), radius=20)
    >>>
    >>> # Query by type
    >>> resources = memory.query_by_type("resource")
    >>>
    >>> # Semantic search
    >>> food = memory.query_semantic("food to collect")
"""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .base import AgentMemory

if TYPE_CHECKING:
    from ..schemas import ExperienceEvent, Observation, WorldObject

logger = logging.getLogger(__name__)


@dataclass
class SpatialQueryResult:
    """Result from a spatial memory query."""

    obj: "WorldObject"
    distance: float  # Distance from query position
    score: float  # Semantic similarity score (if semantic query)
    staleness: int  # Ticks since last seen


class SpatialMemory(AgentMemory):
    """
    Memory system for tracking world objects spatially.

    Combines:
    - In-memory spatial index (for fast proximity queries)
    - Optional vector store (for semantic queries)
    - Object status tracking (collected, destroyed, etc.)

    This allows agents to:
    - Remember where resources and hazards are located
    - Query "what's near me" even for out-of-sight objects
    - Track which resources have been collected
    - Build a mental map of the environment

    Example:
        >>> memory = SpatialMemory()
        >>>
        >>> # Each tick, update with current observation
        >>> memory.update_from_observation(observation)
        >>>
        >>> # Find remembered resources near a position
        >>> nearby = memory.query_near_position(
        ...     position=(10, 0, 5),
        ...     radius=30,
        ...     object_type="resource"
        ... )
        >>>
        >>> # Get all known hazards
        >>> hazards = memory.query_by_type("hazard")
        >>>
        >>> # Semantic search for food
        >>> food = memory.query_semantic("berries or apples to eat")
    """

    def __init__(
        self,
        enable_semantic: bool = True,
        embedding_model: str = "all-MiniLM-L6-v2",
        similarity_threshold: float = 0.3,
        stale_threshold: int = 100,  # Consider objects stale after N ticks unseen
    ):
        """
        Initialize spatial memory.

        Args:
            enable_semantic: Whether to enable semantic search (requires sentence-transformers)
            embedding_model: Model for semantic embeddings
            similarity_threshold: Minimum score for semantic matches
            stale_threshold: Ticks after which unseen objects are considered stale
        """
        # Primary storage: name -> WorldObject
        self._objects: dict[str, "WorldObject"] = {}

        # Spatial index: grid-based for fast proximity queries
        self._grid_size = 10.0  # Grid cell size
        self._spatial_grid: dict[tuple[int, int, int], set[str]] = {}

        # Semantic search (optional)
        self._semantic_memory = None
        self._enable_semantic = enable_semantic
        self._embedding_model = embedding_model
        self._similarity_threshold = similarity_threshold

        # Staleness tracking
        self._stale_threshold = stale_threshold
        self._current_tick = 0

        # Experience tracking
        self._experiences: list["ExperienceEvent"] = []
        self._max_experiences: int = 50

        if enable_semantic:
            self._init_semantic_memory()

        logger.info(
            f"Initialized SpatialMemory (semantic={enable_semantic}, "
            f"stale_threshold={stale_threshold})"
        )

    def _init_semantic_memory(self):
        """Initialize semantic memory component."""
        try:
            from long_term_memory_module import SemanticMemory

            self._semantic_memory = SemanticMemory(
                to_text=self._object_to_text,
                to_metadata=self._object_to_metadata,
                from_dict=self._object_from_dict,
                embedding_model=self._embedding_model,
                index_type="FlatIP",
            )
            logger.debug("Semantic memory initialized")
        except ImportError:
            logger.warning("long_term_memory_module not available, semantic search disabled")
            self._enable_semantic = False

    def _object_to_text(self, obj: "WorldObject") -> str:
        """Convert WorldObject to searchable text."""
        parts = [
            f"{obj.object_type} named {obj.name}",
            f"type {obj.subtype}",
            f"at position {obj.position}",
        ]
        if obj.damage > 0:
            parts.append(f"deals {obj.damage} damage")
        if obj.status != "active":
            parts.append(f"status {obj.status}")
        return ", ".join(parts)

    def _object_to_metadata(self, obj: "WorldObject") -> dict[str, Any]:
        """Extract metadata from WorldObject."""
        return {
            "name": obj.name,
            "object_type": obj.object_type,
            "subtype": obj.subtype,
            "position": obj.position,
            "last_seen_tick": obj.last_seen_tick,
            "status": obj.status,
            "damage": obj.damage,
        }

    def _object_from_dict(self, data: dict[str, Any]) -> "WorldObject":
        """Reconstruct WorldObject from memory data."""
        from ..schemas import WorldObject

        metadata = data.get("metadata", {})
        return WorldObject(
            name=metadata.get("name", "unknown"),
            object_type=metadata.get("object_type", "unknown"),
            subtype=metadata.get("subtype", "unknown"),
            position=tuple(metadata.get("position", (0, 0, 0))),
            last_seen_tick=metadata.get("last_seen_tick", 0),
            status=metadata.get("status", "active"),
            damage=metadata.get("damage", 0.0),
            metadata=metadata.get("metadata", {}),
        )

    def _pos_to_grid(self, pos: tuple[float, float, float]) -> tuple[int, int, int]:
        """Convert world position to grid cell coordinates."""
        return (
            int(pos[0] // self._grid_size),
            int(pos[1] // self._grid_size),
            int(pos[2] // self._grid_size),
        )

    def _add_to_grid(self, obj: "WorldObject"):
        """Add object to spatial grid."""
        cell = self._pos_to_grid(obj.position)
        if cell not in self._spatial_grid:
            self._spatial_grid[cell] = set()
        self._spatial_grid[cell].add(obj.name)

    def _remove_from_grid(self, obj: "WorldObject"):
        """Remove object from spatial grid."""
        cell = self._pos_to_grid(obj.position)
        if cell in self._spatial_grid:
            self._spatial_grid[cell].discard(obj.name)
            if not self._spatial_grid[cell]:
                del self._spatial_grid[cell]

    def _get_nearby_cells(
        self, pos: tuple[float, float, float], radius: float
    ) -> list[tuple[int, int, int]]:
        """Get all grid cells within radius of a position."""
        center = self._pos_to_grid(pos)
        cells_per_axis = int(radius / self._grid_size) + 1

        cells = []
        for dx in range(-cells_per_axis, cells_per_axis + 1):
            for dy in range(-cells_per_axis, cells_per_axis + 1):
                for dz in range(-cells_per_axis, cells_per_axis + 1):
                    cells.append((center[0] + dx, center[1] + dy, center[2] + dz))
        return cells

    def store(self, observation: "Observation") -> None:
        """
        Store/update objects from an observation (AgentMemory interface).

        This is the main entry point - call each tick to update the world map.

        Args:
            observation: Current observation from Godot
        """
        self.update_from_observation(observation)

    def update_from_observation(self, observation: "Observation") -> None:
        """
        Update spatial memory with objects from current observation.

        - Adds new objects
        - Updates positions of known objects
        - Refreshes last_seen_tick for visible objects

        Args:
            observation: Current observation from Godot
        """
        from ..schemas import WorldObject

        self._current_tick = observation.tick

        # Process resources
        for resource in observation.nearby_resources:
            obj = WorldObject.from_resource(resource, observation.tick)
            self._store_or_update(obj)

        # Process hazards
        for hazard in observation.nearby_hazards:
            obj = WorldObject.from_hazard(hazard, observation.tick)
            self._store_or_update(obj)

        # Process entities
        for entity in observation.visible_entities:
            obj = WorldObject.from_entity(entity, observation.tick)
            self._store_or_update(obj)

        logger.debug(
            f"Updated spatial memory from tick {observation.tick}: "
            f"{len(self._objects)} total objects"
        )

    def _store_or_update(self, obj: "WorldObject") -> None:
        """Store a new object or update existing one."""
        existing = self._objects.get(obj.name)

        if existing:
            # Update existing object
            self._remove_from_grid(existing)

            # Preserve status if already collected/destroyed
            if existing.status in ("collected", "destroyed"):
                obj.status = existing.status

            self._objects[obj.name] = obj
            self._add_to_grid(obj)

            # Update semantic memory
            if self._semantic_memory:
                # Remove old entry and add new
                self._semantic_memory.store(obj)
        else:
            # New object
            self._objects[obj.name] = obj
            self._add_to_grid(obj)

            if self._semantic_memory:
                self._semantic_memory.store(obj)

    def mark_collected(self, name: str) -> bool:
        """
        Mark an object as collected (e.g., resource picked up).

        Args:
            name: Object name

        Returns:
            True if object was found and marked
        """
        obj = self._objects.get(name)
        if obj:
            obj.status = "collected"
            logger.debug(f"Marked {name} as collected")
            return True
        return False

    def mark_destroyed(self, name: str) -> bool:
        """
        Mark an object as destroyed (e.g., hazard removed).

        Args:
            name: Object name

        Returns:
            True if object was found and marked
        """
        obj = self._objects.get(name)
        if obj:
            obj.status = "destroyed"
            logger.debug(f"Marked {name} as destroyed")
            return True
        return False

    def query_near_position(
        self,
        position: tuple[float, float, float],
        radius: float = 50.0,
        object_type: str | None = None,
        include_collected: bool = False,
        include_stale: bool = True,
    ) -> list[SpatialQueryResult]:
        """
        Query objects near a position.

        Args:
            position: Center position to search from
            radius: Search radius
            object_type: Filter by type ("resource", "hazard", "entity")
            include_collected: Include collected/destroyed objects
            include_stale: Include objects not seen recently

        Returns:
            List of SpatialQueryResult sorted by distance
        """
        results = []

        # Get candidate objects from nearby grid cells
        candidate_names: set[str] = set()
        for cell in self._get_nearby_cells(position, radius):
            if cell in self._spatial_grid:
                candidate_names.update(self._spatial_grid[cell])

        # Filter and score candidates
        for name in candidate_names:
            obj = self._objects.get(name)
            if not obj:
                continue

            # Type filter
            if object_type and obj.object_type != object_type:
                continue

            # Status filter
            if not include_collected and obj.status in ("collected", "destroyed"):
                continue

            # Distance check
            dist = obj.distance_to(position)
            if dist > radius:
                continue

            # Staleness check
            staleness = self._current_tick - obj.last_seen_tick
            if not include_stale and staleness > self._stale_threshold:
                continue

            results.append(
                SpatialQueryResult(obj=obj, distance=dist, score=1.0, staleness=staleness)
            )

        # Sort by distance
        results.sort(key=lambda r: r.distance)
        return results

    def query_by_type(
        self,
        object_type: str,
        subtype: str | None = None,
        include_collected: bool = False,
    ) -> list["WorldObject"]:
        """
        Query all objects of a given type.

        Args:
            object_type: "resource", "hazard", or "entity"
            subtype: Optional subtype filter (e.g., "berry", "fire")
            include_collected: Include collected/destroyed objects

        Returns:
            List of WorldObjects matching criteria
        """
        results = []
        for obj in self._objects.values():
            if obj.object_type != object_type:
                continue
            if subtype and obj.subtype != subtype:
                continue
            if not include_collected and obj.status in ("collected", "destroyed"):
                continue
            results.append(obj)
        return results

    def query_semantic(
        self,
        query: str,
        limit: int = 5,
        include_collected: bool = False,
    ) -> list[SpatialQueryResult]:
        """
        Semantic search for objects.

        Args:
            query: Natural language query (e.g., "food to collect", "dangerous areas")
            limit: Maximum results to return
            include_collected: Include collected/destroyed objects

        Returns:
            List of SpatialQueryResult sorted by relevance
        """
        if not self._semantic_memory:
            logger.warning("Semantic search not available")
            return []

        # Query semantic memory
        raw_results = self._semantic_memory.query(
            query_text=query,
            k=limit * 2,
            threshold=self._similarity_threshold,  # Over-fetch for filtering
        )

        results = []
        for raw in raw_results:
            name = raw.get("metadata", {}).get("name")
            obj = self._objects.get(name) if name else None
            if not obj:
                continue

            if not include_collected and obj.status in ("collected", "destroyed"):
                continue

            staleness = self._current_tick - obj.last_seen_tick
            results.append(
                SpatialQueryResult(
                    obj=obj,
                    distance=0.0,  # Not a spatial query
                    score=raw.get("score", 0.0),
                    staleness=staleness,
                )
            )

        return results[:limit]

    def get_object(self, name: str) -> "WorldObject | None":
        """Get a specific object by name."""
        return self._objects.get(name)

    def get_all_objects(self, include_collected: bool = False) -> list["WorldObject"]:
        """Get all known objects."""
        if include_collected:
            return list(self._objects.values())
        return [
            obj for obj in self._objects.values() if obj.status not in ("collected", "destroyed")
        ]

    def get_resources(self, include_collected: bool = False) -> list["WorldObject"]:
        """Get all known resources."""
        return self.query_by_type("resource", include_collected=include_collected)

    def get_hazards(self) -> list["WorldObject"]:
        """Get all known hazards."""
        return self.query_by_type("hazard", include_collected=True)

    def retrieve(self, query: str | None = None, limit: int | None = None) -> list["Observation"]:
        """
        Retrieve from memory (AgentMemory interface).

        For SpatialMemory, this returns synthetic observations built from
        remembered objects. Use query_near_position or query_semantic for
        more specific spatial queries.
        """
        # Not directly applicable - spatial memory stores objects, not observations
        # Return empty list; users should use specific query methods
        return []

    def summarize(self) -> str:
        """
        Create a text summary of the world map.

        Returns:
            String description of known objects
        """
        resources = self.get_resources()
        hazards = self.get_hazards()

        parts = [f"World Map: {len(self._objects)} objects known"]

        if resources:
            resource_summary = ", ".join(
                f"{r.name} ({r.subtype}) at {r.position}" for r in resources[:5]
            )
            more = f" (+{len(resources)-5} more)" if len(resources) > 5 else ""
            parts.append(f"\nResources: {resource_summary}{more}")

        if hazards:
            hazard_summary = ", ".join(
                f"{h.name} ({h.subtype}, dmg:{h.damage}) at {h.position}" for h in hazards[:3]
            )
            more = f" (+{len(hazards)-3} more)" if len(hazards) > 3 else ""
            parts.append(f"\nHazards: {hazard_summary}{more}")

        # Find stale objects
        stale = [
            obj
            for obj in self._objects.values()
            if self._current_tick - obj.last_seen_tick > self._stale_threshold
        ]
        if stale:
            parts.append(
                f"\nStale objects (not seen in >{self._stale_threshold} ticks): {len(stale)}"
            )

        return "".join(parts)

    # Experience tracking methods

    def record_experience(self, event: "ExperienceEvent") -> None:
        """Record a significant experience.

        Stores the experience and, for collisions, also marks the
        collision location as an obstacle in the world map.

        Args:
            event: The experience event to record
        """
        from ..schemas import WorldObject

        self._experiences.append(event)
        if len(self._experiences) > self._max_experiences:
            self._experiences.pop(0)

        # Also mark collision locations as obstacles
        if event.event_type == "collision" and event.object_name:
            self._store_or_update(
                WorldObject(
                    name=event.object_name,
                    object_type="obstacle",
                    subtype="collision",
                    position=event.position,
                    last_seen_tick=event.tick,
                )
            )

        logger.debug(
            f"Recorded experience: {event.event_type} at tick {event.tick} "
            f"({len(self._experiences)} total)"
        )

    def get_recent_experiences(self, limit: int = 10) -> list["ExperienceEvent"]:
        """Get recent experiences for LLM context.

        Args:
            limit: Maximum number of experiences to return

        Returns:
            List of most recent experiences (newest last)
        """
        return self._experiences[-limit:]

    def clear_experiences(self) -> None:
        """Clear experience history (call on episode start)."""
        self._experiences.clear()
        logger.debug("Cleared experience history")

    def clear(self) -> None:
        """Clear all stored objects and experiences."""
        self._objects.clear()
        self._spatial_grid.clear()
        self._experiences.clear()
        if self._semantic_memory:
            self._semantic_memory.clear()
        logger.info("Cleared spatial memory")

    def dump(self) -> dict:
        """
        Dump full spatial memory state for inspection/debugging.

        Returns:
            Dictionary containing complete memory state
        """
        all_objects = list(self._objects.values())
        active_objects = [o for o in all_objects if o.status == "active"]
        collected_objects = [o for o in all_objects if o.status == "collected"]

        return {
            "type": "SpatialMemory",
            "stats": {
                "total_objects": len(all_objects),
                "active_objects": len(active_objects),
                "collected_objects": len(collected_objects),
                "experience_count": len(self._experiences),
                "current_tick": self._current_tick,
            },
            "objects": [obj.to_dict() for obj in all_objects],
            "objects_by_type": {
                "resources": [o.to_dict() for o in self.get_resources(include_collected=True)],
                "hazards": [o.to_dict() for o in self.get_hazards()],
                "obstacles": [o.to_dict() for o in self.query_by_type("obstacle")],
            },
            "experiences": [exp.to_dict() for exp in self._experiences],
            "grid_stats": {
                "cell_size": self._grid_size,
                "occupied_cells": len(self._spatial_grid),
            },
        }

    def __len__(self) -> int:
        """Return number of known objects."""
        return len(self._objects)

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"SpatialMemory(objects={len(self._objects)}, "
            f"resources={len(self.get_resources())}, "
            f"hazards={len(self.get_hazards())})"
        )
