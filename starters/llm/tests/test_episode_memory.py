"""
Unit tests for EpisodeMemoryManager.

Tests episode lifecycle detection, key event storage, memory retrieval,
deduplication, memory cap enforcement, persistence, and prompt integration.
"""

import math
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add starters/llm/ to path so we can import episode_memory
sys.path.insert(0, str(Path(__file__).parent.parent))
# Add python/ to path for long_term_memory_module
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "python"))

from agent_arena_sdk.schemas.observation import (
    Observation,
    ResourceInfo,
    HazardInfo,
    ItemInfo,
)
from episode_memory import EpisodeMemoryManager


# ------------------------------------------------------------------ #
#  Test Helpers
# ------------------------------------------------------------------ #


def make_obs(
    tick: int = 1,
    position: tuple = (0.0, 0.0, 0.0),
    health: float = 100.0,
    energy: float = 100.0,
    resources: list[ResourceInfo] | None = None,
    hazards: list[HazardInfo] | None = None,
    inventory: list[ItemInfo] | None = None,
    agent_id: str = "test_agent",
) -> Observation:
    """Create a mock Observation for testing."""
    return Observation(
        agent_id=agent_id,
        tick=tick,
        position=position,
        health=health,
        energy=energy,
        nearby_resources=resources or [],
        nearby_hazards=hazards or [],
        inventory=inventory or [],
    )


def make_resource(
    name: str = "berry_001",
    rtype: str = "food",
    position: tuple = (5.0, 0.0, 5.0),
    distance: float = 3.0,
) -> ResourceInfo:
    """Create a mock ResourceInfo."""
    return ResourceInfo(name=name, type=rtype, position=position, distance=distance)


def make_hazard(
    name: str = "fire_001",
    htype: str = "fire",
    position: tuple = (2.0, 0.0, 2.0),
    distance: float = 2.5,
    damage: float = 10.0,
) -> HazardInfo:
    """Create a mock HazardInfo."""
    return HazardInfo(name=name, type=htype, position=position, distance=distance, damage=damage)


def make_item(
    item_id: str = "inv_1",
    name: str = "berry",
    quantity: int = 1,
) -> ItemInfo:
    """Create a mock ItemInfo."""
    return ItemInfo(id=item_id, name=name, quantity=quantity)


