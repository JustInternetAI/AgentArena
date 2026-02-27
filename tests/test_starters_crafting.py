"""
Tests for all starter templates with crafting scenario.

Simulates crafting-chain observations and verifies each starter
produces sensible decisions. The crafting scenario involves:
- Collecting raw materials (wood, stone, ore)
- Moving to crafting stations
- Crafting items from materials
- Multi-step recipe chains (e.g., ore -> ingot -> tool)

Since the crafting scenario is not yet fully implemented in the game,
these tests verify agents behave correctly with crafting-like observations
using the existing universal tool set (move_to, collect, idle).
"""

import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "starters" / "beginner"))
sys.path.insert(0, str(ROOT / "starters" / "intermediate"))
sys.path.insert(0, str(ROOT / "starters" / "llm"))
sys.path.insert(0, str(ROOT / "python"))

# Module names duplicated across starters that need isolation
_STARTER_MODULES = ("memory", "planner", "agent")


def _clear_starter_modules():
    """Remove cached starter modules so each starter imports its own copy."""
    for mod_name in list(sys.modules):
        if mod_name in _STARTER_MODULES or mod_name.startswith("starters."):
            del sys.modules[mod_name]

from agent_arena_sdk import (
    Decision,
    ExplorationInfo,
    ExploreTarget,
    HazardInfo,
    ItemInfo,
    MetricDefinition,
    Objective,
    Observation,
    ResourceInfo,
)


# ------------------------------------------------------------------ #
#  Crafting Scenario Definitions
# ------------------------------------------------------------------ #

CRAFTING_OBJECTIVE = Objective(
    description="Collect raw materials and craft items. Gather wood and stone, then craft tools.",
    success_metrics={
        "items_crafted": MetricDefinition(target=3.0, weight=1.0, required=True),
        "materials_collected": MetricDefinition(target=6.0, weight=0.5),
        "health_remaining": MetricDefinition(target=50.0, weight=0.3),
    },
    time_limit=400,
)

CRAFTING_EXPLORATION = ExplorationInfo(
    exploration_percentage=40.0,
    total_cells=100,
    seen_cells=40,
    frontiers_by_direction={"north": 12.0, "south": 18.0},
    explore_targets=[
        ExploreTarget(direction="north", distance=12.0, position=(0.0, 0.0, 12.0)),
        ExploreTarget(direction="south", distance=18.0, position=(0.0, 0.0, -18.0)),
    ],
)


def make_crafting_obs(
    tick: int = 1,
    position: tuple = (0.0, 0.0, 0.0),
    health: float = 100.0,
    energy: float = 100.0,
    resources: list[ResourceInfo] | None = None,
    hazards: list[HazardInfo] | None = None,
    inventory: list[ItemInfo] | None = None,
    exploration: ExplorationInfo | None = None,
    objective: Objective | None = None,
    progress: dict | None = None,
) -> Observation:
    """Create a crafting scenario observation."""
    return Observation(
        agent_id="crafting_agent_001",
        tick=tick,
        position=position,
        health=health,
        energy=energy,
        nearby_resources=resources or [],
        nearby_hazards=hazards or [],
        inventory=inventory or [],
        exploration=exploration,
        scenario_name="crafting_chain",
        objective=objective or CRAFTING_OBJECTIVE,
        current_progress=progress or {"items_crafted": 0.0, "materials_collected": 0.0, "health_remaining": 100.0},
    )


def make_raw_material(
    name: str = "wood_001",
    rtype: str = "material",
    position: tuple = (8.0, 0.0, 3.0),
    distance: float = 5.0,
) -> ResourceInfo:
    return ResourceInfo(name=name, type=rtype, position=position, distance=distance)


def make_crafting_station(
    name: str = "workbench_001",
    rtype: str = "station",
    position: tuple = (15.0, 0.0, 0.0),
    distance: float = 10.0,
) -> ResourceInfo:
    """Crafting stations appear as resources the agent can interact with."""
    return ResourceInfo(name=name, type=rtype, position=position, distance=distance)


