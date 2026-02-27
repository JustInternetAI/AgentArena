"""Tests for FrameworkAdapter base class."""

import pytest

from agent_arena_sdk import Decision, Observation, ToolSchema
from agent_arena_sdk.adapters.base import FrameworkAdapter
from agent_arena_sdk.schemas.observation import (
    ExplorationInfo,
    ExploreTarget,
    HazardInfo,
    ItemInfo,
    ResourceInfo,
    StationInfo,
    ToolResult,
)
from agent_arena_sdk.schemas.objective import MetricDefinition, Objective


class ConcreteAdapter(FrameworkAdapter):
    """Minimal concrete adapter for testing base class methods."""

    def decide(self, obs: Observation) -> Decision:
        return Decision.idle("test")


def _make_obs(**kwargs) -> Observation:
    """Helper to create test observations with defaults."""
    defaults = {"agent_id": "test", "tick": 1, "position": (0.0, 0.0, 0.0)}
    defaults.update(kwargs)
    return Observation(**defaults)


# ---------------------------------------------------------------------------
# FrameworkAdapter ABC
# ---------------------------------------------------------------------------


class TestFrameworkAdapterABC:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            FrameworkAdapter()  # type: ignore[abstract]

    def test_requires_decide_implementation(self):
        class IncompleteAdapter(FrameworkAdapter):
            pass

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteAdapter()  # type: ignore[abstract]

    def test_concrete_adapter_works(self):
        adapter = ConcreteAdapter()
        obs = _make_obs()
        decision = adapter.decide(obs)
        assert decision.tool == "idle"


# ---------------------------------------------------------------------------
# format_observation
# ---------------------------------------------------------------------------


class TestFormatObservation:
    def test_minimal_observation(self):
        adapter = ConcreteAdapter()
        text = adapter.format_observation(_make_obs())
        assert "Tick: 1" in text
        assert "Position:" in text
        assert "Health: 100" in text
        assert "Energy: 100" in text
        assert "Resources: None" in text
        assert "Hazards: None" in text
        assert "Stations: None" in text
        assert "Inventory: Empty" in text

    def test_with_resources(self):
        adapter = ConcreteAdapter()
        obs = _make_obs(
            nearby_resources=[
                ResourceInfo(
                    name="berry_1", type="berry", position=(5.0, 0.0, 3.0), distance=5.8
                ),
                ResourceInfo(
                    name="wood_1", type="wood", position=(8.0, 0.0, 1.0), distance=8.1
                ),
            ]
        )
        text = adapter.format_observation(obs)
        assert "berry_1" in text
        assert "berry" in text
        assert "5.8" in text
        assert "wood_1" in text

    def test_resources_limited_to_5(self):
        adapter = ConcreteAdapter()
        resources = [
            ResourceInfo(
                name=f"r_{i}", type="berry", position=(float(i), 0.0, 0.0), distance=float(i)
            )
            for i in range(10)
        ]
        obs = _make_obs(nearby_resources=resources)
        text = adapter.format_observation(obs)
        assert "r_4" in text
        assert "r_5" not in text

    def test_with_hazards(self):
        adapter = ConcreteAdapter()
        obs = _make_obs(
            nearby_hazards=[
                HazardInfo(
                    name="fire_1", type="fire", position=(2.0, 0.0, 1.0), distance=2.2
                )
            ]
        )
        text = adapter.format_observation(obs)
        assert "fire_1" in text
        assert "fire" in text
        assert "2.2" in text

    def test_with_stations(self):
        adapter = ConcreteAdapter()
        obs = _make_obs(
            nearby_stations=[
                StationInfo(
                    name="bench_1",
                    type="workbench",
                    position=(3.0, 0.0, 4.0),
                    distance=5.0,
                )
            ]
        )
        text = adapter.format_observation(obs)
        assert "bench_1" in text
        assert "workbench" in text

    def test_inventory_dict_format(self):
        adapter = ConcreteAdapter()
        obs = _make_obs(custom={"inventory": {"wood": 3, "stone": 1}})
        text = adapter.format_observation(obs)
        assert "wood" in text
        assert "3" in text
        assert "stone" in text

    def test_inventory_iteminfo_format(self):
        adapter = ConcreteAdapter()
        obs = _make_obs(
            inventory=[ItemInfo(id="i1", name="torch", quantity=2)]
        )
        text = adapter.format_observation(obs)
        assert "torch" in text
        assert "x2" in text

    def test_exploration_targets(self):
        adapter = ConcreteAdapter()
        obs = _make_obs(
            exploration=ExplorationInfo(
                exploration_percentage=45.0,
                total_cells=100,
                seen_cells=45,
                frontiers_by_direction={"north": 10.0},
                explore_targets=[
                    ExploreTarget(
                        direction="north", distance=10.0, position=(0.0, 0.0, 10.0)
                    )
                ],
            )
        )
        text = adapter.format_observation(obs)
        assert "45.0%" in text
        assert "north" in text

    def test_exploration_hint_when_no_resources(self):
        adapter = ConcreteAdapter()
        obs = _make_obs(
            nearby_resources=[],
            exploration=ExplorationInfo(
                exploration_percentage=30.0,
                total_cells=100,
                seen_cells=30,
                frontiers_by_direction={},
                explore_targets=[
                    ExploreTarget(
                        direction="east", distance=12.0, position=(12.0, 0.0, 0.0)
                    )
                ],
            ),
        )
        text = adapter.format_observation(obs)
        assert "No resources visible" in text
        assert "12.0" in text

    def test_exploration_hint_no_targets(self):
        adapter = ConcreteAdapter()
        obs = _make_obs(nearby_resources=[])
        text = adapter.format_observation(obs)
        assert "No resources visible" in text
        assert "unexplored area" in text

    def test_no_hint_when_resources_present(self):
        adapter = ConcreteAdapter()
        obs = _make_obs(
            nearby_resources=[
                ResourceInfo(
                    name="r1", type="berry", position=(5.0, 0.0, 0.0), distance=5.0
                )
            ]
        )
        text = adapter.format_observation(obs)
        assert "No resources visible" not in text

    def test_objective_included(self):
        adapter = ConcreteAdapter()
        obs = _make_obs(
            objective=Objective(
                description="Collect 10 resources",
                success_metrics={"resources_collected": MetricDefinition(target=10.0)},
            ),
            current_progress={"resources_collected": 4.0},
        )
        text = adapter.format_observation(obs)
        assert "Collect 10 resources" in text
        assert "resources_collected" in text
        assert "4" in text

    def test_last_tool_result_success(self):
        adapter = ConcreteAdapter()
        obs = _make_obs(
            last_tool_result=ToolResult(tool="move_to", success=True)
        )
        text = adapter.format_observation(obs)
        assert "move_to" in text
        assert "OK" in text

    def test_last_tool_result_failure(self):
        adapter = ConcreteAdapter()
        obs = _make_obs(
            last_tool_result=ToolResult(
                tool="collect", success=False, error="OUT_OF_RANGE"
            )
        )
        text = adapter.format_observation(obs)
        assert "collect" in text
        assert "FAILED" in text
        assert "OUT_OF_RANGE" in text


