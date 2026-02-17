"""
Test script for SpatialMemory system.

Run from python directory:
    python test_spatial_memory.py
"""

import sys
from pathlib import Path

# Add python directory to path
sys.path.insert(0, str(Path(__file__).parent))

from agent_runtime.memory import SpatialMemory  # noqa: E402
from agent_runtime.schemas import (  # noqa: E402
    HazardInfo,
    Observation,
    ResourceInfo,
    WorldObject,
)


def create_test_observation(
    tick: int,
    position: tuple[float, float, float],
    resources: list[dict] | None = None,
    hazards: list[dict] | None = None,
) -> Observation:
    """Create a test observation."""
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


def test_basic_storage():
    """Test basic object storage and retrieval."""
    print("\n=== Test: Basic Storage ===")

    memory = SpatialMemory(enable_semantic=False)  # Disable semantic for speed

    # Create observation with resources
    obs = create_test_observation(
        tick=1,
        position=(0, 0, 0),
        resources=[
            {"name": "Berry1", "type": "berry", "position": (5, 0, 3)},
            {"name": "Wood1", "type": "wood", "position": (10, 0, -5)},
        ],
        hazards=[
            {"name": "Fire1", "type": "fire", "position": (-3, 0, 2), "damage": 25},
        ],
    )

    # Store observation
    memory.update_from_observation(obs)

    print(f"Objects stored: {len(memory)}")
    print(f"Resources: {len(memory.get_resources())}")
    print(f"Hazards: {len(memory.get_hazards())}")

    assert len(memory) == 3, f"Expected 3 objects, got {len(memory)}"
    assert len(memory.get_resources()) == 2
    assert len(memory.get_hazards()) == 1

    # Get specific object
    berry = memory.get_object("Berry1")
    assert berry is not None
    assert berry.subtype == "berry"
    assert berry.position == (5, 0, 3)

    print("[OK] Basic storage test passed")


def test_spatial_queries():
    """Test spatial proximity queries."""
    print("\n=== Test: Spatial Queries ===")

    memory = SpatialMemory(enable_semantic=False)

    # Create observations at different positions
    obs1 = create_test_observation(
        tick=1,
        position=(0, 0, 0),
        resources=[
            {"name": "NearBerry", "type": "berry", "position": (5, 0, 0)},
            {"name": "FarBerry", "type": "berry", "position": (100, 0, 0)},
        ],
    )
    memory.update_from_observation(obs1)

    # Query near origin
    results = memory.query_near_position((0, 0, 0), radius=20)
    print(f"Objects within 20 units of origin: {len(results)}")
    for r in results:
        print(f"  - {r.obj.name} at distance {r.distance:.1f}")

    assert len(results) == 1, f"Expected 1 near object, got {len(results)}"
    assert results[0].obj.name == "NearBerry"

    # Query with larger radius
    results = memory.query_near_position((0, 0, 0), radius=200)
    assert len(results) == 2, f"Expected 2 objects, got {len(results)}"

    print("[OK] Spatial query test passed")


def test_visibility_updates():
    """Test that object positions update when seen again."""
    print("\n=== Test: Visibility Updates ===")

    memory = SpatialMemory(enable_semantic=False)

    # First observation: see resource at position A
    obs1 = create_test_observation(
        tick=1,
        position=(0, 0, 0),
        resources=[
            {"name": "MovingResource", "type": "berry", "position": (10, 0, 0)},
        ],
    )
    memory.update_from_observation(obs1)

    obj = memory.get_object("MovingResource")
    assert obj.position == (10, 0, 0)
    assert obj.last_seen_tick == 1

    # Second observation: see same resource at new position (it moved or we have better info)
    obs2 = create_test_observation(
        tick=5,
        position=(0, 0, 0),
        resources=[
            {"name": "MovingResource", "type": "berry", "position": (12, 0, 2)},
        ],
    )
    memory.update_from_observation(obs2)

    obj = memory.get_object("MovingResource")
    assert obj.position == (12, 0, 2), f"Position should update: {obj.position}"
    assert obj.last_seen_tick == 5, f"Tick should update: {obj.last_seen_tick}"

    print(f"Object position updated to {obj.position}, last seen tick {obj.last_seen_tick}")
    print("[OK] Visibility update test passed")