def make_hazard(
    name: str = "lava_001",
    htype: str = "lava",
    position: tuple = (3.0, 0.0, 0.0),
    distance: float = 2.5,
    damage: float = 15.0,
) -> HazardInfo:
    return HazardInfo(name=name, type=htype, position=position, distance=distance, damage=damage)


def distance_between(pos1, pos2) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(pos1, pos2)))


def assert_valid_decision(decision: Decision):
    assert isinstance(decision, Decision)
    assert decision.tool in {"move_to", "collect", "idle"}
    assert isinstance(decision.params, dict)


# ------------------------------------------------------------------ #
#  Beginner Starter - Crafting Scenario
# ------------------------------------------------------------------ #


class TestBeginnerCrafting:
    """Test the beginner starter with crafting scenario observations."""

    @pytest.fixture
    def agent(self):
        from starters.beginner.agent import Agent

        return Agent()

    def test_collects_raw_materials(self, agent):
        """Agent should move toward raw materials when visible."""
        wood = make_raw_material("wood_001", "material", (8.0, 0.0, 3.0), 5.0)
        obs = make_crafting_obs(resources=[wood])

        decision = agent.decide(obs)

        assert_valid_decision(decision)
        assert decision.tool == "move_to"
        target = decision.params["target_position"]
        assert distance_between(target, wood.position) < 1.0

    def test_picks_closest_material(self, agent):
        """Agent should prefer the closest material."""
        far_wood = make_raw_material("wood_far", "material", (20.0, 0.0, 0.0), 20.0)
        close_stone = make_raw_material("stone_close", "material", (3.0, 0.0, 0.0), 3.0)
        obs = make_crafting_obs(resources=[far_wood, close_stone])

        decision = agent.decide(obs)

        assert_valid_decision(decision)
        assert decision.tool == "move_to"
        target = decision.params["target_position"]
        assert distance_between(target, close_stone.position) < distance_between(
            target, far_wood.position
        )

    def test_escapes_hazard_in_crafting_area(self, agent):
        """Agent should flee from hazards even in crafting scenario."""
        hazard = make_hazard("lava_001", "lava", (1.0, 0.0, 0.0), 1.5)
        obs = make_crafting_obs(hazards=[hazard])

        decision = agent.decide(obs)

        assert_valid_decision(decision)
        assert decision.tool == "move_to"
        target = decision.params["target_position"]
        assert distance_between(target, hazard.position) > hazard.distance

    def test_hazard_priority_over_materials(self, agent):
        """Agent should prioritize escaping hazards over collecting materials."""
        hazard = make_hazard("lava_001", "lava", (1.0, 0.0, 0.0), 1.5)
        wood = make_raw_material("wood_001", "material", (5.0, 0.0, 5.0), 5.0)
        obs = make_crafting_obs(hazards=[hazard], resources=[wood])

        decision = agent.decide(obs)

        assert_valid_decision(decision)
        assert decision.tool == "move_to"
        target = decision.params["target_position"]
        # Should move away from hazard
        assert distance_between(target, hazard.position) > hazard.distance

    def test_explores_for_materials(self, agent):
        """Agent should explore when no materials are visible."""
        obs = make_crafting_obs(exploration=CRAFTING_EXPLORATION)

        decision = agent.decide(obs)

        assert_valid_decision(decision)
        assert decision.tool in {"move_to", "idle"}

    def test_moves_to_crafting_station(self, agent):
        """Agent should move toward crafting stations (they appear as resources)."""
        station = make_crafting_station("workbench_001", "station", (10.0, 0.0, 0.0), 8.0)
        obs = make_crafting_obs(resources=[station])

        decision = agent.decide(obs)

        assert_valid_decision(decision)
        assert decision.tool == "move_to"
        target = decision.params["target_position"]
        assert distance_between(target, station.position) < 1.0


# ------------------------------------------------------------------ #
#  Intermediate Starter - Crafting Scenario
# ------------------------------------------------------------------ #


