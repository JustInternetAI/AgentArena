"""
Tests for the intermediate agent.

Run with:
    cd starters/intermediate
    python -m pytest test_agent.py -v

Or from the repo root:
    python -m pytest starters/intermediate/test_agent.py -v
"""

import sys
from pathlib import Path

# Ensure SDK and local modules are importable
_repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_repo_root / "python" / "sdk"))
sys.path.insert(0, str(Path(__file__).parent))

from agent_arena_sdk.testing import (
    MockArena,
    mock_hazard,
    mock_observation,
    mock_resource,
    mock_station,
)
from agent_arena_sdk.schemas import ToolResult
from agent import Agent
from memory import SlidingWindowMemory
from planner import Planner


# ---------------------------------------------------------------------------
#  Agent decision tests
# ---------------------------------------------------------------------------


class TestHazardEscape:
    def test_escapes_nearby_fire(self):
        agent = Agent()
        obs = mock_observation(
            tick=1,
            position=(0.0, 0.0, 0.0),
            health=80.0,
            nearby_hazards=[mock_hazard("fire", position=(1.0, 0.0, 0.0), distance=1.5)],
        )
        decision = agent.decide(obs)
        assert decision.tool == "move_to"
        # Should move AWAY from the fire (negative x direction)
        assert decision.params["target_position"][0] < 0

    def test_avoids_remembered_hazard(self):
        agent = Agent()
        # Tick 1: See hazard far away (not dangerous yet)
        obs1 = mock_observation(
            agent_id="a", tick=1, position=(10.0, 0.0, 10.0),
            nearby_hazards=[mock_hazard("fire", position=(5.0, 0.0, 5.0), distance=7.0)],
        )
        agent.decide(obs1)

        # Tick 2: Walk closer to remembered hazard (no longer visible)
        obs2 = mock_observation(
            agent_id="a", tick=2, position=(6.0, 0.0, 6.0),
        )
        decision = agent.decide(obs2)
        assert decision.tool == "move_to"
        assert "remembered" in decision.reasoning.lower() or "avoid" in decision.reasoning.lower()


class TestResourceCollection:
    def test_moves_to_visible_resource(self):
        agent = Agent()
        obs = mock_observation(
            tick=1,
            position=(0.0, 0.0, 0.0),
            nearby_resources=[mock_resource("berry", position=(5.0, 0.0, 3.0), distance=5.8)],
        )
        decision = agent.decide(obs)
        assert decision.tool == "move_to"
        # Should target the resource position
        tp = decision.params["target_position"]
        assert tp == [5.0, 0.0, 3.0] or tp == (5.0, 0.0, 3.0)

    def test_collects_when_close(self):
        agent = Agent()
        obs = mock_observation(
            tick=1,
            position=(0.0, 0.0, 0.0),
            nearby_resources=[mock_resource("berry", position=(0.5, 0.0, 0.5), distance=0.7)],
        )
        decision = agent.decide(obs)
        assert decision.tool == "collect"

    def test_uses_memory_when_no_visible_resources(self):
        agent = Agent()
        # Tick 1: See a resource
        obs1 = mock_observation(
            agent_id="a", tick=1, position=(0.0, 0.0, 0.0),
            nearby_resources=[mock_resource("berry", position=(10.0, 0.0, 5.0), distance=11.2)],
        )
        agent.decide(obs1)

        # Tick 2: No resources visible — should remember the berry
        obs2 = mock_observation(
            agent_id="a", tick=2, position=(0.0, 0.0, 0.0),
        )
        decision = agent.decide(obs2)
        assert decision.tool == "move_to"
        tp = decision.params["target_position"]
        assert list(tp) == [10.0, 0.0, 5.0]


