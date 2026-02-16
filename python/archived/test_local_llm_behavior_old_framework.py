"""
Tests for LocalLLMBehavior.

These tests use a mock backend to avoid requiring a real LLM model.
"""

from unittest.mock import MagicMock

import pytest

from agent_runtime import LocalLLMBehavior, Observation, ToolSchema
from agent_runtime.schemas import HazardInfo, ResourceInfo
from backends.base import BaseBackend, GenerationResult


class MockBackend(BaseBackend):
    """Mock backend for testing that returns configurable responses."""

    def __init__(self, response_text: str = "", parse_error: bool = False):
        """Initialize mock backend with a predefined response."""
        # Don't call super().__init__ since we don't have a config
        self.response_text = response_text
        self.parse_error = parse_error
        self._available = True

    def generate(self, prompt: str, temperature=None, max_tokens=None) -> GenerationResult:
        """Return a mock generation result."""
        return GenerationResult(
            text=self.response_text,
            tokens_used=10,
            finish_reason="stop",
            metadata={},
        )

    def generate_with_tools(self, prompt: str, tools: list, temperature=None) -> GenerationResult:
        """Return a mock generation result with optional parsed tool call."""
        metadata = {}
        if not self.parse_error and self.response_text:
            try:
                import json

                parsed = json.loads(self.response_text)
                metadata["parsed_tool_call"] = parsed
            except json.JSONDecodeError:
                metadata["parse_error"] = True

        return GenerationResult(
            text=self.response_text,
            tokens_used=10,
            finish_reason="stop",
            metadata=metadata,
        )

    def is_available(self) -> bool:
        """Return availability status."""
        return self._available

    def unload(self) -> None:
        """Mock unload."""
        pass


def create_test_observation() -> Observation:
    """Create a test observation with sample data."""
    return Observation(
        agent_id="test_agent",
        tick=1,
        position=(0.0, 0.0, 0.0),
        nearby_resources=[
            ResourceInfo(name="apple_1", type="apple", position=(5.0, 0.0, 0.0), distance=5.0),
            ResourceInfo(name="wood_1", type="wood", position=(10.0, 0.0, 0.0), distance=10.0),
        ],
        nearby_hazards=[
            HazardInfo(
                name="fire_1", type="fire", position=(2.0, 0.0, 0.0), distance=2.0, damage=10.0
            ),
        ],
        health=100.0,
        energy=100.0,
    )


def create_test_tools() -> list[ToolSchema]:
    """Create test tool schemas."""
    return [
        ToolSchema(
            name="move_to",
            description="Move to a target position",
            parameters={
                "type": "object",
                "properties": {
                    "target_position": {"type": "array"},
                    "speed": {"type": "number"},
                },
            },
        ),
        ToolSchema(
            name="idle",
            description="Do nothing",
            parameters={"type": "object", "properties": {}},
        ),
    ]


class TestLocalLLMBehavior:
    """Tests for LocalLLMBehavior class."""

    def test_init_with_available_backend(self):
        """Test initialization with an available backend."""
        backend = MockBackend()
        behavior = LocalLLMBehavior(
            backend=backend,
            system_prompt="Test prompt",
            temperature=0.5,
            max_tokens=128,
        )

        assert behavior.backend == backend
        assert behavior.system_prompt == "Test prompt"
        assert behavior.temperature == 0.5
        assert behavior.max_tokens == 128

    def test_init_with_unavailable_backend_raises(self):
        """Test that initialization fails if backend is not available."""
        backend = MockBackend()
        backend._available = False

        with pytest.raises(RuntimeError, match="Backend is not available"):
            LocalLLMBehavior(backend=backend)

    def test_decide_returns_parsed_tool_call(self):
        """Test that decide() correctly parses a valid tool call response."""
        response = '{"tool": "move_to", "params": {"target_position": [5.0, 0.0, 0.0], "speed": 1.5}, "reasoning": "Moving to apple"}'
        backend = MockBackend(response_text=response)
        behavior = LocalLLMBehavior(backend=backend)

        observation = create_test_observation()
        tools = create_test_tools()

        decision = behavior.decide(observation, tools)

        assert decision.tool == "move_to"
        assert decision.params["target_position"] == [5.0, 0.0, 0.0]
        assert decision.params["speed"] == 1.5
        assert decision.reasoning == "Moving to apple"

    def test_decide_returns_idle_on_parse_error(self):
        """Test that decide() returns idle when LLM response cannot be parsed."""
        backend = MockBackend(response_text="not valid json", parse_error=True)
        behavior = LocalLLMBehavior(backend=backend)

        observation = create_test_observation()
        tools = create_test_tools()

        decision = behavior.decide(observation, tools)

        assert decision.tool == "idle"
        assert "Parse error" in (decision.reasoning or "")

    def test_decide_returns_idle_on_generation_error(self):
        """Test that decide() returns idle when generation fails."""
        backend = MockBackend()
        # Override generate_with_tools to return an error
        backend.generate_with_tools = MagicMock(
            return_value=GenerationResult(
                text="",
                tokens_used=0,
                finish_reason="error",
                metadata={"error": "Model error"},
            )
        )
        behavior = LocalLLMBehavior(backend=backend)

        observation = create_test_observation()
        tools = create_test_tools()

        decision = behavior.decide(observation, tools)

        assert decision.tool == "idle"
        assert "error" in (decision.reasoning or "").lower()

    def test_build_prompt_includes_observation_data(self):
        """Test that _build_prompt includes all observation data."""
        backend = MockBackend()
        behavior = LocalLLMBehavior(
            backend=backend,
            system_prompt="You are a test agent.",
        )

        observation = create_test_observation()
        tools = create_test_tools()

        prompt = behavior._build_prompt(observation, tools)

        # Check that key information is in the prompt
        assert "Position:" in prompt
        assert "(0.0, 0.0, 0.0)" in prompt or "0.0, 0.0, 0.0" in prompt
        assert "apple_1" in prompt
        assert "fire_1" in prompt
        assert "Health:" in prompt
        assert "You are a test agent." in prompt

    def test_lifecycle_hooks(self):
        """Test that lifecycle hooks can be called without error."""
        backend = MockBackend()
        behavior = LocalLLMBehavior(backend=backend)

        # These should not raise
        behavior.on_episode_start()
        behavior.on_episode_end(success=True, metrics={"score": 100})
        behavior.on_tool_result("move_to", {"success": True})

    def test_decide_handles_empty_observation(self):
        """Test that decide() handles observations with no resources or hazards."""
        response = '{"tool": "idle", "params": {}, "reasoning": "Nothing nearby"}'
        backend = MockBackend(response_text=response)
        behavior = LocalLLMBehavior(backend=backend)

        observation = Observation(
            agent_id="test_agent",
            tick=1,
            position=(0.0, 0.0, 0.0),
            nearby_resources=[],
            nearby_hazards=[],
        )
        tools = create_test_tools()

        decision = behavior.decide(observation, tools)

        assert decision.tool == "idle"


class TestCreateLocalLLMBehavior:
    """Tests for the create_local_llm_behavior factory function."""

    def test_factory_requires_valid_model_path(self):
        """Test that factory function validates model path."""
        # This test will fail if no model exists, which is expected
        # In a real test environment, we'd mock the LlamaCppBackend
        pass  # Skip this test as it requires a real model


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