class TestIntermediateCrafting:
    """Test the intermediate starter with crafting scenario observations."""

    @pytest.fixture
    def agent(self):
        _clear_starter_modules()
        intermediate_dir = str(ROOT / "starters" / "intermediate")
        if intermediate_dir in sys.path:
            sys.path.remove(intermediate_dir)
        sys.path.insert(0, intermediate_dir)

        from starters.intermediate.agent import Agent

        return Agent()

    def test_collects_materials_with_memory(self, agent):
        """Agent should collect materials when materials_collected is the active goal."""
        wood = make_raw_material("wood_001", "material", (8.0, 0.0, 3.0), 5.0)
        # Set items_crafted as complete so materials_collected becomes the active goal
        obs = make_crafting_obs(
            tick=1,
            resources=[wood],
            progress={"items_crafted": 3.0, "materials_collected": 2.0, "health_remaining": 100.0},
        )

        decision = agent.decide(obs)

        assert_valid_decision(decision)
        assert decision.tool in {"move_to", "collect"}
        # Memory should have stored the observation
        assert agent.memory.count_observations() == 1

    def test_remembers_material_locations(self, agent):
        """Agent should remember where materials were seen."""
        # Tick 1: See wood
        wood = make_raw_material("wood_001", "material", (10.0, 0.0, 5.0), 7.0)
        obs1 = make_crafting_obs(tick=1, resources=[wood])
        agent.decide(obs1)

        # Tick 2: No resources visible
        obs2 = make_crafting_obs(tick=2, position=(5.0, 0.0, 0.0))
        agent.decide(obs2)

        # Memory should still know about wood
        resources = agent.memory.find_resources_seen()
        assert len(resources) >= 1
        assert any(name == "wood_001" for name, _, _ in resources)

    def test_plans_around_crafting_objective(self, agent):
        """Planner should create goals from crafting objective."""
        progress = {"items_crafted": 1.0, "materials_collected": 3.0, "health_remaining": 90.0}

        sub_goals = agent.planner.decompose(CRAFTING_OBJECTIVE, progress)

        # items_crafted target=3, current=1 → should be a goal
        assert len(sub_goals) >= 1

    def test_multi_tick_material_gathering(self, agent):
        """Agent should consistently pursue materials over multiple ticks."""
        decisions = []
        for tick in range(1, 4):
            wood = make_raw_material(
                f"wood_{tick:03d}", "material",
                position=(10.0, 0.0, 0.0),
                distance=max(2.0, 10.0 - tick * 3.0),
            )
            # Set items_crafted as complete so materials_collected is the active goal
            obs = make_crafting_obs(
                tick=tick,
                position=(tick * 3.0, 0.0, 0.0),
                resources=[wood],
                progress={"items_crafted": 3.0, "materials_collected": 2.0, "health_remaining": 100.0},
            )
            decisions.append(agent.decide(obs))

        for d in decisions:
            assert_valid_decision(d)
            assert d.tool in {"move_to", "collect"}

    def test_avoids_hazards_near_station(self, agent):
        """Agent should escape hazard even when near a crafting station."""
        hazard = make_hazard("lava_001", "lava", (1.0, 0.0, 0.0), 1.5)
        station = make_crafting_station("forge_001", "station", (5.0, 0.0, 5.0), 5.0)
        obs = make_crafting_obs(hazards=[hazard], resources=[station])

        decision = agent.decide(obs)

        assert_valid_decision(decision)
        assert decision.tool == "move_to"
        target = decision.params["target_position"]
        assert distance_between(target, hazard.position) > hazard.distance

    def test_remembers_multiple_resource_types(self, agent):
        """Agent should track different types of materials in memory."""
        # Tick 1: See wood
        wood = make_raw_material("wood_001", "material", (5.0, 0.0, 0.0), 3.0)
        obs1 = make_crafting_obs(tick=1, resources=[wood])
        agent.decide(obs1)

        # Tick 2: See stone
        stone = make_raw_material("stone_001", "material", (0.0, 0.0, 8.0), 6.0)
        obs2 = make_crafting_obs(tick=2, position=(2.0, 0.0, 0.0), resources=[stone])
        agent.decide(obs2)

        # Tick 3: See ore
        ore = make_raw_material("ore_001", "material", (10.0, 0.0, 10.0), 10.0)
        obs3 = make_crafting_obs(tick=3, position=(3.0, 0.0, 0.0), resources=[ore])
        agent.decide(obs3)

        resources = agent.memory.find_resources_seen()
        names = [name for name, _, _ in resources]
        assert "wood_001" in names
        assert "stone_001" in names
        assert "ore_001" in names

    def test_tracks_inventory_changes(self, agent):
        """Agent should handle observations with inventory items."""
        inv = [
            ItemInfo(id="inv_1", name="wood", quantity=3),
            ItemInfo(id="inv_2", name="stone", quantity=2),
        ]
        obs = make_crafting_obs(
            tick=5,
            inventory=inv,
            progress={"items_crafted": 0.0, "materials_collected": 5.0, "health_remaining": 100.0},
        )

        decision = agent.decide(obs)

        assert_valid_decision(decision)

    def test_explores_for_materials(self, agent):
        """Agent should explore when no materials are visible."""
        obs = make_crafting_obs(exploration=CRAFTING_EXPLORATION)

        decision = agent.decide(obs)

        assert_valid_decision(decision)
        assert decision.tool in {"move_to", "idle"}


