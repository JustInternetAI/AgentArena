"""
Tests for SpatialMemory module (SDK version).

Migrated from python/archived/test_spatial_memory.py to use SDK schemas
and pytest format per issue #85.
"""

import sys
from pathlib import Path

import pytest

# Add python directory to path for SDK imports
sys.path.insert(0, str(Path(__file__).parent.parent / "python"))

from agent_arena_sdk.memory import SpatialMemory
from agent_arena_sdk.schemas import (
    ExperienceEvent,
    HazardInfo,
    Observation,
    ResourceInfo,
    WorldObject,
)


def _has_semantic_memory() -> bool:
    """Check if semantic memory is fully functional (not just importable)."""
    try:
        memory = SpatialMemory(enable_semantic=True)
        return memory._semantic_memory is not None
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def create_test_observation(
    tick: int,
    position: tuple[float, float, float] = (0, 0, 0),
    resources: list[dict] | None = None,
    hazards: list[dict] | None = None,
) -> Observation:
    """Create a test observation with optional resources and hazards."""
    nearby_resources = []
    if resources:
        for r in resources:
            nearby_resources.append(
                ResourceInfo(
                    name=r["name"],
                    type=r["type"],
                    position=r["position"],
                    distance=r.get("distance", 5.0),
                )
            )

    nearby_hazards = []
    if hazards:
        for h in hazards:
            nearby_hazards.append(
                HazardInfo(
                    name=h["name"],
                    type=h["type"],
                    position=h["position"],
                    distance=h.get("distance", 5.0),
                    damage=h.get("damage", 10.0),
                )
            )

    return Observation(
        agent_id="test_agent",
        tick=tick,
        position=position,
        nearby_resources=nearby_resources,
        nearby_hazards=nearby_hazards,
    )


# ---------------------------------------------------------------------------
# WorldObject schema tests
# ---------------------------------------------------------------------------


class TestWorldObject:
    """Test WorldObject schema methods."""

    def test_from_resource(self):
        resource = ResourceInfo(name="TestBerry", type="berry", position=(5, 0, 3), distance=5.0)
        obj = WorldObject.from_resource(resource, tick=10)
        assert obj.name == "TestBerry"
        assert obj.object_type == "resource"
        assert obj.subtype == "berry"
        assert obj.last_seen_tick == 10

    def test_from_hazard(self):
        hazard = HazardInfo(
            name="TestFire", type="fire", position=(10, 0, 0), distance=10.0, damage=25.0
        )
        obj = WorldObject.from_hazard(hazard, tick=15)
        assert obj.name == "TestFire"
        assert obj.object_type == "hazard"
        assert obj.damage == 25.0

    def test_distance_to(self):
        obj = WorldObject(
            name="Test",
            object_type="resource",
            subtype="test",
            position=(10, 0, 0),
            last_seen_tick=1,
        )
        dist = obj.distance_to((0, 0, 0))
        assert abs(dist - 10.0) < 0.01

    def test_distance_to_3d(self):
        obj = WorldObject(
            name="Test",
            object_type="resource",
            subtype="test",
            position=(3, 4, 0),
            last_seen_tick=1,
        )
        dist = obj.distance_to((0, 0, 0))
        assert abs(dist - 5.0) < 0.01

    def test_to_dict_from_dict(self):
        obj = WorldObject(
            name="Test",
            object_type="resource",
            subtype="test",
            position=(10, 0, 0),
            last_seen_tick=1,
        )
        data = obj.to_dict()
        obj2 = WorldObject.from_dict(data)
        assert obj2.name == obj.name
        assert obj2.position == obj.position
        assert obj2.object_type == obj.object_type

    def test_default_status(self):
        obj = WorldObject(
            name="Test",
            object_type="resource",
            subtype="test",
            position=(0, 0, 0),
            last_seen_tick=1,
        )
        assert obj.status == "active"
        assert obj.damage == 0.0
        assert obj.metadata == {}


# ---------------------------------------------------------------------------
# ExperienceEvent schema tests
# ---------------------------------------------------------------------------