class TestCrafting:
    def test_crafts_at_station_with_materials(self):
        agent = Agent()
        obs = mock_observation(
            tick=1,
            position=(0.0, 0.0, 0.0),
            inventory={"wood": 2, "stone": 1},
            nearby_stations=[mock_station("workbench", position=(1.0, 0.0, 0.0), distance=1.0)],
        )
        decision = agent.decide(obs)
        assert decision.tool == "craft_item"
        assert decision.params["recipe"] == "torch"

    def test_crafts_meal_with_berries(self):
        agent = Agent()
        obs = mock_observation(
            tick=1,
            position=(0.0, 0.0, 0.0),
            inventory={"berry": 3},
            nearby_stations=[mock_station("workbench", position=(1.0, 0.0, 0.0), distance=1.0)],
        )
        decision = agent.decide(obs)
        assert decision.tool == "craft_item"
        assert decision.params["recipe"] in ("torch", "meal")


class TestDangerVsReward:
    def test_prioritizes_safety_over_collection(self):
        agent = Agent()
        obs = mock_observation(
            tick=1,
            position=(0.0, 0.0, 0.0),
            health=60.0,
            nearby_hazards=[mock_hazard("fire", position=(2.0, 0.0, 0.0), distance=2.0)],
            nearby_resources=[mock_resource("berry", position=(3.0, 0.0, 1.0), distance=3.2)],
        )
        decision = agent.decide(obs)
        # Should escape, not collect
        assert decision.tool == "move_to"
        assert "escap" in decision.reasoning.lower() or "avoid" in decision.reasoning.lower()


class TestToolResultHandling:
    def test_replans_on_failure(self):
        agent = Agent()
        # Tick 1: Start collecting a resource (creates plan)
        obs1 = mock_observation(
            agent_id="a", tick=1, position=(0.0, 0.0, 0.0),
            nearby_resources=[mock_resource("berry", position=(5.0, 0.0, 3.0), distance=5.8)],
        )
        d1 = agent.decide(obs1)
        assert d1.tool == "move_to"  # First step of collect plan

        # Tick 2: Tool failed — plan should be cancelled, agent replans
        failed_result = ToolResult(tool="move_to", success=False, error="path_blocked")
        obs2 = mock_observation(
            agent_id="a", tick=2, position=(0.0, 0.0, 0.0),
            last_tool_result=failed_result,
        )
        d2 = agent.decide(obs2)
        # Agent should still produce a valid decision (not stuck on old plan)
        assert d2.tool in ("move_to", "collect", "idle", "craft_item")

    def test_advances_plan_on_success(self):
        agent = Agent()
        # Tick 1: Start collecting a resource (creates 2-step plan: move + collect)
        obs1 = mock_observation(
            agent_id="a", tick=1, position=(0.0, 0.0, 0.0),
            nearby_resources=[mock_resource("berry", position=(5.0, 0.0, 3.0), distance=5.8)],
        )
        d1 = agent.decide(obs1)
        assert d1.tool == "move_to"

        # Tick 2: Tool succeeded — should advance to collect step
        success_result = ToolResult(tool="move_to", success=True)
        obs2 = mock_observation(
            agent_id="a", tick=2, position=(5.0, 0.0, 3.0),
            nearby_resources=[mock_resource("berry", position=(5.0, 0.0, 3.0), distance=0.1)],
            last_tool_result=success_result,
        )
        d2 = agent.decide(obs2)
        assert d2.tool == "collect"


class TestExploration:
    def test_explores_when_nothing_to_do(self):
        agent = Agent()
        obs = mock_observation(
            tick=10,
            position=(0.0, 0.0, 0.0),
            health=100.0,
        )
        decision = agent.decide(obs)
        # Should explore, not idle
        assert decision.tool == "move_to"


# ---------------------------------------------------------------------------
#  Memory unit tests
# ---------------------------------------------------------------------------


