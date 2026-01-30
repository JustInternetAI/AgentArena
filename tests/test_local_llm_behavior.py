"""
Tests for LocalLLMBehavior.
"""

import json
from unittest.mock import Mock, patch

import pytest

from agent_runtime.local_llm_behavior import LocalLLMBehavior, create_local_llm_behavior
from agent_runtime.schemas import AgentDecision, HazardInfo, Observation, ResourceInfo, ToolSchema
from backends.base import BackendConfig, GenerationResult


class MockBackend:
    """Mock backend for testing LocalLLMBehavior."""

    def __init__(self, config: BackendConfig):
        self.config = config
        self.available = True
        self.generate_calls = []
        self.generate_with_tools_calls = []
        self.mock_response = None  # Can be set to override default response

    def is_available(self) -> bool:
        return self.available

    def generate(self, prompt: str, temperature=None, max_tokens=None) -> GenerationResult:
        self.generate_calls.append((prompt, temperature, max_tokens))
        if self.mock_response:
            return self.mock_response
        return GenerationResult(
            text='{"tool": "idle", "params": {}, "reasoning": "Test decision"}',
            tokens_used=50,
            finish_reason="stop",
            metadata={},
        )

    def generate_with_tools(
        self, prompt: str, tools: list[dict], temperature=None
    ) -> GenerationResult:
        self.generate_with_tools_calls.append((prompt, tools, temperature))
        if self.mock_response:
            return self.mock_response
        return GenerationResult(
            text='{"tool": "idle", "params": {}, "reasoning": "Test decision"}',
            tokens_used=50,
            finish_reason="stop",
            metadata={},
        )

    def unload(self) -> None:
        pass