class TestExperienceEvent:
    """Test ExperienceEvent schema methods."""

    def test_create(self):
        event = ExperienceEvent(
            tick=5,
            event_type="collision",
            description="Hit a wall",
            position=(10, 0, 5),
            object_name="wall1",
            damage_taken=10.0,
        )
        assert event.tick == 5
        assert event.event_type == "collision"
        assert event.object_name == "wall1"

    def test_to_dict_from_dict(self):
        event = ExperienceEvent(
            tick=5,
            event_type="damage",
            description="Burned by fire",
            position=(10, 0, 5),
            damage_taken=25.0,
        )
        data = event.to_dict()
        event2 = ExperienceEvent.from_dict(data)
        assert event2.tick == event.tick
        assert event2.event_type == event.event_type
        assert event2.damage_taken == event.damage_taken


# ---------------------------------------------------------------------------
# SpatialMemory core tests
# ---------------------------------------------------------------------------


class TestSpatialMemory:
    """Test core SpatialMemory functionality."""

    @pytest.fixture
    def memory(self):
        return SpatialMemory(enable_semantic=False)

    def test_basic_storage(self, memory):
        obs = create_test_observation(
            tick=1,
            resources=[
                {"name": "Berry1", "type": "berry", "position": (5, 0, 3)},
                {"name": "Wood1", "type": "wood", "position": (10, 0, -5)},
            ],
            hazards=[
                {"name": "Fire1", "type": "fire", "position": (-3, 0, 2), "damage": 25},
            ],
        )
        memory.update_from_observation(obs)

        assert len(memory) == 3
        assert len(memory.get_resources()) == 2
        assert len(memory.get_hazards()) == 1

    def test_get_object(self, memory):
        obs = create_test_observation(
            tick=1,
            resources=[{"name": "Berry1", "type": "berry", "position": (5, 0, 3)}],
        )
        memory.update_from_observation(obs)

        berry = memory.get_object("Berry1")
        assert berry is not None
        assert berry.subtype == "berry"
        assert berry.position == (5, 0, 3)

    def test_get_object_not_found(self, memory):
        assert memory.get_object("NonExistent") is None

    def test_visibility_updates(self, memory):
        """Test that object positions update when seen again."""
        obs1 = create_test_observation(
            tick=1,
            resources=[{"name": "MovingResource", "type": "berry", "position": (10, 0, 0)}],
        )
        memory.update_from_observation(obs1)

        obj = memory.get_object("MovingResource")
        assert obj.position == (10, 0, 0)
        assert obj.last_seen_tick == 1

        obs2 = create_test_observation(
            tick=5,
            resources=[{"name": "MovingResource", "type": "berry", "position": (12, 0, 2)}],
        )
        memory.update_from_observation(obs2)

        obj = memory.get_object("MovingResource")
        assert obj.position == (12, 0, 2)
        assert obj.last_seen_tick == 5

    def test_mark_collected(self, memory):
        obs = create_test_observation(
            tick=1,
            resources=[
                {"name": "Berry1", "type": "berry", "position": (5, 0, 0)},
                {"name": "Berry2", "type": "berry", "position": (10, 0, 0)},
            ],
        )
        memory.update_from_observation(obs)

        assert memory.mark_collected("Berry1") is True
        assert memory.get_object("Berry1").status == "collected"

        # Without collected
        resources = memory.get_resources(include_collected=False)
        assert len(resources) == 1
        assert resources[0].name == "Berry2"

        # With collected
        all_resources = memory.get_resources(include_collected=True)
        assert len(all_resources) == 2

    def test_mark_collected_nonexistent(self, memory):
        assert memory.mark_collected("NonExistent") is False

    def test_mark_destroyed(self, memory):
        obs = create_test_observation(
            tick=1,
            hazards=[{"name": "Fire1", "type": "fire", "position": (5, 0, 0), "damage": 25}],
        )
        memory.update_from_observation(obs)

        assert memory.mark_destroyed("Fire1") is True
        assert memory.get_object("Fire1").status == "destroyed"

    def test_collected_status_persists(self, memory):
        """Collected status should persist even when object is re-observed."""
        obs1 = create_test_observation(
            tick=1,
            resources=[{"name": "Berry1", "type": "berry", "position": (5, 0, 0)}],
        )
        memory.update_from_observation(obs1)
        memory.mark_collected("Berry1")

        # Re-observe at same position
        obs2 = create_test_observation(
            tick=5,
            resources=[{"name": "Berry1", "type": "berry", "position": (5, 0, 0)}],
        )
        memory.update_from_observation(obs2)

        assert memory.get_object("Berry1").status == "collected"

    def test_store_alias(self, memory):
        """store() should be an alias for update_from_observation()."""
        obs = create_test_observation(
            tick=1,
            resources=[{"name": "Berry1", "type": "berry", "position": (5, 0, 0)}],
        )
        memory.store(obs)
        assert len(memory) == 1

    def test_get_all_objects(self, memory):
        obs = create_test_observation(
            tick=1,
            resources=[{"name": "Berry1", "type": "berry", "position": (5, 0, 0)}],
            hazards=[{"name": "Fire1", "type": "fire", "position": (10, 0, 0)}],
        )
        memory.update_from_observation(obs)

        all_objs = memory.get_all_objects(include_collected=True)
        assert len(all_objs) == 2

        memory.mark_collected("Berry1")
        active_objs = memory.get_all_objects(include_collected=False)
        assert len(active_objs) == 1

    def test_clear(self, memory):
        obs = create_test_observation(
            tick=1,
            resources=[{"name": "Berry1", "type": "berry", "position": (5, 0, 0)}],
        )
        memory.update_from_observation(obs)
        assert len(memory) == 1

        memory.clear()
        assert len(memory) == 0

    def test_summarize(self, memory):
        obs = create_test_observation(
            tick=1,
            resources=[
                {"name": "Berry1", "type": "berry", "position": (5, 0, 0)},
                {"name": "Wood1", "type": "wood", "position": (10, 0, 0)},
            ],
            hazards=[
                {"name": "Fire1", "type": "fire", "position": (20, 0, 0), "damage": 25},
            ],
        )
        memory.update_from_observation(obs)

        summary = memory.summarize()
        assert "3 objects" in summary
        assert "Berry1" in summary
        assert "Fire1" in summary

    def test_dump(self, memory):
        obs = create_test_observation(
            tick=1,
            resources=[{"name": "Berry1", "type": "berry", "position": (5, 0, 0)}],
        )
        memory.update_from_observation(obs)

        dump = memory.dump()
        assert dump["type"] == "SpatialMemory"
        assert dump["stats"]["total_objects"] == 1
        assert len(dump["objects"]) == 1

    def test_repr(self, memory):
        repr_str = repr(memory)
        assert "SpatialMemory" in repr_str
        assert "objects=0" in repr_str

    def test_retrieve_returns_empty(self, memory):
        """retrieve() is not applicable for SpatialMemory."""
        assert memory.retrieve() == []