# ------------------------------------------------------------------ #
#  LLM Starter - Crafting Scenario (Fallback Logic)
# ------------------------------------------------------------------ #


class TestLLMStarterCrafting:
    """Test the LLM starter's fallback and parsing logic with crafting scenarios."""

    @pytest.fixture
    def agent_cls(self):
        from starters.llm.agent import Agent

        return Agent

    def test_fallback_collects_material(self, agent_cls):
        """Fallback should move toward visible materials."""
        agent = object.__new__(agent_cls)
        agent.VALID_TOOLS = {"move_to", "collect", "idle"}
        agent.HAZARD_SAFE_DISTANCE = 3.0

        wood = make_raw_material("wood_001", "material", (8.0, 0.0, 3.0), 5.0)
        obs = make_crafting_obs(resources=[wood])

        decision = agent._fallback_decision(obs)

        assert_valid_decision(decision)
        assert decision.tool == "move_to"
        target = decision.params["target_position"]
        assert distance_between(target, wood.position) < 1.0

    def test_fallback_flees_hazard(self, agent_cls):
        """Fallback should flee from close hazards in crafting scenario."""
        agent = object.__new__(agent_cls)
        agent.VALID_TOOLS = {"move_to", "collect", "idle"}
        agent.HAZARD_SAFE_DISTANCE = 3.0

        hazard = make_hazard("lava_001", "lava", (1.0, 0.0, 0.0), 1.5)
        obs = make_crafting_obs(hazards=[hazard])

        decision = agent._fallback_decision(obs)

        assert_valid_decision(decision)
        assert decision.tool == "move_to"
        target = decision.params["target_position"]
        assert distance_between(target, hazard.position) > hazard.distance

    def test_fallback_explores_for_materials(self, agent_cls):
        """Fallback should explore when no materials visible."""
        agent = object.__new__(agent_cls)
        agent.VALID_TOOLS = {"move_to", "collect", "idle"}
        agent.HAZARD_SAFE_DISTANCE = 3.0

        obs = make_crafting_obs(exploration=CRAFTING_EXPLORATION)

        decision = agent._fallback_decision(obs)

        assert_valid_decision(decision)
        assert decision.tool == "move_to"

    def test_parse_crafting_collect_response(self, agent_cls):
        """Parser should handle collect tool for crafting materials."""
        agent = object.__new__(agent_cls)
        agent.VALID_TOOLS = {"move_to", "collect", "idle"}
        agent.HAZARD_SAFE_DISTANCE = 3.0

        response = {
            "text": '{"tool": "collect", "params": {"target_name": "wood_001"}, "reasoning": "Collecting wood for crafting"}',
        }
        obs = make_crafting_obs()

        decision = agent._parse_response(response, obs)

        assert decision.tool == "collect"
        assert decision.params["target_name"] == "wood_001"

    def test_parse_move_to_station_response(self, agent_cls):
        """Parser should handle move_to for crafting station."""
        agent = object.__new__(agent_cls)
        agent.VALID_TOOLS = {"move_to", "collect", "idle"}
        agent.HAZARD_SAFE_DISTANCE = 3.0

        response = {
            "text": '{"tool": "move_to", "params": {"target_position": [15.0, 0.0, 0.0]}, "reasoning": "Moving to workbench"}',
        }
        obs = make_crafting_obs()

        decision = agent._parse_response(response, obs)

        assert decision.tool == "move_to"
        assert decision.params["target_position"] == [15.0, 0.0, 0.0]

    def test_parse_idle_while_crafting(self, agent_cls):
        """Parser should handle idle (waiting for craft to complete)."""
        agent = object.__new__(agent_cls)
        agent.VALID_TOOLS = {"move_to", "collect", "idle"}
        agent.HAZARD_SAFE_DISTANCE = 3.0

        response = {
            "text": '{"tool": "idle", "params": {}, "reasoning": "Waiting for crafting to finish"}',
        }
        obs = make_crafting_obs()

        decision = agent._parse_response(response, obs)

        assert decision.tool == "idle"

    def test_fallback_prefers_closer_material(self, agent_cls):
        """Fallback should choose the closest material."""
        agent = object.__new__(agent_cls)
        agent.VALID_TOOLS = {"move_to", "collect", "idle"}
        agent.HAZARD_SAFE_DISTANCE = 3.0

        far = make_raw_material("wood_far", "material", (20.0, 0.0, 0.0), 20.0)
        close = make_raw_material("stone_close", "material", (3.0, 0.0, 0.0), 3.0)
        obs = make_crafting_obs(resources=[far, close])

        decision = agent._fallback_decision(obs)

        assert_valid_decision(decision)
        assert decision.tool == "move_to"
        target = decision.params["target_position"]
        assert distance_between(target, close.position) < distance_between(
            target, far.position
        )


