"""
LLM Client - Interface to Local Language Models

This module provides a simple interface to use local LLMs with the model manager.
You can see exactly how it works and modify it!

Supports:
- llama.cpp backend (GGUF models)
- vLLM backend (for high-performance inference)
- Automatic tool calling
"""

import json
import logging
from pathlib import Path
import sys

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "python"))

from backends.base import BackendConfig
from backends.llama_cpp_backend import LlamaCppBackend
from agent_runtime.schemas import ToolSchema

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Simple LLM client using local models.

    This client:
    - Uses models managed by the model manager
    - Supports tool calling
    - Handles errors gracefully
    - Provides reasoning traces

    Example:
        client = LLMClient(model_path="models/llama-2-7b/gguf/q4/model.gguf")

        response = client.generate(
            prompt="What should I do?",
            tools=[...tool schemas...]
        )

        print(response["text"])
    """

    def __init__(
        self,
        model_path: str,
        temperature: float = 0.7,
        max_tokens: int = 512,
        n_gpu_layers: int = -1,  # -1 = all layers on GPU
    ):
        """
        Initialize LLM client.

        Args:
            model_path: Path to model file (relative to project root)
            temperature: Sampling temperature (0-1, higher = more creative)
            max_tokens: Maximum tokens to generate
            n_gpu_layers: Number of layers on GPU (-1 = all, 0 = CPU only)
        """
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Create backend config
        config = BackendConfig(
            model_path=model_path,
            temperature=temperature,
            max_tokens=max_tokens,
            n_gpu_layers=n_gpu_layers,
        )

        # Initialize backend
        logger.info(f"Loading model from {model_path}")
        self.backend = LlamaCppBackend(config)

        if not self.backend.is_available():
            raise RuntimeError(f"Failed to load model from {model_path}")

        logger.info("Model loaded successfully")

    def generate(
        self,
        prompt: str,
        tools: list[ToolSchema] | None = None,
        temperature: float | None = None,
    ) -> dict:
        """
        Generate a response from the LLM.

        Args:
            prompt: The prompt to send to the LLM
            tools: Optional list of tools the LLM can call
            temperature: Optional temperature override

        Returns:
            Dictionary with:
                - text: Generated text
                - tool_call: Parsed tool call (if tools provided)
                - tokens_used: Number of tokens generated
                - finish_reason: Why generation stopped
        """
        try:
            if tools:
                # Convert tools to backend format
                tool_schemas = [t.to_anthropic_format() for t in tools]
                result = self.backend.generate_with_tools(
                    prompt=prompt, tools=tool_schemas, temperature=temperature or self.temperature
                )
            else:
                result = self.backend.generate(
                    prompt=prompt, temperature=temperature or self.temperature
                )

            # Parse tool calls if present
            tool_call = None
            if tools and result.text:
                tool_call = self._parse_tool_call(result.text)

            return {
                "text": result.text,
                "tool_call": tool_call,
                "tokens_used": result.tokens_used,
                "finish_reason": result.finish_reason,
            }

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return {
                "text": "",
                "tool_call": None,
                "tokens_used": 0,
                "finish_reason": "error",
                "error": str(e),
            }

    def _parse_tool_call(self, text: str) -> dict | None:
        """
        Parse tool call from LLM response.

        Looks for JSON blocks or function call syntax.

        Args:
            text: LLM response text

        Returns:
            Dictionary with tool and params, or None
        """
        try:
            # Try to find JSON block
            if "{" in text and "}" in text:
                start = text.find("{")
                end = text.rfind("}") + 1
                json_str = text[start:end]
                data = json.loads(json_str)

                # Check if it looks like a tool call
                if "tool" in data and "params" in data:
                    return {"tool": data["tool"], "params": data.get("params", {})}

            return None

        except Exception as e:
            logger.debug(f"Could not parse tool call: {e}")
            return None

    def is_available(self) -> bool:
        """Check if the LLM backend is ready."""
        return self.backend.is_available()

    def unload(self) -> None:
        """Unload the model and free resources."""
        self.backend.unload()
        logger.info("Model unloaded")