class TestLocalLLMBehavior:
    """Tests for LocalLLMBehavior class."""

    def test_initialization_with_available_backend(self):
        """Test that LocalLLMBehavior can be initialized with an available backend."""
        config = BackendConfig(model_path="test_model.gguf")
        backend = MockBackend(config)

        behavior = LocalLLMBehavior(backend=backend, system_prompt="Test prompt")

        assert behavior.backend is backend
        assert behavior.system_prompt == "Test prompt"
        assert behavior.memory.capacity == 10

    def test_initialization_with_unavailable_backend(self):
        """Test that LocalLLMBehavior raises error if backend is unavailable."""
        config = BackendConfig(model_path="test_model.gguf")
        backend = MockBackend(config)
        backend.available = False

        with pytest.raises(RuntimeError, match="is not available"):
            LocalLLMBehavior(backend=backend)

    def test_initialization_with_custom_memory_capacity(self):
        """Test initialization with custom memory capacity."""
        config = BackendConfig(model_path="test_model.gguf")
        backend = MockBackend(config)

        behavior = LocalLLMBehavior(backend=backend, memory_capacity=20)

        assert behavior.memory.capacity == 20

    def test_initialization_with_temperature_and_max_tokens(self):
        """Test initialization with custom temperature and max tokens."""
        config = BackendConfig(model_path="test_model.gguf")
        backend = MockBackend(config)

        behavior = LocalLLMBehavior(
            backend=backend, temperature=0.8, max_tokens=512
        )

        assert behavior.temperature == 0.8
        assert behavior.max_tokens == 512

    def test_decide_calls_backend_with_tools(self):
        """Test that decide() calls backend.generate_with_tools()."""
        config = BackendConfig(model_path="test_model.gguf")
        backend = MockBackend(config)
        behavior = LocalLLMBehavior(backend=backend)

        observation = Observation(
            agent_id="test_agent",
            tick=1,
            position=(0.0, 0.0, 0.0),
        )

        tools = [
            ToolSchema(
                name="move_to",
                description="Move to a position",
                parameters={"type": "object"},
            )
        ]

        decision = behavior.decide(observation, tools)

        # Verify backend was called
        assert len(backend.generate_with_tools_calls) == 1
        prompt, tools_arg, temp = backend.generate_with_tools_calls[0]

        # Verify prompt contains observation data
        assert "test_agent" not in prompt  # agent_id not in prompt
        assert "Tick: 1" in prompt
        assert "Position: (0.0, 0.0, 0.0)" in prompt

        # Verify tools were passed
        assert len(tools_arg) == 1
        assert tools_arg[0]["name"] == "move_to"

        # Verify decision was returned
        assert isinstance(decision, AgentDecision)
        assert decision.tool == "idle"

    def test_decide_stores_observation_in_memory(self):
        """Test that decide() stores observation in memory."""
        config = BackendConfig(model_path="test_model.gguf")
        backend = MockBackend(config)
        behavior = LocalLLMBehavior(backend=backend, memory_capacity=5)

        # Make multiple decisions
        for i in range(3):
            obs = Observation(
                agent_id="test_agent",
                tick=i,
                position=(float(i), 0.0, 0.0),
            )
            behavior.decide(obs, [])

        # Verify all observations are in memory
        memory_items = behavior.memory.retrieve()
        assert len(memory_items) == 3
        # retrieve() returns most recent first
        assert memory_items[0].tick == 2
        assert memory_items[2].tick == 0

    def test_decide_includes_memory_in_prompt(self):
        """Test that decide() includes recent observations in prompt."""
        config = BackendConfig(model_path="test_model.gguf")
        backend = MockBackend(config)
        behavior = LocalLLMBehavior(backend=backend)

        # Add some observations to memory
        for i in range(3):
            obs = Observation(
                agent_id="test_agent",
                tick=i,
                position=(float(i), 0.0, 0.0),
            )
            behavior.decide(obs, [])

        # Check that the last call included memory context
        prompt, _, _ = backend.generate_with_tools_calls[-1]
        assert "## Recent History" in prompt

    def test_decide_handles_resources_in_observation(self):
        """Test that decide() includes resources in prompt."""
        config = BackendConfig(model_path="test_model.gguf")
        backend = MockBackend(config)
        behavior = LocalLLMBehavior(backend=backend)

        observation = Observation(
            agent_id="test_agent",
            tick=1,
            position=(0.0, 0.0, 0.0),
            nearby_resources=[
                ResourceInfo(
                    name="apple",
                    type="food",
                    position=(5.0, 0.0, 0.0),
                    distance=5.0,
                ),
                ResourceInfo(
                    name="wood",
                    type="material",
                    position=(10.0, 0.0, 0.0),
                    distance=10.0,
                ),
            ],
        )

        behavior.decide(observation, [])

        # Verify resources were included in prompt
        prompt, _, _ = backend.generate_with_tools_calls[0]
        assert "## Nearby Resources" in prompt
        assert "apple (food)" in prompt
        assert "wood (material)" in prompt

    def test_decide_handles_hazards_in_observation(self):
        """Test that decide() includes hazards in prompt."""
        config = BackendConfig(model_path="test_model.gguf")
        backend = MockBackend(config)
        behavior = LocalLLMBehavior(backend=backend)

        observation = Observation(
            agent_id="test_agent",
            tick=1,
            position=(0.0, 0.0, 0.0),
            nearby_hazards=[
                HazardInfo(
                    name="fire",
                    type="hazard",
                    position=(3.0, 0.0, 0.0),
                    distance=3.0,
                    damage=10.0,
                ),
            ],
        )

        behavior.decide(observation, [])

        # Verify hazards were included in prompt
        prompt, _, _ = backend.generate_with_tools_calls[0]
        assert "## Nearby Hazards" in prompt
        assert "fire (hazard)" in prompt
        assert "damage: 10.0" in prompt

    def test_parse_decision_from_json_text(self):
        """Test parsing decision from JSON text response."""
        config = BackendConfig(model_path="test_model.gguf")
        backend = MockBackend(config)
        backend.mock_response = GenerationResult(
            text='{"tool": "move_to", "params": {"target_position": [5, 0, 0]}, "reasoning": "Moving to resource"}',
            tokens_used=50,
            finish_reason="stop",
            metadata={},
        )
        behavior = LocalLLMBehavior(backend=backend)

        observation = Observation(agent_id="test", tick=0, position=(0.0, 0.0, 0.0))
        decision = behavior.decide(observation, [])

        assert decision.tool == "move_to"
        assert decision.params == {"target_position": [5, 0, 0]}
        assert decision.reasoning == "Moving to resource"

    def test_parse_decision_from_json_with_markdown(self):
        """Test parsing decision from JSON wrapped in markdown code blocks."""
        config = BackendConfig(model_path="test_model.gguf")
        backend = MockBackend(config)
        backend.mock_response = GenerationResult(
            text='```json\n{"tool": "pickup", "params": {"item_id": "apple"}}\n```',
            tokens_used=50,
            finish_reason="stop",
            metadata={},
        )
        behavior = LocalLLMBehavior(backend=backend)

        observation = Observation(agent_id="test", tick=0, position=(0.0, 0.0, 0.0))
        decision = behavior.decide(observation, [])

        assert decision.tool == "pickup"
        assert decision.params == {"item_id": "apple"}

    def test_parse_decision_from_native_tool_call(self):
        """Test parsing decision from native tool call (e.g., vLLM)."""
        config = BackendConfig(model_path="test_model.gguf")
        backend = MockBackend(config)
        backend.mock_response = GenerationResult(
            text="Moving to the nearest resource",
            tokens_used=50,
            finish_reason="stop",
            metadata={
                "tool_call": {
                    "name": "move_to",
                    "arguments": {"target_position": [10, 0, 5]},
                }
            },
        )
        behavior = LocalLLMBehavior(backend=backend)

        observation = Observation(agent_id="test", tick=0, position=(0.0, 0.0, 0.0))
        decision = behavior.decide(observation, [])

        assert decision.tool == "move_to"
        assert decision.params == {"target_position": [10, 0, 5]}
        assert decision.reasoning == "Moving to the nearest resource"

    def test_parse_decision_from_parsed_tool_call(self):
        """Test parsing decision from pre-parsed tool call (e.g., llama.cpp)."""
        config = BackendConfig(model_path="test_model.gguf")
        backend = MockBackend(config)
        backend.mock_response = GenerationResult(
            text='{"tool": "idle", "params": {}}',
            tokens_used=50,
            finish_reason="stop",
            metadata={
                "parsed_tool_call": {
                    "tool": "move_to",
                    "params": {"target_position": [5, 0, 0]},
                    "reasoning": "Pre-parsed decision",
                }
            },
        )
        behavior = LocalLLMBehavior(backend=backend)

        observation = Observation(agent_id="test", tick=0, position=(0.0, 0.0, 0.0))
        decision = behavior.decide(observation, [])

        assert decision.tool == "move_to"
        assert decision.params == {"target_position": [5, 0, 0]}
        assert decision.reasoning == "Pre-parsed decision"

    def test_parse_decision_fallback_to_idle(self):
        """Test that invalid responses fall back to idle."""
        config = BackendConfig(model_path="test_model.gguf")
        backend = MockBackend(config)
        backend.mock_response = GenerationResult(
            text="This is not valid JSON",
            tokens_used=50,
            finish_reason="stop",
            metadata={},
        )
        behavior = LocalLLMBehavior(backend=backend)

        observation = Observation(agent_id="test", tick=0, position=(0.0, 0.0, 0.0))
        decision = behavior.decide(observation, [])

        assert decision.tool == "idle"
        assert "Parse error" in decision.reasoning

    def test_decide_handles_backend_error(self):
        """Test that decide() handles backend errors gracefully."""
        config = BackendConfig(model_path="test_model.gguf")
        backend = MockBackend(config)
        behavior = LocalLLMBehavior(backend=backend)

        # Make backend raise an error
        backend.generate_with_tools = Mock(side_effect=RuntimeError("Backend error"))

        observation = Observation(
            agent_id="test_agent",
            tick=1,
            position=(0.0, 0.0, 0.0),
        )

        decision = behavior.decide(observation, [])

        # Should return idle decision with error message
        assert decision.tool == "idle"
        assert "Error" in decision.reasoning

    def test_on_episode_start_clears_memory(self):
        """Test that on_episode_start() clears memory."""
        config = BackendConfig(model_path="test_model.gguf")
        backend = MockBackend(config)
        behavior = LocalLLMBehavior(backend=backend)

        # Add observations to memory
        for i in range(3):
            obs = Observation(agent_id="test", tick=i, position=(float(i), 0.0, 0.0))
            behavior.decide(obs, [])

        assert len(behavior.memory) == 3

        # Start new episode
        behavior.on_episode_start()

        # Memory should be cleared
        assert len(behavior.memory) == 0

    def test_on_episode_end_logs_metrics(self):
        """Test that on_episode_end() is called without errors."""
        config = BackendConfig(model_path="test_model.gguf")
        backend = MockBackend(config)
        behavior = LocalLLMBehavior(backend=backend)

        # Should not raise
        behavior.on_episode_end(success=True, metrics={"score": 100})
        behavior.on_episode_end(success=False)

    def test_on_tool_result_logs_result(self):
        """Test that on_tool_result() is called without errors."""
        config = BackendConfig(model_path="test_model.gguf")
        backend = MockBackend(config)
        behavior = LocalLLMBehavior(backend=backend)

        # Should not raise
        behavior.on_tool_result("move_to", {"success": True})


