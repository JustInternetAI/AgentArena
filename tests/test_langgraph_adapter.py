"""Tests for the LangGraph adapter (starters/langgraph/agent.py).

All LangGraph/LangChain calls are mocked — no real API key needed.
The ``langgraph`` and ``langchain-anthropic`` packages are not required
to be installed.
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
# Mock the ``langchain_anthropic``, ``langchain_core``, and ``langgraph``
# packages so the starter can be imported without them being installed.
# ---------------------------------------------------------------------------

def _install_mock_module(name: str, **attrs) -> types.ModuleType:
    """Create and register a mock module with optional attributes."""
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules.setdefault(name, mod)
    return mod


# --- langchain_core mocks ---
_lc_core = _install_mock_module("langchain_core")

# Messages
_AIMessage = type("AIMessage", (), {
    "__init__": lambda self, **kw: self.__dict__.update(kw),
})
_HumanMessage = type("HumanMessage", (), {
    "__init__": lambda self, **kw: self.__dict__.update(kw),
})
_SystemMessage = type("SystemMessage", (), {
    "__init__": lambda self, **kw: self.__dict__.update(kw),
})

_lc_messages = _install_mock_module(
    "langchain_core.messages",
    AIMessage=_AIMessage,
    HumanMessage=_HumanMessage,
    SystemMessage=_SystemMessage,
)

# Tools
_lc_tools = _install_mock_module("langchain_core.tools")

# --- langchain_anthropic mock ---
_MockChatAnthropic = MagicMock()
_lc_anthropic = _install_mock_module(
    "langchain_anthropic",
    ChatAnthropic=_MockChatAnthropic,
)

# --- langgraph mocks ---
_lg = _install_mock_module("langgraph")
_lg_graph = _install_mock_module("langgraph.graph", END="__end__")

# StateGraph mock that returns a configurable compiled graph
_MockCompiledGraph = MagicMock()
_MockStateGraph = MagicMock()
_MockStateGraph.return_value.compile.return_value = _MockCompiledGraph
_lg_graph.StateGraph = _MockStateGraph

_lg_msg = _install_mock_module(
    "langgraph.graph.message",
    add_messages=lambda x, y: x + y,
)
_lg_prebuilt = _install_mock_module("langgraph.prebuilt", ToolNode=MagicMock())


# ---------------------------------------------------------------------------
# Import the LangGraph starter
# ---------------------------------------------------------------------------

_LANGGRAPH_STARTER = str(
    Path(__file__).resolve().parent.parent / "starters" / "langgraph"
)
if _LANGGRAPH_STARTER not in sys.path:
    sys.path.insert(0, _LANGGRAPH_STARTER)

# Force (re-)import so it picks up the mocks.
if "agent" in sys.modules:
    del sys.modules["agent"]
from agent import LangGraphAdapter  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_obs(**kwargs) -> Observation:
    defaults = {"agent_id": "test", "tick": 1, "position": (5.0, 0.0, 3.0)}
    defaults.update(kwargs)
    return Observation(**defaults)


def _mock_ai_message_with_tool_call(
    tool_name: str = "move_to",
    tool_args: dict | None = None,
    text: str = "I should move toward the berry.",
) -> _AIMessage:
    """Build a mock AIMessage containing a tool call."""
    if tool_args is None:
        tool_args = {"target_position": [10.0, 0.0, 5.0]}

    msg = _AIMessage(content=text)
    msg.tool_calls = [{"name": tool_name, "args": tool_args, "id": "call_123"}]
    msg.usage_metadata = {"input_tokens": 120, "output_tokens": 45}
    return msg


def _mock_ai_message_text_only(text: str = "Let me think about this...") -> _AIMessage:
    """Build a mock AIMessage with NO tool call."""
    msg = _AIMessage(content=text)
    msg.tool_calls = []
    msg.usage_metadata = {"input_tokens": 80, "output_tokens": 30}
    return msg


def _make_adapter(graph_result: dict | None = None) -> LangGraphAdapter:
    """Create a LangGraphAdapter with a mocked graph."""
    adapter = LangGraphAdapter(api_key="test-key")

    # Replace the compiled graph with a mock
    mock_graph = MagicMock()
    if graph_result is not None:
        mock_graph.invoke.return_value = graph_result
    adapter.graph = mock_graph
    return adapter


def _graph_result_with_tool_call(
    tool_name: str = "move_to",
    tool_args: dict | None = None,
    text: str = "Moving toward the berry.",
) -> dict:
    """Build a graph invoke result containing an AIMessage with a tool call."""
    ai_msg = _mock_ai_message_with_tool_call(tool_name, tool_args, text)
    return {"messages": [ai_msg]}


def _graph_result_text_only(text: str = "Let me think...") -> dict:
    """Build a graph invoke result with text-only AIMessage."""
    ai_msg = _mock_ai_message_text_only(text)
    return {"messages": [ai_msg]}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestLangGraphAdapterDecide:
    def test_tool_call_move_to(self):
        adapter = _make_adapter(
            _graph_result_with_tool_call(
                tool_name="move_to",
                tool_args={"target_position": [10.0, 0.0, 5.0]},
            )
        )
        decision = adapter.decide(_make_obs())

        assert decision.tool == "move_to"
        assert decision.params == {"target_position": [10.0, 0.0, 5.0]}
        assert isinstance(decision.reasoning, str)

    def test_tool_call_collect(self):
        adapter = _make_adapter(
            _graph_result_with_tool_call(
                tool_name="collect",
                tool_args={"target_name": "berry_001"},
                text="Collecting the nearby berry.",
            )
        )
        decision = adapter.decide(_make_obs())

        assert decision.tool == "collect"
        assert decision.params == {"target_name": "berry_001"}

    def test_tool_call_craft_item(self):
        adapter = _make_adapter(
            _graph_result_with_tool_call(
                tool_name="craft_item",
                tool_args={"recipe": "torch"},
            )
        )
        decision = adapter.decide(_make_obs())

        assert decision.tool == "craft_item"
        assert decision.params == {"recipe": "torch"}

    def test_tool_call_idle(self):
        adapter = _make_adapter(
            _graph_result_with_tool_call(
                tool_name="idle",
                tool_args={},
            )
        )
        decision = adapter.decide(_make_obs())

        assert decision.tool == "idle"


class TestExploreTranslation:
    def test_explore_with_targets(self):
        adapter = _make_adapter(
            _graph_result_with_tool_call(
                tool_name="explore",
                tool_args={},
            )
        )
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
        adapter = _make_adapter(
            _graph_result_with_tool_call(
                tool_name="explore",
                tool_args={},
            )
        )
        obs = _make_obs(position=(5.0, 0.0, 3.0))
        decision = adapter.decide(obs)

        # Falls back to +10 in X
        assert decision.tool == "move_to"
        assert decision.params["target_position"][0] == pytest.approx(15.0)


class TestFallbacks:
    def test_fallback_on_text_only_response(self):
        adapter = _make_adapter(_graph_result_text_only())
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

    def test_fallback_on_graph_error(self):
        adapter = _make_adapter()
        adapter.graph.invoke.side_effect = Exception("rate limit exceeded")

        obs = _make_obs()
        decision = adapter.decide(obs)

        # Should not raise, should return a valid decision
        assert decision.tool in ("move_to", "idle")
        assert isinstance(decision, Decision)

    def test_fallback_flees_hazard(self):
        adapter = _make_adapter(_graph_result_text_only())
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
    def test_trace_populated_on_tool_call(self):
        adapter = _make_adapter(_graph_result_with_tool_call())
        adapter.decide(_make_obs())

        assert adapter.last_trace is not None
        assert adapter.last_trace["parse_method"] == "tool_call"
        assert adapter.last_trace["decision"]["tool"] == "move_to"
        assert adapter.last_trace["tokens_used"] == 165  # 120 + 45

    def test_trace_populated_on_fallback(self):
        adapter = _make_adapter(_graph_result_text_only())
        adapter.decide(_make_obs())

        assert adapter.last_trace is not None
        assert adapter.last_trace["parse_method"] == "fallback_no_tool_call"

    def test_trace_populated_on_error(self):
        adapter = _make_adapter()
        adapter.graph.invoke.side_effect = RuntimeError("boom")

        adapter.decide(_make_obs())

        assert adapter.last_trace is not None
        assert adapter.last_trace["parse_method"] == "error"

    def test_trace_has_system_and_user_prompt(self):
        adapter = _make_adapter(_graph_result_with_tool_call())
        adapter.decide(_make_obs())

        assert adapter.last_trace["system_prompt"] == adapter.system_prompt
        assert "Tick: 1" in adapter.last_trace["user_prompt"]


class TestGraphInvocation:
    def test_graph_invoked_with_messages(self):
        adapter = _make_adapter(_graph_result_with_tool_call())
        adapter.decide(_make_obs(tick=42))

        adapter.graph.invoke.assert_called_once()
        call_args = adapter.graph.invoke.call_args[0][0]
        assert "messages" in call_args
        assert len(call_args["messages"]) == 2  # SystemMessage + HumanMessage

    def test_observation_in_user_message(self):
        adapter = _make_adapter(_graph_result_with_tool_call())
        adapter.decide(_make_obs(tick=42))

        call_args = adapter.graph.invoke.call_args[0][0]
        human_msg = call_args["messages"][1]
        assert "42" in human_msg.content
