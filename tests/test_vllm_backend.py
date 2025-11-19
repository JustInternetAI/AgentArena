"""
Tests for vLLM backend.

Note: These tests require a running vLLM server.
Use pytest markers to skip if server is not available.
"""

import pytest
from backends.vllm_backend import VLLMBackend, VLLMBackendConfig


@pytest.fixture
def vllm_config():
    """Create a vLLM config for testing."""
    return VLLMBackendConfig(
        model_path="meta-llama/Llama-2-7b-chat-hf",
        api_base="http://localhost:8000/v1",
        temperature=0.7,
        max_tokens=100,
    )


@pytest.fixture
def vllm_backend(vllm_config):
    """Create a vLLM backend instance."""
    try:
        backend = VLLMBackend(vllm_config)
        if not backend.is_available():
            pytest.skip("vLLM server not available")
        return backend
    except Exception as e:
        pytest.skip(f"Could not connect to vLLM server: {e}")


def test_vllm_config_creation():
    """Test vLLM config initialization."""
    config = VLLMBackendConfig(
        model_path="test-model",
        api_base="http://test:8000/v1",
        api_key="test-key",
        temperature=0.5,
        max_tokens=256,
    )

    assert config.model_path == "test-model"
    assert config.api_base == "http://test:8000/v1"
    assert config.api_key == "test-key"
    assert config.temperature == 0.5
    assert config.max_tokens == 256


def test_vllm_backend_initialization(vllm_config):
    """Test vLLM backend can be initialized."""
    try:
        backend = VLLMBackend(vllm_config)
        assert backend.client is not None
        assert backend.config == vllm_config
    except Exception:
        pytest.skip("vLLM server not available")


def test_vllm_is_available(vllm_backend):
    """Test availability check."""
    assert vllm_backend.is_available() is True


def test_vllm_generate(vllm_backend):
    """Test basic text generation."""
    prompt = "Hello, my name is"
    result = vllm_backend.generate(prompt, max_tokens=20)

    assert result is not None
    assert len(result.text) > 0
    assert result.tokens_used > 0
    assert result.finish_reason in ["stop", "length"]
    assert "model" in result.metadata


def test_vllm_generate_with_temperature(vllm_backend):
    """Test generation with custom temperature."""
    prompt = "The weather today is"
    result = vllm_backend.generate(prompt, temperature=0.1, max_tokens=20)

    assert result is not None
    assert len(result.text) > 0
    assert result.finish_reason in ["stop", "length"]


def test_vllm_generate_with_tools(vllm_backend):
    """Test tool calling generation."""
    prompt = "I need to move to coordinates (10, 20, 5)"

    tools = [
        {
            "name": "move_to",
            "description": "Move agent to target coordinates",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Target [x, y, z] coordinates",
                    }
                },
                "required": ["target"],
            },
        }
    ]

    result = vllm_backend.generate_with_tools(prompt, tools)

    assert result is not None
    # Result should contain either a tool call or text response
    assert len(result.text) > 0 or "tool_call" in result.metadata


def test_vllm_generate_error_handling(vllm_backend):
    """Test error handling with invalid input."""
    # Empty prompt should still work
    result = vllm_backend.generate("", max_tokens=10)
    assert result is not None
    assert result.finish_reason in ["stop", "length", "error"]


def test_vllm_unload(vllm_config):
    """Test unloading backend."""
    try:
        backend = VLLMBackend(vllm_config)
        backend.unload()
        assert backend.client is None
        assert backend.is_available() is False
    except Exception:
        pytest.skip("vLLM server not available")


def test_vllm_multiple_generations(vllm_backend):
    """Test multiple sequential generations."""
    prompts = ["Hello", "How are you?", "What is AI?"]

    for prompt in prompts:
        result = vllm_backend.generate(prompt, max_tokens=20)
        assert result is not None
        assert len(result.text) > 0


def test_vllm_generate_with_tools_fallback(vllm_backend):
    """Test fallback tool calling method."""
    prompt = "Pick up the sword item"

    tools = [
        {
            "name": "pickup_item",
            "description": "Pick up an item from the world",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_name": {
                        "type": "string",
                        "description": "Name of the item to pick up",
                    }
                },
                "required": ["item_name"],
            },
        }
    ]

    # Test the fallback method directly
    result = vllm_backend._generate_with_tools_fallback(prompt, tools, temperature=0.7)

    assert result is not None
    assert len(result.text) > 0


@pytest.mark.parametrize("max_tokens", [10, 50, 100])
def test_vllm_different_max_tokens(vllm_backend, max_tokens):
    """Test generation with different max token limits."""
    prompt = "Once upon a time"
    result = vllm_backend.generate(prompt, max_tokens=max_tokens)

    assert result is not None
    assert result.tokens_used <= max_tokens * 1.5  # Some tolerance


@pytest.mark.parametrize("temperature", [0.1, 0.7, 1.0])
def test_vllm_different_temperatures(vllm_backend, temperature):
    """Test generation with different temperatures."""
    prompt = "The capital of France is"
    result = vllm_backend.generate(prompt, temperature=temperature, max_tokens=20)

    assert result is not None
    assert len(result.text) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