class TestCreateLocalLLMBehavior:
    """Tests for create_local_llm_behavior() factory function."""

    def test_create_with_model_path_only(self):
        """Test creating behavior with just a model_path."""
        # Skip - requires llama-cpp-python to be installed
        pytest.skip("Requires llama-cpp-python installation")

        behavior = create_local_llm_behavior(model_path="test_model.gguf")

        assert isinstance(behavior, LocalLLMBehavior)
        # Should use default foraging prompt
        assert "foraging agent" in behavior.system_prompt.lower()
        assert behavior.memory.capacity == 10

    def test_create_with_custom_system_prompt(self):
        """Test creating behavior with custom system prompt."""
        pytest.skip("Requires llama-cpp-python installation")

        behavior = create_local_llm_behavior(
            model_path="test_model.gguf", system_prompt="Custom prompt"
        )

        assert behavior.system_prompt == "Custom prompt"

    def test_create_with_custom_memory_capacity(self):
        """Test creating behavior with custom memory capacity."""
        pytest.skip("Requires llama-cpp-python installation")

        behavior = create_local_llm_behavior(model_path="test_model.gguf", memory_capacity=20)

        assert behavior.memory.capacity == 20

    def test_create_with_temperature_and_max_tokens(self):
        """Test creating behavior with custom temperature and max tokens."""
        pytest.skip("Requires llama-cpp-python installation")

        behavior = create_local_llm_behavior(
            model_path="test_model.gguf", temperature=0.9, max_tokens=1024
        )

        assert behavior.temperature == 0.9
        assert behavior.max_tokens == 1024

    def test_create_with_all_parameters(self):
        """Test creating behavior with all parameters."""
        pytest.skip("Requires llama-cpp-python installation")

        behavior = create_local_llm_behavior(
            model_path="test_model.gguf",
            system_prompt="Test prompt",
            memory_capacity=15,
            temperature=0.5,
            max_tokens=512,
        )

        assert behavior.system_prompt == "Test prompt"
        assert behavior.memory.capacity == 15
        assert behavior.temperature == 0.5
        assert behavior.max_tokens == 512


