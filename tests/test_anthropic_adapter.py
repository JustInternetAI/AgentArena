"""Tests for the Anthropic/Claude adapter (starters/claude/agent.py).

All Anthropic API calls are mocked — no real API key needed.
The ``anthropic`` package is not required to be installed.
"""

import importlib
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agent_arena_sdk import Decision, Observation
from agent_arena_sdk.schemas.observation import (
    ExplorationInfo,
    ExploreTarget,
    HazardInfo,
    ResourceInfo,
)

# ---------------------------------------------------------------------------
# Mock the ``anthropic`` package so the starter can be imported without it
# being installed.  We create a fake module with a MagicMock ``Anthropic``
# class.
# ---------------------------------------------------------------------------
_anthropic_mock = types.ModuleType("anthropic")
_anthropic_mock.Anthropic = MagicMock  # type: ignore[attr-defined]
sys.modules.setdefault("anthropic", _anthropic_mock)

# The Claude starter lives outside the installed package.
_CLAUDE_STARTER = str(Path(__file__).resolve().parent.parent / "starters" / "claude")
if _CLAUDE_STARTER not in sys.path:
    sys.path.insert(0, _CLAUDE_STARTER)

# Force (re-)import so it picks up the mock.
if "agent" in sys.modules:
    importlib.reload(sys.modules["agent"])
from agent import ClaudeAdapter  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_obs(**kwargs) -> Observation:
    defaults = {"agent_id": "test", "tick": 1, "position": (5.0, 0.0, 3.0)}
    defaults.update(kwargs)
    return Observation(**defaults)


def _mock_tool_use_response(
    tool_name: str = "move_to",
    tool_input: dict | None = None,
    text: str = "I should move toward the berry.",
) -> MagicMock:
    """Build a mock Anthropic response containing a tool_use block."""
    if tool_input is None:
        tool_input = {"target_position": [10.0, 0.0, 5.0]}

    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = text

    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = tool_name
    tool_block.input = tool_input

    response = MagicMock()
    response.content = [text_block, tool_block]
    response.stop_reason = "tool_use"
    response.usage.input_tokens = 120
    response.usage.output_tokens = 45
    return response


def _mock_text_only_response(text: str = "Let me think about this...") -> MagicMock:
    """Build a mock Anthropic response with NO tool_use block."""
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = text

    response = MagicMock()
    response.content = [text_block]
    response.stop_reason = "end_turn"
    response.usage.input_tokens = 80
    response.usage.output_tokens = 30
    return response


def _make_adapter(mock_client: MagicMock | None = None) -> ClaudeAdapter:
    """Create a ClaudeAdapter with a mocked Anthropic client."""
    adapter = ClaudeAdapter(api_key="test-key")
    if mock_client is not None:
        adapter.client = mock_client
    return adapter


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestClaudeAdapterDecide:
    def test_tool_use_move_to(self):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_tool_use_response(
            tool_name="move_to",
            tool_input={"target_position": [10.0, 0.0, 5.0]},
        )

        adapter = _make_adapter(mock_client)
        decision = adapter.decide(_make_obs())

        assert decision.tool == "move_to"
        assert decision.params == {"target_position": [10.0, 0.0, 5.0]}
        assert isinstance(decision.reasoning, str)

    def test_tool_use_collect(self):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_tool_use_response(
            tool_name="collect",
            tool_input={"target_name": "berry_001"},
            text="Collecting the nearby berry.",
        )

        adapter = _make_adapter(mock_client)
        decision = adapter.decide(_make_obs())

        assert decision.tool == "collect"
        assert decision.params == {"target_name": "berry_001"}

    def test_tool_use_craft_item(self):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_tool_use_response(
            tool_name="craft_item",
            tool_input={"recipe": "torch"},
        )

        adapter = _make_adapter(mock_client)
        decision = adapter.decide(_make_obs())

        assert decision.tool == "craft_item"
        assert decision.params == {"recipe": "torch"}

    def test_tool_use_idle(self):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_tool_use_response(
            tool_name="idle",
            tool_input={},
        )

        adapter = _make_adapter(mock_client)
        decision = adapter.decide(_make_obs())

        assert decision.tool == "idle"