# ------------------------------------------------------------------ #
#  Planner Tests with Crafting Objective
# ------------------------------------------------------------------ #


class TestPlannerCrafting:
    """Test the planner with crafting-specific objectives."""

    @pytest.fixture
    def planner(self):
        _clear_starter_modules()
        intermediate_dir = str(ROOT / "starters" / "intermediate")
        if intermediate_dir in sys.path:
            sys.path.remove(intermediate_dir)
        sys.path.insert(0, intermediate_dir)

        from starters.intermediate.planner import Planner

        return Planner()

    def test_decomposes_crafting_objective(self, planner):
        """Planner should create goals from crafting objective."""
        progress = {"items_crafted": 1.0, "materials_collected": 2.0, "health_remaining": 90.0}

        sub_goals = planner.decompose(CRAFTING_OBJECTIVE, progress)

        assert len(sub_goals) >= 1
        # items_crafted (required, 1/3) should be highest priority
        assert sub_goals[0].metric_name == "items_crafted"

    def test_crafting_required_metric_prioritized(self, planner):
        """Required crafting metric should have highest priority."""
        progress = {"items_crafted": 0.0, "materials_collected": 0.0, "health_remaining": 80.0}

        sub_goals = planner.decompose(CRAFTING_OBJECTIVE, progress)

        # items_crafted is required=True, should be first
        required_goals = [g for g in sub_goals if g.metric_name == "items_crafted"]
        assert len(required_goals) == 1
        assert sub_goals[0].metric_name == "items_crafted"

    def test_tracks_crafting_progress(self, planner):
        """Sub-goals should reflect correct crafting progress."""
        progress = {"items_crafted": 2.0, "materials_collected": 5.0}

        sub_goals = planner.decompose(CRAFTING_OBJECTIVE, progress)

        crafting_goal = next((g for g in sub_goals if g.metric_name == "items_crafted"), None)
        assert crafting_goal is not None
        assert crafting_goal.current == 2.0
        assert crafting_goal.target == 3.0
        assert abs(crafting_goal.progress_percent() - 66.67) < 1.0

    def test_materials_goal_when_incomplete(self, planner):
        """Should have materials goal when materials_collected < target."""
        progress = {"items_crafted": 0.0, "materials_collected": 2.0}

        sub_goals = planner.decompose(CRAFTING_OBJECTIVE, progress)

        materials_goals = [g for g in sub_goals if g.metric_name == "materials_collected"]
        assert len(materials_goals) == 1
        assert materials_goals[0].current == 2.0
        assert materials_goals[0].target == 6.0

    def test_explain_crafting_plan(self, planner):
        """Planner should produce readable crafting plan."""
        progress = {"items_crafted": 1.0, "materials_collected": 3.0}

        sub_goals = planner.decompose(CRAFTING_OBJECTIVE, progress)
        explanation = planner.explain_plan(sub_goals)

        assert "Sub-goals:" in explanation