# ---------------------------------------------------------------------------
# Spatial query tests
# ---------------------------------------------------------------------------


class TestSpatialQueries:
    """Test spatial query methods."""

    @pytest.fixture
    def memory(self):
        return SpatialMemory(enable_semantic=False)

    def test_query_near_position(self, memory):
        obs = create_test_observation(
            tick=1,
            resources=[
                {"name": "NearBerry", "type": "berry", "position": (5, 0, 0)},
                {"name": "FarBerry", "type": "berry", "position": (100, 0, 0)},
            ],
        )
        memory.update_from_observation(obs)

        results = memory.query_near_position((0, 0, 0), radius=20)
        assert len(results) == 1
        assert results[0].obj.name == "NearBerry"

    def test_query_near_position_large_radius(self, memory):
        obs = create_test_observation(
            tick=1,
            resources=[
                {"name": "NearBerry", "type": "berry", "position": (5, 0, 0)},
                {"name": "FarBerry", "type": "berry", "position": (100, 0, 0)},
            ],
        )
        memory.update_from_observation(obs)

        results = memory.query_near_position((0, 0, 0), radius=200)
        assert len(results) == 2

    def test_query_sorted_by_distance(self, memory):
        obs = create_test_observation(
            tick=1,
            resources=[
                {"name": "Far", "type": "berry", "position": (30, 0, 0)},
                {"name": "Near", "type": "berry", "position": (5, 0, 0)},
                {"name": "Mid", "type": "berry", "position": (15, 0, 0)},
            ],
        )
        memory.update_from_observation(obs)

        results = memory.query_near_position((0, 0, 0), radius=50)
        assert [r.obj.name for r in results] == ["Near", "Mid", "Far"]

    def test_query_with_type_filter(self, memory):
        obs = create_test_observation(
            tick=1,
            resources=[{"name": "Berry1", "type": "berry", "position": (5, 0, 0)}],
            hazards=[{"name": "Fire1", "type": "fire", "position": (5, 0, 5)}],
        )
        memory.update_from_observation(obs)

        results = memory.query_near_position((0, 0, 0), radius=20, object_type="resource")
        assert len(results) == 1
        assert results[0].obj.name == "Berry1"

    def test_query_excludes_collected(self, memory):
        obs = create_test_observation(
            tick=1,
            resources=[
                {"name": "Berry1", "type": "berry", "position": (5, 0, 0)},
                {"name": "Berry2", "type": "berry", "position": (10, 0, 0)},
            ],
        )
        memory.update_from_observation(obs)
        memory.mark_collected("Berry1")

        results = memory.query_near_position((0, 0, 0), radius=20, include_collected=False)
        assert len(results) == 1
        assert results[0].obj.name == "Berry2"

    def test_query_by_type(self, memory):
        obs = create_test_observation(
            tick=1,
            resources=[
                {"name": "Berry1", "type": "berry", "position": (5, 0, 0)},
                {"name": "Wood1", "type": "wood", "position": (10, 0, 0)},
                {"name": "Berry2", "type": "berry", "position": (15, 0, 0)},
            ],
            hazards=[{"name": "Fire1", "type": "fire", "position": (20, 0, 0)}],
        )
        memory.update_from_observation(obs)

        resources = memory.query_by_type("resource")
        assert len(resources) == 3

        berries = memory.query_by_type("resource", subtype="berry")
        assert len(berries) == 2

        wood = memory.query_by_type("resource", subtype="wood")
        assert len(wood) == 1

    def test_query_stale_objects(self, memory):
        """Objects not seen recently can be excluded."""
        obs1 = create_test_observation(
            tick=1,
            resources=[{"name": "OldBerry", "type": "berry", "position": (5, 0, 0)}],
        )
        memory.update_from_observation(obs1)

        # Advance tick far enough to make object stale (default threshold=100)
        obs2 = create_test_observation(tick=200)
        memory.update_from_observation(obs2)

        results = memory.query_near_position((0, 0, 0), radius=20, include_stale=False)
        assert len(results) == 0

        results = memory.query_near_position((0, 0, 0), radius=20, include_stale=True)
        assert len(results) == 1


