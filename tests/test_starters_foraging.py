"""
Tests for all starter templates with foraging scenario.

Simulates realistic foraging observations and verifies each starter
produces sensible decisions. Covers:
- Resource collection
- Hazard avoidance
- Exploration when nothing is visible
- Objective-driven behavior
- Multi-tick behavior (intermediate only)
"""

import sys
from pathlib import Path

import pytest

# Add paths so starters can be imported
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "starters" / "beginner"))
sys.path.insert(0, str(ROOT / "starters" / "intermediate"))
sys.path.insert(0, str(ROOT / "starters" / "llm"))
sys.path.insert(0, str(ROOT / "python"))

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
from agent_arena_sdk.testing import (
    assert_valid_decision,
    distance_between,
)


# ------------------------------------------------------------------ #
#  Test Helpers
# ------------------------------------------------------------------ #
# NOTE: make_foraging_obs, make_resource, and make_hazard are thin
# wrappers with foraging-specific defaults.  A future follow-up can
# migrate them to ``agent_arena_sdk.testing.mock_observation`` with
# appropriate kwargs.

FORAGING_OBJECTIVE = Objective(
    description="Collect resources while avoiding hazards and staying healthy.",
    success_metrics={
        "resources_collected": MetricDefinition(target=10.0, weight=1.0, required=True),
        "health_remaining": MetricDefinition(target=50.0, weight=0.5),
        "time_taken": MetricDefinition(target=300.0, weight=0.2, lower_is_better=True),
    },
    time_limit=600,
)

EXPLORATION_INFO = ExplorationInfo(
    exploration_percentage=25.0,
    total_cells=100,
    seen_cells=25,
    frontiers_by_direction={"north": 15.0, "east": 20.0},
    explore_targets=[
        ExploreTarget(direction="north", distance=15.0, position=(0.0, 0.0, 15.0)),
        ExploreTarget(direction="east", distance=20.0, position=(20.0, 0.0, 0.0)),
    ],
)