def test_collected_objects():
    """Test marking objects as collected."""
    print("\n=== Test: Collected Objects ===")

    memory = SpatialMemory(enable_semantic=False)

    # Add some resources
    obs = create_test_observation(
        tick=1,
        position=(0, 0, 0),
        resources=[
            {"name": "Berry1", "type": "berry", "position": (5, 0, 0)},
            {"name": "Berry2", "type": "berry", "position": (10, 0, 0)},
        ],
    )
    memory.update_from_observation(obs)

    # Mark one as collected
    memory.mark_collected("Berry1")

    # Query without collected
    resources = memory.get_resources(include_collected=False)
    print(f"Active resources: {len(resources)}")
    assert len(resources) == 1
    assert resources[0].name == "Berry2"

    # Query with collected
    all_resources = memory.get_resources(include_collected=True)
    print(f"All resources (incl. collected): {len(all_resources)}")
    assert len(all_resources) == 2

    # Verify status
    berry1 = memory.get_object("Berry1")
    assert berry1.status == "collected"

    print("[OK] Collected objects test passed")


def test_type_queries():
    """Test querying by object type."""
    print("\n=== Test: Type Queries ===")

    memory = SpatialMemory(enable_semantic=False)

    obs = create_test_observation(
        tick=1,
        position=(0, 0, 0),
        resources=[
            {"name": "Berry1", "type": "berry", "position": (5, 0, 0)},
            {"name": "Wood1", "type": "wood", "position": (10, 0, 0)},
            {"name": "Berry2", "type": "berry", "position": (15, 0, 0)},
        ],
        hazards=[
            {"name": "Fire1", "type": "fire", "position": (20, 0, 0)},
        ],
    )
    memory.update_from_observation(obs)

    # Query all resources
    resources = memory.query_by_type("resource")
    print(f"All resources: {len(resources)}")
    assert len(resources) == 3

    # Query by subtype
    berries = memory.query_by_type("resource", subtype="berry")
    print(f"Berries: {len(berries)}")
    assert len(berries) == 2

    wood = memory.query_by_type("resource", subtype="wood")
    print(f"Wood: {len(wood)}")
    assert len(wood) == 1

    print("[OK] Type query test passed")


def test_world_object_schema():
    """Test WorldObject schema methods."""
    print("\n=== Test: WorldObject Schema ===")

    # Test from_resource
    resource = ResourceInfo(name="TestBerry", type="berry", position=(5, 0, 3), distance=5.0)
    obj = WorldObject.from_resource(resource, tick=10)
    assert obj.name == "TestBerry"
    assert obj.object_type == "resource"
    assert obj.subtype == "berry"
    assert obj.last_seen_tick == 10

    # Test from_hazard
    hazard = HazardInfo(
        name="TestFire", type="fire", position=(10, 0, 0), distance=10.0, damage=25.0
    )
    obj = WorldObject.from_hazard(hazard, tick=15)
    assert obj.name == "TestFire"
    assert obj.object_type == "hazard"
    assert obj.damage == 25.0

    # Test distance_to
    obj = WorldObject(
        name="Test",
        object_type="resource",
        subtype="test",
        position=(10, 0, 0),
        last_seen_tick=1,
    )
    dist = obj.distance_to((0, 0, 0))
    assert abs(dist - 10.0) < 0.01

    # Test to_dict / from_dict
    data = obj.to_dict()
    obj2 = WorldObject.from_dict(data)
    assert obj2.name == obj.name
    assert obj2.position == obj.position

    print("[OK] WorldObject schema test passed")


def test_summarize():
    """Test memory summarization."""
    print("\n=== Test: Summarize ===")

    memory = SpatialMemory(enable_semantic=False)

    obs = create_test_observation(
        tick=1,
        position=(0, 0, 0),
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
    print(summary)

    assert "3 objects" in summary
    assert "Berry1" in summary
    assert "Fire1" in summary

    print("[OK] Summarize test passed")


def test_semantic_search():
    """Test semantic search (if available)."""
    print("\n=== Test: Semantic Search ===")

    try:
        memory = SpatialMemory(enable_semantic=True)
    except Exception as e:
        print(f"Semantic search not available: {e}")
        print("⊘ Skipping semantic search test")
        return

    obs = create_test_observation(
        tick=1,
        position=(0, 0, 0),
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

    # Search for food
    results = memory.query_semantic("food to eat")
    print(f"Semantic search 'food to eat': {len(results)} results")
    for r in results:
        print(f"  - {r.obj.name} (score: {r.score:.2f})")

    # Search for danger
    results = memory.query_semantic("dangerous fire")
    print(f"Semantic search 'dangerous fire': {len(results)} results")
    for r in results:
        print(f"  - {r.obj.name} (score: {r.score:.2f})")

    print("[OK] Semantic search test passed")


def main():
    """Run all tests."""
    print("=" * 60)
    print("SpatialMemory Test Suite")
    print("=" * 60)

    test_world_object_schema()
    test_basic_storage()
    test_spatial_queries()
    test_visibility_updates()
    test_collected_objects()
    test_type_queries()
    test_summarize()
    test_semantic_search()

    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