# ---------------------------------------------------------------------------
# Experience tracking tests
# ---------------------------------------------------------------------------


class TestExperienceTracking:
    """Test experience event tracking."""

    @pytest.fixture
    def memory(self):
        return SpatialMemory(enable_semantic=False)

    def test_record_experience(self, memory):
        event = ExperienceEvent(
            tick=5,
            event_type="collision",
            description="Hit a wall",
            position=(10, 0, 5),
            object_name="wall1",
        )
        memory.record_experience(event)

        experiences = memory.get_recent_experiences()
        assert len(experiences) == 1
        assert experiences[0].event_type == "collision"

    def test_collision_creates_obstacle(self, memory):
        """Collision events should create obstacle objects in the world map."""
        event = ExperienceEvent(
            tick=5,
            event_type="collision",
            description="Hit a wall",
            position=(10, 0, 5),
            object_name="wall1",
        )
        memory.record_experience(event)

        wall = memory.get_object("wall1")
        assert wall is not None
        assert wall.object_type == "obstacle"
        assert wall.subtype == "collision"

    def test_experience_limit(self, memory):
        """Should keep at most max_experiences entries."""
        for i in range(60):
            memory.record_experience(
                ExperienceEvent(
                    tick=i,
                    event_type="damage",
                    description=f"Damage {i}",
                    position=(0, 0, 0),
                )
            )

        experiences = memory.get_recent_experiences(limit=100)
        assert len(experiences) == 50  # Default max is 50

    def test_clear_experiences(self, memory):
        memory.record_experience(
            ExperienceEvent(
                tick=1,
                event_type="damage",
                description="Ouch",
                position=(0, 0, 0),
            )
        )
        assert len(memory.get_recent_experiences()) == 1

        memory.clear_experiences()
        assert len(memory.get_recent_experiences()) == 0

    def test_recent_experiences_limit(self, memory):
        for i in range(10):
            memory.record_experience(
                ExperienceEvent(
                    tick=i,
                    event_type="damage",
                    description=f"Damage {i}",
                    position=(0, 0, 0),
                )
            )

        recent = memory.get_recent_experiences(limit=3)
        assert len(recent) == 3
        assert recent[0].tick == 7  # Newest last