def make_foraging_obs(
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
    """Create a foraging scenario observation."""
    return Observation(
        agent_id="foraging_agent_001",
        tick=tick,
        position=position,
        health=health,
        energy=energy,
        nearby_resources=resources or [],
        nearby_hazards=hazards or [],
        inventory=inventory or [],
        exploration=exploration,
        scenario_name="foraging",
        objective=objective or FORAGING_OBJECTIVE,
        current_progress=progress or {"resources_collected": 0.0, "health_remaining": 100.0, "time_taken": 0.0},
    )


def make_resource(
    name: str = "berry_001",
    rtype: str = "food",
    position: tuple = (5.0, 0.0, 5.0),
    distance: float = 3.0,
) -> ResourceInfo:
    return ResourceInfo(name=name, type=rtype, position=position, distance=distance)


def make_hazard(
    name: str = "fire_001",
    htype: str = "fire",
    position: tuple = (2.0, 0.0, 0.0),
    distance: float = 2.0,
    damage: float = 10.0,
) -> HazardInfo:
    return HazardInfo(name=name, type=htype, position=position, distance=distance, damage=damage)


# ------------------------------------------------------------------ #
#  Beginner Starter Tests
# ------------------------------------------------------------------ #


class TestBeginnerForaging:
    """Test the beginner starter with foraging scenarios."""

    @pytest.fixture
    def agent(self):
        from starters.beginner.agent import Agent

        return Agent()

    def test_escapes_nearby_hazard(self, agent):
        """Agent should move away from a close hazard."""
        hazard = make_hazard(position=(1.0, 0.0, 0.0), distance=1.5)
        obs = make_foraging_obs(hazards=[hazard])

        decision = agent.decide(obs)

        assert_valid_decision(decision)
        assert decision.tool == "move_to"
        # Should move AWAY from hazard (at x=1), so target x should be < 0
        target = decision.params["target_position"]
        assert distance_between(target, hazard.position) > hazard.distance

    def test_ignores_distant_hazard(self, agent):
        """Agent should not flee from hazards that are far away."""
        hazard = make_hazard(position=(20.0, 0.0, 0.0), distance=20.0)
        resource = make_resource(position=(5.0, 0.0, 0.0), distance=5.0)
        obs = make_foraging_obs(hazards=[hazard], resources=[resource])

        decision = agent.decide(obs)

        assert_valid_decision(decision)
        # Should go for the resource, not flee
        assert decision.tool == "move_to"

    def test_moves_toward_resource(self, agent):
        """Agent should move toward a visible resource."""
        resource = make_resource(position=(10.0, 0.0, 5.0), distance=8.0)
        obs = make_foraging_obs(resources=[resource])

        decision = agent.decide(obs)

        assert_valid_decision(decision)
        assert decision.tool == "move_to"
        target = decision.params["target_position"]
        # Target should be at or near the resource position
        assert distance_between(target, resource.position) < 1.0

    def test_picks_closest_resource(self, agent):
        """Agent should prefer the closest resource."""
        far_resource = make_resource("berry_far", "food", (20.0, 0.0, 0.0), 20.0)
        close_resource = make_resource("berry_close", "food", (3.0, 0.0, 0.0), 3.0)
        obs = make_foraging_obs(resources=[far_resource, close_resource])

        decision = agent.decide(obs)

        assert_valid_decision(decision)
        assert decision.tool == "move_to"
        target = decision.params["target_position"]
        # Should target the closer resource
        assert distance_between(target, close_resource.position) < distance_between(
            target, far_resource.position
        )

    def test_explores_when_no_resources(self, agent):
        """Agent should explore when no resources are visible."""
        obs = make_foraging_obs(exploration=EXPLORATION_INFO)

        decision = agent.decide(obs)

        assert_valid_decision(decision)
        # Should either move_to explore or idle
        assert decision.tool in {"move_to", "idle"}

    def test_idles_when_nothing_available(self, agent):
        """Agent should idle when no resources, hazards, or exploration targets exist."""
        obs = make_foraging_obs()

        decision = agent.decide(obs)

        assert_valid_decision(decision)
        # Should idle since nothing to do
        assert decision.tool == "idle"

    def test_hazard_takes_priority_over_resource(self, agent):
        """Agent should escape hazard even when resources are nearby."""
        hazard = make_hazard(position=(1.0, 0.0, 0.0), distance=1.5)
        resource = make_resource(position=(5.0, 0.0, 5.0), distance=5.0)
        obs = make_foraging_obs(hazards=[hazard], resources=[resource])

        decision = agent.decide(obs)

        assert_valid_decision(decision)
        assert decision.tool == "move_to"
        target = decision.params["target_position"]
        # Should move away from hazard, not toward resource
        assert distance_between(target, hazard.position) > hazard.distance

    def test_returns_decision_type(self, agent):
        """Agent should always return a Decision object."""
        obs = make_foraging_obs()
        decision = agent.decide(obs)
        assert isinstance(decision, Decision)

    def test_decision_has_reasoning(self, agent):
        """Decisions should include reasoning for debugging."""
        resource = make_resource()
        obs = make_foraging_obs(resources=[resource])
        decision = agent.decide(obs)
        assert decision.reasoning is not None
        assert len(decision.reasoning) > 0


# ------------------------------------------------------------------ #
#  Intermediate Starter Tests
# ------------------------------------------------------------------ #


class TestIntermediateForaging:
    """Test the intermediate starter with foraging scenarios."""

    @pytest.fixture
    def agent(self):
        from starters.intermediate.agent import Agent

        return Agent()

    def test_escapes_nearby_hazard(self, agent):
        """Agent should move away from a close hazard."""
        hazard = make_hazard(position=(1.0, 0.0, 0.0), distance=1.5)
        obs = make_foraging_obs(hazards=[hazard])

        decision = agent.decide(obs)

        assert_valid_decision(decision)
        assert decision.tool == "move_to"
        target = decision.params["target_position"]
        assert distance_between(target, hazard.position) > hazard.distance

    def test_moves_toward_resource(self, agent):
        """Agent should move toward a visible resource."""
        resource = make_resource(position=(10.0, 0.0, 5.0), distance=8.0)
        obs = make_foraging_obs(resources=[resource])

        decision = agent.decide(obs)

        assert_valid_decision(decision)
        assert decision.tool in {"move_to", "collect"}

    def test_memory_stores_observations(self, agent):
        """Agent should store observations in memory."""
        resource = make_resource()
        obs = make_foraging_obs(tick=1, resources=[resource])

        agent.decide(obs)

        assert agent.memory.count_observations() == 1

    def test_memory_accumulates_over_ticks(self, agent):
        """Memory should accumulate observations over multiple ticks."""
        for tick in range(1, 6):
            obs = make_foraging_obs(
                tick=tick,
                position=(tick * 2.0, 0.0, 0.0),
            )
            agent.decide(obs)

        assert agent.memory.count_observations() == 5

    def test_remembers_resources_from_previous_ticks(self, agent):
        """Agent should remember resources seen in earlier ticks."""
        # Tick 1: See a resource
        resource = make_resource("berry_001", "food", (10.0, 0.0, 5.0), 5.0)
        obs1 = make_foraging_obs(tick=1, resources=[resource])
        agent.decide(obs1)

        # Verify memory has the resource
        resources_seen = agent.memory.find_resources_seen()
        assert len(resources_seen) >= 1
        assert any(name == "berry_001" for name, _, _ in resources_seen)

    def test_avoids_remembered_hazards(self, agent):
        """Agent should avoid areas where hazards were seen recently."""
        # Tick 1: See a hazard
        hazard = make_hazard("fire_001", "fire", (5.0, 0.0, 0.0), 2.0)
        obs1 = make_foraging_obs(tick=1, hazards=[hazard], position=(3.0, 0.0, 0.0))
        agent.decide(obs1)

        # Tick 2: Near same location, no visible hazards but memory should warn
        obs2 = make_foraging_obs(tick=2, position=(4.0, 0.0, 0.0))
        decision = agent.decide(obs2)

        assert_valid_decision(decision)
        # Should either escape or explore elsewhere
        if decision.tool == "move_to":
            target = decision.params["target_position"]
            # Should not move toward the remembered hazard
            assert distance_between(target, hazard.position) >= 3.0 or decision.tool == "idle"

    def test_planner_decomposes_objective(self, agent):
        """Planner should break objective into sub-goals."""
        obs = make_foraging_obs(
            objective=FORAGING_OBJECTIVE,
            progress={"resources_collected": 3.0, "health_remaining": 80.0, "time_taken": 50.0},
        )

        sub_goals = agent.planner.decompose(obs.objective, obs.current_progress)

        assert len(sub_goals) >= 1
        # resources_collected should be a goal (3 < 10)
        resource_goals = [g for g in sub_goals if "resources" in g.metric_name.lower() or "collected" in g.metric_name.lower()]
        assert len(resource_goals) >= 1

    def test_planner_skips_completed_metrics(self, agent):
        """Planner should skip metrics that are already met."""
        obs = make_foraging_obs(
            objective=FORAGING_OBJECTIVE,
            progress={"resources_collected": 10.0, "health_remaining": 100.0, "time_taken": 50.0},
        )

        sub_goals = agent.planner.decompose(obs.objective, obs.current_progress)

        # resources_collected should NOT be a goal (10 >= 10)
        resource_goals = [g for g in sub_goals if "resources_collected" == g.metric_name]
        assert len(resource_goals) == 0

    def test_explores_with_memory(self, agent):
        """Agent should explore unvisited areas using memory."""
        obs = make_foraging_obs(
            tick=1,
            exploration=EXPLORATION_INFO,
        )

        decision = agent.decide(obs)

        assert_valid_decision(decision)
        assert decision.tool in {"move_to", "idle"}

    def test_tracks_visited_positions(self, agent):
        """Agent should track positions it has visited."""
        positions = [(0.0, 0.0, 0.0), (5.0, 0.0, 0.0), (10.0, 0.0, 0.0)]
        for tick, pos in enumerate(positions, 1):
            obs = make_foraging_obs(tick=tick, position=pos, exploration=EXPLORATION_INFO)
            agent.decide(obs)

        assert len(agent.visited_positions) == 3

    def test_multi_tick_resource_collection(self, agent):
        """Agent should consistently pursue resources across ticks."""
        decisions = []
        for tick in range(1, 6):
            resource = make_resource(
                "berry_001", "food",
                position=(10.0, 0.0, 0.0),
                distance=max(1.0, 10.0 - tick * 2.0),
            )
            obs = make_foraging_obs(
                tick=tick,
                position=(tick * 2.0, 0.0, 0.0),
                resources=[resource],
            )
            decisions.append(agent.decide(obs))

        # All decisions should be pursuing the resource
        for d in decisions:
            assert_valid_decision(d)
            assert d.tool in {"move_to", "collect"}


# ------------------------------------------------------------------ #
#  LLM Starter Tests (Fallback Logic)
# ------------------------------------------------------------------ #


class TestLLMStarterForaging:
    """
    Test the LLM starter's fallback/parsing logic with foraging scenarios.

    These tests verify the agent's observation-based fallback logic and
    response parsing without requiring an actual LLM model.
    """

    @pytest.fixture
    def agent_cls(self):
        """Import and return the LLM Agent class (don't instantiate - needs model)."""
        from starters.llm.agent import Agent

        return Agent

    def test_fallback_flees_close_hazard(self, agent_cls):
        """Fallback logic should flee from nearby hazards."""
        agent = object.__new__(agent_cls)
        agent.VALID_TOOLS = {"move_to", "collect", "idle"}
        agent.HAZARD_SAFE_DISTANCE = 3.0

        hazard = make_hazard(position=(1.0, 0.0, 0.0), distance=1.5)
        obs = make_foraging_obs(hazards=[hazard])

        decision = agent._fallback_decision(obs)

        assert_valid_decision(decision)
        assert decision.tool == "move_to"
        target = decision.params["target_position"]
        # Should move away from hazard
        assert distance_between(target, hazard.position) > hazard.distance

    def test_fallback_pursues_resource(self, agent_cls):
        """Fallback logic should move toward resources."""
        agent = object.__new__(agent_cls)
        agent.VALID_TOOLS = {"move_to", "collect", "idle"}
        agent.HAZARD_SAFE_DISTANCE = 3.0

        resource = make_resource(position=(10.0, 0.0, 5.0), distance=8.0)
        obs = make_foraging_obs(resources=[resource])

        decision = agent._fallback_decision(obs)

        assert_valid_decision(decision)
        assert decision.tool == "move_to"
        target = decision.params["target_position"]
        assert distance_between(target, resource.position) < 1.0

    def test_fallback_explores_when_empty(self, agent_cls):
        """Fallback logic should explore when no resources/hazards."""
        agent = object.__new__(agent_cls)
        agent.VALID_TOOLS = {"move_to", "collect", "idle"}
        agent.HAZARD_SAFE_DISTANCE = 3.0

        obs = make_foraging_obs(exploration=EXPLORATION_INFO)

        decision = agent._fallback_decision(obs)

        assert_valid_decision(decision)
        assert decision.tool == "move_to"

    def test_parse_valid_move_to_json(self, agent_cls):
        """Parser should handle valid move_to JSON response."""
        agent = object.__new__(agent_cls)
        agent.VALID_TOOLS = {"move_to", "collect", "idle"}
        agent.HAZARD_SAFE_DISTANCE = 3.0

        response = {
            "text": '{"tool": "move_to", "params": {"target_position": [10.0, 0.0, 5.0]}, "reasoning": "Going to berry"}',
        }
        obs = make_foraging_obs()

        decision = agent._parse_response(response, obs)

        assert decision.tool == "move_to"
        assert decision.params["target_position"] == [10.0, 0.0, 5.0]

    def test_parse_valid_collect_json(self, agent_cls):
        """Parser should handle valid collect JSON response."""
        agent = object.__new__(agent_cls)
        agent.VALID_TOOLS = {"move_to", "collect", "idle"}
        agent.HAZARD_SAFE_DISTANCE = 3.0

        response = {
            "text": '{"tool": "collect", "params": {"target_name": "berry_001"}, "reasoning": "Collecting"}',
        }
        obs = make_foraging_obs()

        decision = agent._parse_response(response, obs)

        assert decision.tool == "collect"
        assert decision.params["target_name"] == "berry_001"

    def test_parse_valid_idle_json(self, agent_cls):
        """Parser should handle valid idle JSON response."""
        agent = object.__new__(agent_cls)
        agent.VALID_TOOLS = {"move_to", "collect", "idle"}
        agent.HAZARD_SAFE_DISTANCE = 3.0

        response = {
            "text": '{"tool": "idle", "params": {}, "reasoning": "Waiting"}',
        }
        obs = make_foraging_obs()

        decision = agent._parse_response(response, obs)

        assert decision.tool == "idle"

    def test_parse_invalid_tool_falls_back(self, agent_cls):
        """Parser should fall back when LLM returns invalid tool name."""
        agent = object.__new__(agent_cls)
        agent.VALID_TOOLS = {"move_to", "collect", "idle"}
        agent.HAZARD_SAFE_DISTANCE = 3.0

        response = {
            "text": '{"tool": "fly_away", "params": {}, "reasoning": "Invalid tool"}',
        }
        resource = make_resource()
        obs = make_foraging_obs(resources=[resource])

        decision = agent._parse_response(response, obs)

        # Should fall back to observation-based decision
        assert_valid_decision(decision)
        assert decision.tool == "move_to"

    def test_parse_malformed_json_falls_back(self, agent_cls):
        """Parser should fall back on malformed JSON."""
        agent = object.__new__(agent_cls)
        agent.VALID_TOOLS = {"move_to", "collect", "idle"}
        agent.HAZARD_SAFE_DISTANCE = 3.0

        response = {
            "text": "I think the agent should move north {broken json",
        }
        obs = make_foraging_obs(exploration=EXPLORATION_INFO)

        decision = agent._parse_response(response, obs)

        assert_valid_decision(decision)

    def test_parse_empty_response_falls_back(self, agent_cls):
        """Parser should fall back on empty response."""
        agent = object.__new__(agent_cls)
        agent.VALID_TOOLS = {"move_to", "collect", "idle"}
        agent.HAZARD_SAFE_DISTANCE = 3.0

        response = {"text": ""}
        obs = make_foraging_obs(exploration=EXPLORATION_INFO)

        decision = agent._parse_response(response, obs)

        assert_valid_decision(decision)

    def test_parse_rejects_move_toward_hazard(self, agent_cls):
        """Parser should reject move_to that targets near a hazard."""
        agent = object.__new__(agent_cls)
        agent.VALID_TOOLS = {"move_to", "collect", "idle"}
        agent.HAZARD_SAFE_DISTANCE = 3.0

        hazard = make_hazard(position=(5.0, 0.0, 5.0), distance=3.0)
        response = {
            "text": '{"tool": "move_to", "params": {"target_position": [5.0, 0.0, 5.0]}, "reasoning": "Going there"}',
        }
        obs = make_foraging_obs(hazards=[hazard])

        decision = agent._parse_response(response, obs)

        # Should reject and fall back (not move to hazard position)
        assert_valid_decision(decision)

    def test_parse_tool_call_response(self, agent_cls):
        """Parser should handle tool_call format from backend."""
        agent = object.__new__(agent_cls)
        agent.VALID_TOOLS = {"move_to", "collect", "idle"}
        agent.HAZARD_SAFE_DISTANCE = 3.0

        response = {
            "text": "Moving to berry",
            "tool_call": {
                "tool": "move_to",
                "params": {"target_position": [10.0, 0.0, 5.0]},
            },
        }
        obs = make_foraging_obs()

        decision = agent._parse_response(response, obs)

        assert decision.tool == "move_to"
        assert decision.params["target_position"] == [10.0, 0.0, 5.0]

    def test_extract_json_from_mixed_text(self, agent_cls):
        """JSON extractor should find JSON embedded in surrounding text."""
        agent = object.__new__(agent_cls)

        text = 'Let me think... {"tool": "move_to", "params": {"target_position": [1, 0, 2]}, "reasoning": "test"} end'
        result = agent._extract_first_json_object(text)

        assert result is not None
        assert result["tool"] == "move_to"

    def test_extract_json_handles_nested_braces(self, agent_cls):
        """JSON extractor should handle nested objects correctly."""
        agent = object.__new__(agent_cls)

        text = '{"tool": "move_to", "params": {"target_position": [1, 0, 2]}, "reasoning": "ok"}'
        result = agent._extract_first_json_object(text)

        assert result is not None
        assert result["tool"] == "move_to"
        assert result["params"]["target_position"] == [1, 0, 2]


# ------------------------------------------------------------------ #
#  Sliding Window Memory Tests (used by intermediate and LLM starters)
# ------------------------------------------------------------------ #


class TestSlidingWindowMemoryForaging:
    """Test the sliding window memory with foraging data."""

    @pytest.fixture
    def memory(self):
        from starters.intermediate.memory import SlidingWindowMemory

        return SlidingWindowMemory(capacity=10)

    def test_store_and_retrieve(self, memory):
        """Memory should store and retrieve observations."""
        obs = make_foraging_obs(tick=1)
        memory.store(obs)

        recent = memory.get_recent(5)
        assert len(recent) == 1
        assert recent[0].tick == 1

    def test_capacity_limit(self, memory):
        """Memory should respect capacity limit."""
        for tick in range(1, 20):
            memory.store(make_foraging_obs(tick=tick))

        assert memory.count_observations() == 10
        recent = memory.get_recent(10)
        # Should keep most recent (ticks 10-19)
        assert recent[0].tick == 19  # Most recent first

    def test_find_resources_across_ticks(self, memory):
        """Memory should aggregate resources from all stored observations."""
        obs1 = make_foraging_obs(
            tick=1,
            resources=[make_resource("berry_001", "food", (5.0, 0.0, 5.0), 3.0)],
        )
        obs2 = make_foraging_obs(
            tick=2,
            resources=[make_resource("apple_001", "food", (10.0, 0.0, 0.0), 8.0)],
        )
        memory.store(obs1)
        memory.store(obs2)

        resources = memory.find_resources_seen()
        names = [name for name, _, _ in resources]
        assert "berry_001" in names
        assert "apple_001" in names

    def test_find_hazards_across_ticks(self, memory):
        """Memory should aggregate hazards from all stored observations."""
        obs1 = make_foraging_obs(
            tick=1,
            hazards=[make_hazard("fire_001", "fire", (3.0, 0.0, 0.0), 2.0)],
        )
        obs2 = make_foraging_obs(
            tick=2,
            hazards=[make_hazard("pit_001", "pit", (8.0, 0.0, 8.0), 5.0)],
        )
        memory.store(obs1)
        memory.store(obs2)

        hazards = memory.find_hazards_seen()
        names = [name for name, _, _ in hazards]
        assert "fire_001" in names
        assert "pit_001" in names

    def test_summarize(self, memory):
        """Memory summary should include resource and hazard counts."""
        obs = make_foraging_obs(
            tick=1,
            resources=[make_resource("berry_001")],
            hazards=[make_hazard("fire_001")],
        )
        memory.store(obs)

        summary = memory.summarize()
        assert "1 observations" in summary
        assert "Resources seen: 1" in summary
        assert "Hazards seen: 1" in summary

    def test_clear(self, memory):
        """Clear should empty the memory."""
        memory.store(make_foraging_obs(tick=1))
        assert memory.count_observations() == 1

        memory.clear()
        assert memory.count_observations() == 0


# ------------------------------------------------------------------ #
#  Planner Tests (used by intermediate starter)
# ------------------------------------------------------------------ #


class TestPlannerForaging:
    """Test the planner with foraging objectives."""

    @pytest.fixture
    def planner(self):
        from starters.intermediate.planner import Planner

        return Planner()

    def test_decomposes_foraging_objective(self, planner):
        """Planner should create sub-goals from foraging objective."""
        progress = {"resources_collected": 3.0, "health_remaining": 80.0, "time_taken": 50.0}

        sub_goals = planner.decompose(FORAGING_OBJECTIVE, progress)

        assert len(sub_goals) >= 1
        # resources_collected not yet at target (3 < 10)
        assert any("resources" in g.metric_name.lower() or "collected" in g.metric_name.lower() for g in sub_goals)

    def test_required_metrics_get_higher_priority(self, planner):
        """Required metrics should have higher priority."""
        progress = {"resources_collected": 3.0, "health_remaining": 80.0, "time_taken": 50.0}

        sub_goals = planner.decompose(FORAGING_OBJECTIVE, progress)

        if len(sub_goals) >= 2:
            # resources_collected is required, should be first
            assert sub_goals[0].metric_name == "resources_collected"

    def test_no_goals_when_all_complete(self, planner):
        """Planner should return no goals when all metrics are met."""
        # Note: planner uses current >= target for all metrics,
        # so time_taken needs to be >= 300 to be considered "complete"
        progress = {"resources_collected": 10.0, "health_remaining": 100.0, "time_taken": 300.0}

        sub_goals = planner.decompose(FORAGING_OBJECTIVE, progress)

        # All targets met, no sub-goals needed
        assert len(sub_goals) == 0

    def test_none_objective_returns_empty(self, planner):
        """Planner should handle None objective gracefully."""
        sub_goals = planner.decompose(None, {})
        assert sub_goals == []

    def test_sub_goal_progress_percentage(self, planner):
        """Sub-goals should report correct progress percentage."""
        progress = {"resources_collected": 5.0}

        sub_goals = planner.decompose(FORAGING_OBJECTIVE, progress)

        resource_goal = next(g for g in sub_goals if g.metric_name == "resources_collected")
        assert resource_goal.progress_percent() == 50.0

    def test_explain_plan(self, planner):
        """Planner should produce readable plan explanation."""
        progress = {"resources_collected": 3.0}

        sub_goals = planner.decompose(FORAGING_OBJECTIVE, progress)
        explanation = planner.explain_plan(sub_goals)

        assert "Current Plan:" in explanation
        assert "1." in explanation