class TestMemory:
    def test_mark_collected(self):
        mem = SlidingWindowMemory(capacity=10)
        obs = mock_observation(
            agent_id="a", tick=1,
            nearby_resources=[mock_resource("berry", position=(5, 0, 3), distance=5)],
        )
        mem.store(obs)

        # Before marking: should appear in uncollected
        uncollected = mem.find_uncollected_resources(current_tick=2)
        assert len(uncollected) == 1

        # After marking: should be filtered out
        mem.mark_collected(uncollected[0][0])
        uncollected = mem.find_uncollected_resources(current_tick=2)
        assert len(uncollected) == 0

    def test_find_productive_areas(self):
        mem = SlidingWindowMemory(capacity=20)
        # Add observations with resources clustered in the same area
        for i in range(5):
            obs = mock_observation(
                agent_id="a", tick=i,
                nearby_resources=[
                    mock_resource("berry", position=(10 + i * 0.5, 0, 10 + i * 0.5), distance=5),
                ],
            )
            mem.store(obs)

        areas = mem.find_productive_areas()
        assert len(areas) >= 1
        # Centroid should be near (11, 0, 11)
        assert 9 < areas[0][0] < 13
        assert 9 < areas[0][2] < 13

    def test_hazard_zones_recency(self):
        mem = SlidingWindowMemory(capacity=10)
        obs = mock_observation(
            agent_id="a", tick=1,
            nearby_hazards=[mock_hazard("fire", position=(5, 0, 5), distance=5)],
        )
        mem.store(obs)

        # Recent: should appear
        zones = mem.find_hazard_zones(current_tick=10, recency=30)
        assert len(zones) == 1

        # Old: should not appear
        zones = mem.find_hazard_zones(current_tick=100, recency=30)
        assert len(zones) == 0


# ---------------------------------------------------------------------------
#  Planner unit tests
# ---------------------------------------------------------------------------


class TestPlanner:
    def test_plan_collect_creates_steps(self):
        p = Planner()
        steps = p.plan_collect("berry_001", (5, 0, 3), (0, 0, 0))
        assert len(steps) == 2  # move_to + collect
        assert steps[0].tool == "move_to"
        assert steps[1].tool == "collect"

    def test_plan_collect_skips_move_when_close(self):
        p = Planner()
        steps = p.plan_collect("berry_001", (0.5, 0, 0.5), (0, 0, 0))
        assert len(steps) == 1  # just collect
        assert steps[0].tool == "collect"

    def test_plan_craft_with_missing_materials(self):
        p = Planner()
        steps = p.plan_craft(
            recipe="torch",
            station_name="workbench_001",
            station_position=(10, 0, 10),
            missing_materials=[("wood_001", (5, 0, 3))],
        )
        # move_to wood, collect wood, move_to station, craft
        assert len(steps) == 4
        assert steps[0].tool == "move_to"
        assert steps[1].tool == "collect"
        assert steps[2].tool == "move_to"
        assert steps[3].tool == "craft_item"

    def test_plan_execution_lifecycle(self):
        p = Planner()
        steps = p.plan_collect("berry_001", (5, 0, 3), (0, 0, 0))
        p.set_plan(steps)

        assert p.has_active_plan()
        assert p.current_step().tool == "move_to"

        p.advance()
        assert p.current_step().tool == "collect"

        p.advance()
        assert not p.has_active_plan()

    def test_cancel_clears_plan(self):
        p = Planner()
        p.set_plan(p.plan_collect("berry_001", (5, 0, 3), (0, 0, 0)))
        assert p.has_active_plan()

        p.cancel()
        assert not p.has_active_plan()


# ---------------------------------------------------------------------------
#  Integration: MockArena multi-tick test
# ---------------------------------------------------------------------------


class TestMockArenaIntegration:
    def test_collects_resources_over_time(self):
        arena = MockArena()
        arena.add_resource("berry", position=(5, 0, 3))
        arena.add_resource("berry", position=(8, 0, 1))

        agent = Agent()
        results = arena.run(agent.decide, ticks=50)

        assert results.resources_collected >= 1
        assert results.ticks_survived == 50

    def test_survives_with_hazards(self):
        arena = MockArena()
        arena.add_resource("berry", position=(10, 0, 0))
        arena.add_hazard("fire", position=(3, 0, 0), damage=5.0)

        agent = Agent()
        results = arena.run(agent.decide, ticks=30)

        # Should survive (escape the fire instead of walking through it)
        assert results.final_health > 0