# ---------------------------------------------------------------------------
# Semantic search tests (optional)
# ---------------------------------------------------------------------------


class TestSemanticSearch:
    """Test optional semantic search functionality."""

    def test_semantic_query(self):
        # Use low threshold since we're testing functionality, not tuning
        memory = SpatialMemory(enable_semantic=True, similarity_threshold=0.05)

        if memory._semantic_memory is None:
            pytest.skip("Semantic memory not available (missing FAISS or sentence-transformers)")

        obs = create_test_observation(
            tick=1,
            resources=[
                {"name": "Berries", "type": "berry", "position": (5, 0, 0)},
                {"name": "WoodPile", "type": "wood", "position": (10, 0, 0)},
                {"name": "Apple", "type": "apple", "position": (15, 0, 0)},
            ],
            hazards=[
                {"name": "Campfire", "type": "fire", "position": (20, 0, 0), "damage": 25},
            ],
        )
        memory.update_from_observation(obs)

        results = memory.query_semantic("food to eat")
        assert len(results) > 0

    def test_semantic_disabled_returns_empty(self):
        memory = SpatialMemory(enable_semantic=False)

        obs = create_test_observation(
            tick=1,
            resources=[{"name": "Berry1", "type": "berry", "position": (5, 0, 0)}],
        )
        memory.update_from_observation(obs)

        results = memory.query_semantic("food")
        assert results == []


# ---------------------------------------------------------------------------
# SDK import path tests
# ---------------------------------------------------------------------------


class TestSDKImports:
    """Test that SDK import paths work correctly."""

    def test_import_from_memory_module(self):
        from agent_arena_sdk.memory import SpatialMemory as SM

        assert SM is not None

    def test_import_from_top_level(self):
        from agent_arena_sdk import SpatialMemory as SM

        assert SM is not None

    def test_import_schemas_from_top_level(self):
        from agent_arena_sdk import ExperienceEvent, SpatialQueryResult, WorldObject

        assert WorldObject is not None
        assert ExperienceEvent is not None
        assert SpatialQueryResult is not None

    def test_import_schemas_from_schemas_module(self):
        from agent_arena_sdk.schemas import ExperienceEvent, SpatialQueryResult, WorldObject

        assert WorldObject is not None
        assert ExperienceEvent is not None
        assert SpatialQueryResult is not None

    def test_no_agent_runtime_dependency(self):
        """SDK SpatialMemory should not import from agent_runtime."""
        import inspect

        from agent_arena_sdk.memory import spatial as spatial_module

        source = inspect.getsource(spatial_module)
        assert "agent_runtime" not in source