class TestExploreTranslation:
    def test_explore_with_targets(self):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_tool_use_response(
            tool_name="explore",
            tool_input={},
        )

        adapter = _make_adapter(mock_client)
        obs = _make_obs(
            exploration=ExplorationInfo(
                exploration_percentage=25.0,
                total_cells=100,
                seen_cells=25,
                frontiers_by_direction={},
                explore_targets=[
                    ExploreTarget(
                        direction="north",
                        distance=12.0,
                        position=(0.0, 0.0, 12.0),
                    )
                ],
            )
        )
        decision = adapter.decide(obs)

        # explore is translated to move_to
        assert decision.tool == "move_to"
        assert decision.params["target_position"] == [0.0, 0.0, 12.0]
        assert "north" in (decision.reasoning or "").lower()

    def test_explore_without_targets(self):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_tool_use_response(
            tool_name="explore",
            tool_input={},
        )

        adapter = _make_adapter(mock_client)
        obs = _make_obs(position=(5.0, 0.0, 3.0))
        decision = adapter.decide(obs)

        # Falls back to +10 in X
        assert decision.tool == "move_to"
        assert decision.params["target_position"][0] == pytest.approx(15.0)


class TestFallbacks:
    def test_fallback_on_text_only_response(self):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_text_only_response()

        adapter = _make_adapter(mock_client)
        obs = _make_obs(
            nearby_resources=[
                ResourceInfo(
                    name="berry", type="berry", position=(8.0, 0.0, 4.0), distance=3.2
                )
            ]
        )
        decision = adapter.decide(obs)

        # Fallback should go to nearest resource
        assert decision.tool == "move_to"
        assert decision.params["target_position"] == [8.0, 0.0, 4.0]

    def test_fallback_on_api_error(self):
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("rate limit exceeded")

        adapter = _make_adapter(mock_client)
        obs = _make_obs()
        decision = adapter.decide(obs)

        # Should not raise, should return a valid decision
        assert decision.tool in ("move_to", "idle")
        assert isinstance(decision, Decision)

    def test_fallback_flees_hazard(self):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_text_only_response()

        adapter = _make_adapter(mock_client)
        obs = _make_obs(
            position=(0.0, 0.0, 0.0),
            nearby_hazards=[
                HazardInfo(
                    name="fire", type="fire", position=(1.0, 0.0, 0.0), distance=1.0
                )
            ],
        )
        decision = adapter.decide(obs)

        assert decision.tool == "move_to"
        # Should move away from hazard (negative X)
        assert decision.params["target_position"][0] < 0


class TestTraceRecording:
    def test_trace_populated_on_tool_use(self):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_tool_use_response()

        adapter = _make_adapter(mock_client)
        adapter.decide(_make_obs())

        assert adapter.last_trace is not None
        assert adapter.last_trace["parse_method"] == "tool_use"
        assert adapter.last_trace["decision"]["tool"] == "move_to"
        assert adapter.last_trace["tokens_used"] == 165  # 120 + 45

    def test_trace_populated_on_fallback(self):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_text_only_response()

        adapter = _make_adapter(mock_client)
        adapter.decide(_make_obs())

        assert adapter.last_trace is not None
        assert adapter.last_trace["parse_method"] == "fallback_no_tool_use"

    def test_trace_populated_on_error(self):
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = RuntimeError("boom")

        adapter = _make_adapter(mock_client)
        adapter.decide(_make_obs())

        assert adapter.last_trace is not None
        assert adapter.last_trace["parse_method"] == "error"

    def test_trace_has_system_and_user_prompt(self):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_tool_use_response()

        adapter = _make_adapter(mock_client)
        adapter.decide(_make_obs())

        assert adapter.last_trace["system_prompt"] == adapter.system_prompt
        assert "Tick: 1" in adapter.last_trace["user_prompt"]


class TestAPICallParameters:
    def test_messages_create_called_with_tools(self):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_tool_use_response()

        adapter = _make_adapter(mock_client)
        adapter.decide(_make_obs())

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["model"] == "claude-sonnet-4-20250514"
        assert call_kwargs["max_tokens"] == 1024
        assert isinstance(call_kwargs["tools"], list)
        assert len(call_kwargs["tools"]) == 5  # move_to, collect, craft_item, explore, idle

        # Verify tool names
        tool_names = {t["name"] for t in call_kwargs["tools"]}
        assert tool_names == {"move_to", "collect", "craft_item", "explore", "idle"}

    def test_observation_is_user_message(self):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_tool_use_response()

        adapter = _make_adapter(mock_client)
        adapter.decide(_make_obs(tick=42))

        call_kwargs = mock_client.messages.create.call_args.kwargs
        messages = call_kwargs["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert "Tick: 42" in messages[0]["content"]

    def test_custom_model(self):
        adapter = ClaudeAdapter(model="claude-haiku-4-5-20251001", api_key="k")

        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_tool_use_response()
        adapter.client = mock_client

        adapter.decide(_make_obs())

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["model"] == "claude-haiku-4-5-20251001"