# ------------------------------------------------------------------ #
#  Memory with Crafting Data
# ------------------------------------------------------------------ #


class TestMemoryCrafting:
    """Test sliding window memory with crafting-specific data."""

    @pytest.fixture
    def memory(self):
        _clear_starter_modules()
        intermediate_dir = str(ROOT / "starters" / "intermediate")
        if intermediate_dir in sys.path:
            sys.path.remove(intermediate_dir)
        sys.path.insert(0, intermediate_dir)

        from starters.intermediate.memory import SlidingWindowMemory

        return SlidingWindowMemory(capacity=20)

    def test_remembers_crafting_materials(self, memory):
        """Memory should track different crafting materials."""
        obs1 = make_crafting_obs(
            tick=1,
            resources=[make_raw_material("wood_001", "material", (5.0, 0.0, 0.0), 3.0)],
        )
        obs2 = make_crafting_obs(
            tick=2,
            resources=[make_raw_material("stone_001", "material", (8.0, 0.0, 8.0), 6.0)],
        )
        obs3 = make_crafting_obs(
            tick=3,
            resources=[make_raw_material("ore_001", "material", (12.0, 0.0, 4.0), 10.0)],
        )

        memory.store(obs1)
        memory.store(obs2)
        memory.store(obs3)

        resources = memory.find_resources_seen()
        names = [name for name, _, _ in resources]
        assert "wood_001" in names
        assert "stone_001" in names
        assert "ore_001" in names

    def test_remembers_crafting_stations(self, memory):
        """Memory should track crafting station locations."""
        obs = make_crafting_obs(
            tick=1,
            resources=[
                make_crafting_station("workbench_001", "station", (15.0, 0.0, 0.0), 10.0),
                make_crafting_station("forge_001", "station", (20.0, 0.0, 10.0), 15.0),
            ],
        )
        memory.store(obs)

        resources = memory.find_resources_seen()
        names = [name for name, _, _ in resources]
        assert "workbench_001" in names
        assert "forge_001" in names

    def test_summarize_crafting_memory(self, memory):
        """Memory summary should include crafting materials and stations."""
        obs = make_crafting_obs(
            tick=1,
            resources=[
                make_raw_material("wood_001", "material"),
                make_crafting_station("workbench_001", "station"),
            ],
            hazards=[make_hazard("lava_001", "lava")],
        )
        memory.store(obs)

        summary = memory.summarize()
        assert "Resources seen: 2" in summary
        assert "Hazards seen: 1" in summary

    def test_recent_observations_order(self, memory):
        """get_recent should return most recent first."""
        for tick in range(1, 6):
            memory.store(make_crafting_obs(tick=tick))

        recent = memory.get_recent(3)
        assert len(recent) == 3
        assert recent[0].tick == 5  # Most recent first
        assert recent[1].tick == 4
        assert recent[2].tick == 3
