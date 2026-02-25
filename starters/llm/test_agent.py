"""
Tests for the LLM Agent.

Run without Godot (no GPU or model files needed):
    pytest test_agent.py -v

Uses a mocked LLM client — tests focus on prompt construction,
JSON parsing robustness, and fallback behaviour.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Ensure the starter directory is on the path
sys.path.insert(0, str(Path(__file__).parent))
# Ensure the SDK and python/ are importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "python" / "sdk"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "python"))

from agent_arena_sdk import Decision
from agent_arena_sdk.testing import (
    assert_valid_decision,
    mock_hazard,
    mock_observation,
    mock_resource,
)

from agent import Agent


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------


def _make_mock_llm(text: str = '{"tool": "idle", "params": {}, "reasoning": "waiting"}'):
    """Create a mock LLMClient whose generate() returns *text*."""
    mock = MagicMock()
    mock.generate.return_value = {
        "text": text,
        "tool_call": None,
        "tokens_used": 10,
        "finish_reason": "stop",
    }
    return mock


def _make_agent(llm_text: str | None = None) -> Agent:
    """Create an Agent with a mocked LLM (no model file needed)."""
    mock_llm = _make_mock_llm(llm_text) if llm_text else _make_mock_llm()
    return Agent(llm_client=mock_llm)


# ---------------------------------------------------------------------------
#  Tests
# ---------------------------------------------------------------------------


class TestBuildPrompt:
    """Tests for _build_prompt() — verifies observation data reaches the prompt."""

    def test_includes_resource_info(self):
        """Prompt should mention nearby resources."""
        agent = _make_agent()
        resource = mock_resource("berry", position=(5.0, 0.0, 3.0), distance=4.2)
        obs = mock_observation(tick=1, nearby_resources=[resource])

        prompt = agent._build_prompt(obs)

        assert "berry" in prompt.lower() or resource.name in prompt

    def test_includes_hazard_info(self):
        """Prompt should mention nearby hazards."""
        agent = _make_agent()
        hazard = mock_hazard("fire", position=(2.0, 0.0, 1.0), distance=1.5)
        obs = mock_observation(tick=1, nearby_hazards=[hazard])

        prompt = agent._build_prompt(obs)

        assert "fire" in prompt.lower() or hazard.name in prompt

    def test_includes_health_and_energy(self):
        """Prompt should include current health and energy."""
        agent = _make_agent()
        obs = mock_observation(tick=1, health=42.0, energy=75.0)

        prompt = agent._build_prompt(obs)

        assert "42" in prompt
        assert "75" in prompt


class TestParseResponse:
    """Tests for _parse_response() — JSON parsing and fallback behaviour."""

    def test_parse_valid_json(self):
        """Valid JSON with known tool should be parsed correctly."""
        agent = _make_agent()
        response = {
            "text": '{"tool": "move_to", "params": {"target_position": [5, 0, 3]}, "reasoning": "going for berry"}',
        }
        obs = mock_observation(tick=1)

        decision = agent._parse_response(response, obs)

        assert decision.tool == "move_to"
        assert decision.params["target_position"] == [5, 0, 3]

    def test_parse_idle_response(self):
        """Idle tool response should be parsed correctly."""
        agent = _make_agent()
        response = {
            "text": '{"tool": "idle", "params": {}, "reasoning": "waiting"}',
        }
        obs = mock_observation(tick=1)

        decision = agent._parse_response(response, obs)

        assert decision.tool == "idle"

    def test_parse_invalid_tool_falls_back(self):
        """Invalid tool name should trigger observation-based fallback."""
        agent = _make_agent()
        response = {
            "text": '{"tool": "fly_away", "params": {}, "reasoning": "invalid"}',
        }
        resource = mock_resource("berry", position=(5.0, 0.0, 3.0), distance=4.2)
        obs = mock_observation(tick=1, nearby_resources=[resource])

        decision = agent._parse_response(response, obs)

        assert_valid_decision(decision)
        # Fallback should use observation data to make a useful decision
        assert decision.tool == "move_to"

    def test_parse_malformed_json_falls_back(self):
        """Malformed JSON should trigger fallback."""
        agent = _make_agent()
        response = {
            "text": "I think the agent should move {broken json",
        }
        obs = mock_observation(tick=1)

        decision = agent._parse_response(response, obs)

        assert_valid_decision(decision)

    def test_parse_empty_response_falls_back(self):
        """Empty response should trigger fallback."""
        agent = _make_agent()
        response = {"text": ""}
        obs = mock_observation(tick=1)

        decision = agent._parse_response(response, obs)

        assert_valid_decision(decision)


class TestFallbackDecision:
    """Tests for _fallback_decision() — sensible defaults from observation."""

    def test_flees_nearby_hazard(self):
        """Fallback should flee from a nearby hazard."""
        agent = _make_agent()
        hazard = mock_hazard("fire", position=(1.0, 0.0, 0.0), distance=1.5)
        obs = mock_observation(tick=1, nearby_hazards=[hazard])

        decision = agent._fallback_decision(obs)

        assert decision.tool == "move_to"
        target = decision.params["target_position"]
        # Should move away from hazard
        from agent_arena_sdk.testing import distance_between

        assert distance_between(target, hazard.position) > hazard.distance

    def test_moves_toward_resource(self):
        """Fallback should move toward nearest resource."""
        agent = _make_agent()
        resource = mock_resource("berry", position=(10.0, 0.0, 5.0), distance=8.0)
        obs = mock_observation(tick=1, nearby_resources=[resource])

        decision = agent._fallback_decision(obs)

        assert decision.tool == "move_to"
        assert decision.params["target_position"] == list(resource.position)

    def test_moves_when_nothing_visible(self):
        """Fallback should still produce a move_to even with empty observations."""
        agent = _make_agent()
        obs = mock_observation(tick=1)

        decision = agent._fallback_decision(obs)

        # The fallback should still return a valid decision (move to explore)
        assert_valid_decision(decision)
        assert decision.tool == "move_to"


class TestExtractJson:
    """Tests for _extract_first_json_object() — JSON extraction from text."""

    def test_extracts_embedded_json(self):
        """Should extract JSON from surrounding text."""
        agent = _make_agent()
        text = 'Here is my decision: {"tool": "move_to", "params": {"target_position": [1, 0, 2]}} done.'

        result = agent._extract_first_json_object(text)

        assert result is not None
        assert result["tool"] == "move_to"

    def test_returns_none_for_no_json(self):
        """Should return None when no JSON is present."""
        agent = _make_agent()

        result = agent._extract_first_json_object("no json here at all")

        assert result is None

    def test_handles_truncated_json(self):
        """Should return None for truncated JSON."""
        agent = _make_agent()

        result = agent._extract_first_json_object('{"tool": "move_to", "params":')

        assert result is None