class TestLocalLLMBehaviorIntegration:
    """Integration tests for LocalLLMBehavior."""

    def test_full_decision_cycle(self):
        """Test a full decision cycle from observation to decision."""
        config = BackendConfig(model_path="test_model.gguf")
        backend = MockBackend(config)

        # Configure backend to return a move_to decision
        backend.generate_with_tools = Mock(
            return_value=GenerationResult(
                text='{"tool": "move_to", "params": {"target_position": [10, 0, 0]}, "reasoning": "Moving to resource"}',
                tokens_used=75,
                finish_reason="stop",
                metadata={},
            )
        )

        behavior = LocalLLMBehavior(
            backend=backend,
            system_prompt="You are a foraging agent.",
            memory_capacity=5,
        )

        observation = Observation(
            agent_id="forager_001",
            tick=10,
            position=(0.0, 0.0, 0.0),
            nearby_resources=[
                ResourceInfo(
                    name="apple",
                    type="food",
                    position=(10.0, 0.0, 0.0),
                    distance=10.0,
                )
            ],
        )

        tools = [
            ToolSchema(
                name="move_to",
                description="Move to target position",
                parameters={"type": "object"},
            ),
            ToolSchema(
                name="idle",
                description="Do nothing",
                parameters={"type": "object"},
            ),
        ]

        decision = behavior.decide(observation, tools)

        # Verify decision
        assert decision.tool == "move_to"
        assert decision.params == {"target_position": [10, 0, 0]}
        assert decision.reasoning == "Moving to resource"

        # Verify observation was stored
        memory_items = behavior.memory.retrieve()
        assert len(memory_items) == 1
        assert memory_items[0].tick == 10

    def test_multiple_decision_cycles_with_memory(self):
        """Test multiple decisions with memory building up."""
        config = BackendConfig(model_path="test_model.gguf")
        backend = MockBackend(config)
        behavior = LocalLLMBehavior(backend=backend, memory_capacity=3)

        tools = [
            ToolSchema(name="move_to", description="Move", parameters={}),
            ToolSchema(name="idle", description="Idle", parameters={}),
        ]

        # Make 5 decisions
        for i in range(5):
            obs = Observation(
                agent_id="test",
                tick=i,
                position=(float(i), 0.0, 0.0),
            )
            decision = behavior.decide(obs, tools)
            assert isinstance(decision, AgentDecision)

        # Memory should only keep last 3
        memory_items = behavior.memory.retrieve()
        assert len(memory_items) == 3
        # retrieve() returns most recent first
        assert memory_items[0].tick == 4
        assert memory_items[2].tick == 2