@pytest.fixture
def tmp_memory_dir():
    """Create a temporary directory for memory persistence."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def manager(tmp_memory_dir):
    """Create an EpisodeMemoryManager with temporary persistence."""
    return EpisodeMemoryManager(persist_dir=tmp_memory_dir)


# ------------------------------------------------------------------ #
#  Episode Boundary Detection
# ------------------------------------------------------------------ #


class TestEpisodeBoundaryDetection:
    def test_first_tick_not_boundary(self, manager):
        """First tick should not trigger an episode boundary."""
        obs = make_obs(tick=1)
        assert manager.check_episode_boundary(obs) is False

    def test_monotonic_ticks_no_boundary(self, manager):
        """Monotonically increasing ticks should not trigger boundaries."""
        for tick in range(1, 10):
            obs = make_obs(tick=tick)
            assert manager.check_episode_boundary(obs) is False

    def test_tick_reset_triggers_boundary(self, manager):
        """Tick dropping below previous tick should trigger boundary."""
        manager.check_episode_boundary(make_obs(tick=50))
        manager.check_episode_boundary(make_obs(tick=100))
        assert manager.check_episode_boundary(make_obs(tick=1)) is True

    def test_boundary_increments_episode_on_start(self, manager):
        """on_episode_start should increment episode_number."""
        assert manager.episode_number == 0
        manager.on_episode_start(make_obs(tick=1))
        assert manager.episode_number == 1
        manager.on_episode_start(make_obs(tick=1))
        assert manager.episode_number == 2

    def test_episode_start_resets_counters(self, manager):
        """on_episode_start should reset all per-episode counters."""
        manager.on_episode_start(make_obs(tick=1))
        manager._episode_resources_collected = 10
        manager._episode_total_damage = 50.0
        manager._episode_hazard_types_seen = {"fire", "water"}

        manager.on_episode_start(make_obs(tick=1, health=90.0))
        assert manager._episode_resources_collected == 0
        assert manager._episode_total_damage == 0.0
        assert manager._episode_hazard_types_seen == set()


# ------------------------------------------------------------------ #
#  Key Event Detection
# ------------------------------------------------------------------ #


class TestKeyEventDetection:
    def test_new_hazard_type_stored(self, manager):
        """First encounter with a hazard type should store a memory."""
        manager.on_episode_start(make_obs(tick=1))
        hazard = make_hazard(name="fire_001", htype="fire")
        obs = make_obs(tick=2, hazards=[hazard])

        events = manager.check_key_events(obs)

        assert len(events) == 1
        assert "fire" in events[0]
        assert manager.memory_count >= 1

    def test_duplicate_hazard_type_not_stored_again(self, manager):
        """Second encounter with same hazard type should not store another memory."""
        manager.on_episode_start(make_obs(tick=1))
        hazard1 = make_hazard(name="fire_001", htype="fire")
        hazard2 = make_hazard(name="fire_002", htype="fire", position=(10.0, 0.0, 10.0))

        manager.check_key_events(make_obs(tick=2, hazards=[hazard1]))
        count_after_first = manager.memory_count

        events = manager.check_key_events(make_obs(tick=3, hazards=[hazard2]))
        # No new event for same type
        assert len(events) == 0
        assert manager.memory_count == count_after_first

    def test_different_hazard_types_both_stored(self, manager):
        """Different hazard types should each be stored."""
        manager.on_episode_start(make_obs(tick=1))
        fire = make_hazard(name="fire_001", htype="fire")
        water = make_hazard(name="water_001", htype="water", position=(10.0, 0.0, 10.0))

        events1 = manager.check_key_events(make_obs(tick=2, hazards=[fire]))
        events2 = manager.check_key_events(make_obs(tick=3, hazards=[water]))

        assert len(events1) == 1
        assert len(events2) == 1
        assert manager.memory_count >= 2

    def test_resource_cluster_detected(self, manager):
        """3+ resources within radius should trigger cluster storage."""
        manager.on_episode_start(make_obs(tick=1))
        resources = [
            make_resource("r1", "food", (5.0, 0.0, 5.0), 3.0),
            make_resource("r2", "food", (6.0, 0.0, 5.0), 3.5),
            make_resource("r3", "food", (5.5, 0.0, 6.0), 4.0),
        ]
        obs = make_obs(tick=2, resources=resources)

        events = manager.check_key_events(obs)

        assert len(events) >= 1
        assert any("cluster" in e.lower() for e in events)

    def test_sparse_resources_no_cluster(self, manager):
        """Resources far apart should not trigger cluster detection."""
        manager.on_episode_start(make_obs(tick=1))
        resources = [
            make_resource("r1", "food", (0.0, 0.0, 0.0), 3.0),
            make_resource("r2", "food", (50.0, 0.0, 50.0), 30.0),
            make_resource("r3", "food", (100.0, 0.0, 100.0), 60.0),
        ]
        obs = make_obs(tick=2, resources=resources)

        events = manager.check_key_events(obs)

        assert not any("cluster" in e.lower() for e in events)

    def test_significant_damage_stored(self, manager):
        """Damage > threshold should store a memory."""
        manager.on_episode_start(make_obs(tick=1, health=100.0))
        # First tick sets prev_health
        manager.check_key_events(make_obs(tick=1, health=100.0))
        # Second tick with big drop
        events = manager.check_key_events(make_obs(tick=2, health=70.0))

        assert len(events) >= 1
        assert any("damage" in e.lower() for e in events)

    def test_minor_damage_not_stored(self, manager):
        """Damage <= threshold should not store a memory."""
        manager.on_episode_start(make_obs(tick=1, health=100.0))
        manager.check_key_events(make_obs(tick=1, health=100.0))
        events = manager.check_key_events(make_obs(tick=2, health=95.0))

        # 5 HP drop < 20 threshold — no damage event
        assert not any("damage" in e.lower() for e in events)

    def test_inventory_increase_tracked(self, manager):
        """Resource collection should be tracked via inventory changes."""
        manager.on_episode_start(make_obs(tick=1))
        manager.check_key_events(make_obs(tick=1, inventory=[]))
        manager.check_key_events(
            make_obs(tick=2, inventory=[make_item("i1", "berry", 3)])
        )

        assert manager._episode_resources_collected == 3


# ------------------------------------------------------------------ #
#  Episode Summary
# ------------------------------------------------------------------ #


class TestEpisodeSummary:
    def test_episode_end_stores_summary(self, manager):
        """on_episode_end should store an episode summary memory."""
        manager.on_episode_start(make_obs(tick=1))
        manager._episode_max_tick = 100
        manager._episode_resources_collected = 5
        manager._episode_total_damage = 20.0

        last_obs = make_obs(tick=100, health=80.0)
        manager.on_episode_end(last_obs)

        assert manager.memory_count >= 1
        all_mems = manager.ltm.get_all_memories()
        summaries = [m for m in all_mems if m["metadata"].get("type") == "episode_summary"]
        assert len(summaries) >= 1
        assert "Episode 1" in summaries[0]["text"]

    def test_heavy_damage_produces_strategy_learning(self, manager):
        """Episode with heavy damage should produce a strategy learning."""
        manager.on_episode_start(make_obs(tick=1))
        manager._episode_total_damage = 60.0
        manager._episode_max_tick = 50

        manager.on_episode_end(make_obs(tick=50, health=40.0))

        all_mems = manager.ltm.get_all_memories()
        learnings = [m for m in all_mems if m["metadata"].get("type") == "learning"]
        strategy = [l for l in learnings if l["metadata"].get("category") == "strategy"]
        assert len(strategy) >= 1
        assert "cautious" in strategy[0]["text"].lower() or "damage" in strategy[0]["text"].lower()

    def test_death_produces_survival_learning(self, manager):
        """Death (health=0) should produce a survival learning."""
        manager.on_episode_start(make_obs(tick=1))
        manager._episode_max_tick = 30

        manager.on_episode_end(make_obs(tick=30, health=0.0))

        all_mems = manager.ltm.get_all_memories()
        learnings = [m for m in all_mems if m["metadata"].get("type") == "learning"]
        survival = [l for l in learnings if l["metadata"].get("category") == "survival"]
        assert len(survival) >= 1
        assert "died" in survival[0]["text"].lower() or "survival" in survival[0]["text"].lower()

    def test_productive_episode_produces_learning(self, manager):
        """Episode with many resources collected should produce a learning."""
        manager.on_episode_start(make_obs(tick=1))
        manager._episode_resources_collected = 10
        manager._episode_max_tick = 80

        manager.on_episode_end(make_obs(tick=80, health=90.0))

        all_mems = manager.ltm.get_all_memories()
        learnings = [m for m in all_mems if m["metadata"].get("type") == "learning"]
        strategy = [l for l in learnings if "productive" in l["text"].lower()]
        assert len(strategy) >= 1


# ------------------------------------------------------------------ #
#  Memory Retrieval
# ------------------------------------------------------------------ #


class TestMemoryRetrieval:
    def test_query_empty_memory(self, manager):
        """Querying empty memory should return empty list."""
        obs = make_obs(tick=1)
        results = manager.query_relevant_memories(obs)
        assert results == []

    def test_query_returns_relevant_memories(self, manager):
        """Stored hazard memory should be retrievable with related query."""
        manager.on_episode_start(make_obs(tick=1))
        # Store a hazard memory
        manager.ltm.store_memory(
            "Discovered fire hazard at position [5.0, 0.0, 3.0], very dangerous",
            {"type": "hazard_discovery", "episode": 1},
        )

        # Query with observation near that area with hazards
        obs = make_obs(
            tick=10,
            position=(4.0, 0.0, 2.0),
            hazards=[make_hazard("fire_002", "fire", (5.0, 0.0, 3.0), 1.5)],
        )
        results = manager.query_relevant_memories(obs)

        assert len(results) >= 1
        assert "fire" in results[0]["text"].lower()

    def test_query_caching(self, manager):
        """Same tick should return cached results without re-querying."""
        # Store a memory that will match the query (agent near hazards)
        manager.ltm.store_memory(
            "Agent at position [0.0, 0.0, 0.0]. health=100 energy=100. nearby hazards: fire",
            {"episode": 1},
        )
        obs = make_obs(
            tick=5,
            hazards=[make_hazard("fire_001", "fire", (2.0, 0.0, 2.0), 2.5)],
        )

        # Lower threshold to ensure we get results
        original_threshold = manager.QUERY_SIMILARITY_THRESHOLD
        manager.QUERY_SIMILARITY_THRESHOLD = 0.0

        results1 = manager.query_relevant_memories(obs)
        assert len(results1) >= 1, "Expected at least one result for cache test"

        results2 = manager.query_relevant_memories(obs)

        # Should be the exact same list object (cached)
        assert results1 is results2

        manager.QUERY_SIMILARITY_THRESHOLD = original_threshold

    def test_cache_invalidated_after_n_ticks(self, manager):
        """Cache should refresh after QUERY_EVERY_N_TICKS."""
        manager.ltm.store_memory("test memory", {"episode": 1})

        obs1 = make_obs(tick=1)
        results1 = manager.query_relevant_memories(obs1)

        # Advance past cache window
        obs2 = make_obs(tick=1 + manager.QUERY_EVERY_N_TICKS)
        results2 = manager.query_relevant_memories(obs2)

        # Should be a different list object (re-queried)
        assert results1 is not results2

    def test_format_memories_empty(self, manager):
        """Formatting empty memories should return default message."""
        text = manager.format_memories_for_prompt([])
        assert "No relevant past experiences" in text

    def test_format_memories_with_results(self, manager):
        """Formatting memories should produce numbered, readable output."""
        memories = [
            {"text": "Found berries near forest", "score": 0.85, "metadata": {"episode": 2}},
            {"text": "Fire hazard at north end", "score": 0.72, "metadata": {"episode": 1}},
        ]
        text = manager.format_memories_for_prompt(memories)

        assert "1." in text
        assert "2." in text
        assert "Ep.2" in text
        assert "Ep.1" in text
        assert "0.85" in text
        assert "berries" in text


# ------------------------------------------------------------------ #
#  Memory Hygiene
# ------------------------------------------------------------------ #


class TestMemoryHygiene:
    def test_dedup_prevents_duplicate_storage(self, manager):
        """Near-identical memories should not be stored twice."""
        manager.on_episode_start(make_obs(tick=1))
        text = "Found a large cluster of berries near the eastern forest edge"

        id1 = manager._store_if_novel(text, {"episode": 1})
        id2 = manager._store_if_novel(text, {"episode": 1})  # Exact same text

        assert id1 is not None
        assert id2 is None  # Should be deduplicated
        assert manager.memory_count == 1

    def test_different_memories_both_stored(self, manager):
        """Clearly different memories should both be stored."""
        id1 = manager._store_if_novel(
            "Fire hazard discovered at the northern mountain pass",
            {"episode": 1},
        )
        id2 = manager._store_if_novel(
            "Found a cluster of 5 wood resources near the river",
            {"episode": 1},
        )

        assert id1 is not None
        assert id2 is not None
        assert manager.memory_count == 2

    def test_memory_cap_enforced(self, manager):
        """Storing more than MAX_MEMORIES should trigger cap enforcement."""
        manager.MAX_MEMORIES = 10  # Lower cap for testing

        for i in range(15):
            # Use very different texts to avoid dedup
            manager.ltm.store_memory(
                f"Unique memory number {i} about topic {i * 7} in area {i * 13}",
                {"episode": i, "type": "test"},
            )

        manager._enforce_memory_cap()
        assert manager.memory_count == 10

    def test_oldest_memories_removed_first(self, manager):
        """Cap enforcement should remove memories from earliest episodes first."""
        manager.MAX_MEMORIES = 5

        for i in range(8):
            manager.ltm.store_memory(
                f"Memory from episode {i} with unique content {i * 17}",
                {"episode": i, "type": "test"},
            )

        manager._enforce_memory_cap()

        remaining = manager.ltm.get_all_memories()
        episodes = [m["metadata"]["episode"] for m in remaining]
        # Oldest episodes (0, 1, 2) should have been removed
        assert 0 not in episodes
        assert 1 not in episodes
        assert 2 not in episodes


# ------------------------------------------------------------------ #
#  Persistence
# ------------------------------------------------------------------ #


class TestPersistence:
    def test_save_and_load_roundtrip(self, tmp_memory_dir):
        """Memories should survive save/load cycle."""
        manager1 = EpisodeMemoryManager(persist_dir=tmp_memory_dir)
        manager1.ltm.store_memory(
            "Important discovery: berries grow near water",
            {"episode": 1, "type": "learning"},
        )
        manager1.save()

        # Create new manager pointing to same dir
        manager2 = EpisodeMemoryManager(persist_dir=tmp_memory_dir)
        assert manager2.memory_count == 1

        all_mems = manager2.ltm.get_all_memories()
        assert "berries" in all_mems[0]["text"]

    def test_load_nonexistent_is_graceful(self, tmp_memory_dir):
        """Loading from empty directory should not crash."""
        # tmp_memory_dir is empty, no .index/.metadata files
        manager = EpisodeMemoryManager(persist_dir=tmp_memory_dir)
        assert manager.memory_count == 0

    def test_persistence_files_created(self, tmp_memory_dir):
        """Save should create .index and .metadata files."""
        manager = EpisodeMemoryManager(persist_dir=tmp_memory_dir)
        manager.ltm.store_memory("test", {"episode": 1})
        manager.save()

        persist_path = Path(tmp_memory_dir) / "agent_ltm.faiss"
        assert persist_path.with_suffix(".index").exists()
        assert persist_path.with_suffix(".metadata").exists()


# ------------------------------------------------------------------ #
#  Prompt Integration
# ------------------------------------------------------------------ #


class TestPromptIntegration:
    def test_decision_template_has_memories_section_placeholder(self):
        """decision.txt should contain {memories_section} placeholder."""
        template_path = Path(__file__).parent.parent / "prompts" / "decision.txt"
        content = template_path.read_text()
        assert "{memories_section}" in content

    def test_memory_addendum_defined_in_agent(self):
        """Agent source should define the LONG-TERM MEMORY system prompt addendum."""
        agent_path = Path(__file__).parent.parent / "agent.py"
        content = agent_path.read_text()
        assert "LONG-TERM MEMORY" in content
        assert "_memory_system_addendum" in content

    def test_situation_query_construction(self, manager):
        """Situation query should include position, health, and entity types."""
        obs = make_obs(
            tick=5,
            position=(10.0, 0.0, -5.0),
            health=45.0,
            energy=80.0,
            resources=[make_resource("b1", "food")],
            hazards=[make_hazard("f1", "fire")],
        )
        query = manager._build_situation_query(obs)

        assert "10.0" in query
        assert "-5.0" in query
        assert "45" in query
        assert "food" in query
        assert "fire" in query
        assert "low health" in query