# ---------------------------------------------------------------------------
# get_action_tools
# ---------------------------------------------------------------------------


class TestGetActionTools:
    def test_returns_tool_schemas(self):
        adapter = ConcreteAdapter()
        tools = adapter.get_action_tools()
        assert isinstance(tools, list)
        assert all(isinstance(t, ToolSchema) for t in tools)

    def test_canonical_tool_names(self):
        adapter = ConcreteAdapter()
        names = {t.name for t in adapter.get_action_tools()}
        assert names == {"move_to", "collect", "craft_item", "explore", "idle"}

    def test_descriptions_say_ends_turn(self):
        adapter = ConcreteAdapter()
        for tool in adapter.get_action_tools():
            assert "ends your turn" in tool.description.lower(), (
                f"Tool {tool.name} description missing 'ends your turn'"
            )

    def test_anthropic_format_conversion(self):
        adapter = ConcreteAdapter()
        for tool in adapter.get_action_tools():
            fmt = tool.to_anthropic_format()
            assert "name" in fmt
            assert "description" in fmt
            assert "input_schema" in fmt
            assert fmt["name"] == tool.name

    def test_openai_format_conversion(self):
        adapter = ConcreteAdapter()
        for tool in adapter.get_action_tools():
            fmt = tool.to_openai_format()
            assert fmt["type"] == "function"
            assert fmt["function"]["name"] == tool.name

    def test_move_to_has_target_position(self):
        adapter = ConcreteAdapter()
        tools = {t.name: t for t in adapter.get_action_tools()}
        move_to = tools["move_to"]
        assert "target_position" in move_to.parameters["properties"]
        assert "target_position" in move_to.parameters["required"]

    def test_collect_has_target_name(self):
        adapter = ConcreteAdapter()
        tools = {t.name: t for t in adapter.get_action_tools()}
        collect = tools["collect"]
        assert "target_name" in collect.parameters["properties"]

    def test_craft_item_has_recipe(self):
        adapter = ConcreteAdapter()
        tools = {t.name: t for t in adapter.get_action_tools()}
        craft = tools["craft_item"]
        assert "recipe" in craft.parameters["properties"]


# ---------------------------------------------------------------------------
# fallback_decision
# ---------------------------------------------------------------------------


class TestFallbackDecision:
    def test_flee_hazard(self):
        adapter = ConcreteAdapter()
        obs = _make_obs(
            nearby_hazards=[
                HazardInfo(
                    name="fire", type="fire", position=(1.0, 0.0, 0.0), distance=1.0
                )
            ]
        )
        decision = adapter.fallback_decision(obs)
        assert decision.tool == "move_to"
        # Should move away from hazard at x=1 (i.e. negative X direction)
        assert decision.params["target_position"][0] < 0

    def test_hazard_far_away_not_fleeing(self):
        adapter = ConcreteAdapter()
        obs = _make_obs(
            nearby_hazards=[
                HazardInfo(
                    name="fire", type="fire", position=(10.0, 0.0, 0.0), distance=10.0
                )
            ]
        )
        decision = adapter.fallback_decision(obs)
        # Hazard at 10.0 > 3.0 threshold, should not flee
        assert decision.tool == "move_to"
        # With no resources, goes to +X direction
        assert decision.params["target_position"][0] > 0

    def test_collect_nearest_resource(self):
        adapter = ConcreteAdapter()
        obs = _make_obs(
            nearby_resources=[
                ResourceInfo(
                    name="berry", type="berry", position=(5.0, 0.0, 3.0), distance=5.8
                ),
                ResourceInfo(
                    name="wood", type="wood", position=(2.0, 0.0, 1.0), distance=2.2
                ),
            ]
        )
        decision = adapter.fallback_decision(obs)
        assert decision.tool == "move_to"
        # Should pick wood (closer at 2.2)
        assert decision.params["target_position"] == [2.0, 0.0, 1.0]

    def test_explore_when_nothing_visible(self):
        adapter = ConcreteAdapter()
        obs = _make_obs(
            exploration=ExplorationInfo(
                exploration_percentage=20.0,
                total_cells=100,
                seen_cells=20,
                frontiers_by_direction={},
                explore_targets=[
                    ExploreTarget(
                        direction="east", distance=15.0, position=(15.0, 0.0, 0.0)
                    )
                ],
            )
        )
        decision = adapter.fallback_decision(obs)
        assert decision.tool == "move_to"
        assert decision.params["target_position"] == [15.0, 0.0, 0.0]

    def test_default_move_when_no_data(self):
        adapter = ConcreteAdapter()
        obs = _make_obs()
        decision = adapter.fallback_decision(obs)
        assert decision.tool == "move_to"
        # Moves +10 in X from position (0, 0, 0)
        assert decision.params["target_position"][0] == pytest.approx(10.0)

    def test_hazard_priority_over_resources(self):
        adapter = ConcreteAdapter()
        obs = _make_obs(
            nearby_hazards=[
                HazardInfo(
                    name="fire", type="fire", position=(1.0, 0.0, 0.0), distance=1.0
                )
            ],
            nearby_resources=[
                ResourceInfo(
                    name="berry", type="berry", position=(5.0, 0.0, 0.0), distance=5.0
                )
            ],
        )
        decision = adapter.fallback_decision(obs)
        # Should flee (hazard at 1.0 < 3.0), not go toward resource
        assert decision.params["target_position"][0] < 0


# ---------------------------------------------------------------------------
# AgentArena.run() duck-typing
# ---------------------------------------------------------------------------


class TestResolveCallback:
    def test_callable_accepted(self):
        from agent_arena_sdk.arena import _resolve_callback

        def my_decide(obs: Observation) -> Decision:
            return Decision.idle()

        cb = _resolve_callback(my_decide)
        assert cb is my_decide

    def test_adapter_accepted(self):
        from agent_arena_sdk.arena import _resolve_callback

        adapter = ConcreteAdapter()
        cb = _resolve_callback(adapter)
        assert cb == adapter.decide

    def test_object_with_decide_accepted(self):
        from agent_arena_sdk.arena import _resolve_callback

        class PlainAgent:
            def decide(self, obs: Observation) -> Decision:
                return Decision.idle()

        agent = PlainAgent()
        cb = _resolve_callback(agent)
        assert cb == agent.decide

    def test_non_callable_rejected(self):
        from agent_arena_sdk.arena import _resolve_callback

        with pytest.raises(TypeError, match="callable"):
            _resolve_callback(42)

    def test_string_rejected(self):
        from agent_arena_sdk.arena import _resolve_callback

        with pytest.raises(TypeError, match="callable"):
            _resolve_callback("not a callback")
