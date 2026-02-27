"""
LLM Client - Interface to Local Language Models

This module provides a simple interface to use local LLMs via llama-cpp-python.
You can see exactly how it works and modify it!

Supports:
- llama.cpp backend (GGUF models)
- Automatic tool calling

Requirements:
    pip install llama-cpp-python
"""

import json
import logging
from typing import Any, cast

from agent_arena_sdk import ToolSchema

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Simple LLM client using local models via llama-cpp-python.

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
        top_p: float = 0.9,
        top_k: int = 40,
    ):
        """
        Initialize LLM client.

        Args:
            model_path: Path to GGUF model file
            temperature: Sampling temperature (0-1, higher = more creative)
            max_tokens: Maximum tokens to generate
            n_gpu_layers: Number of layers on GPU (-1 = all, 0 = CPU only)
            top_p: Top-p sampling parameter
            top_k: Top-k sampling parameter
        """
        self.model_path = model_path
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.top_k = top_k
        self.llm = None

        try:
            from llama_cpp import Llama

            logger.info(f"Loading model from {model_path}")

            if n_gpu_layers == -1:
                logger.info("Offloading all layers to GPU")
            elif n_gpu_layers > 0:
                logger.info(f"Offloading {n_gpu_layers} layers to GPU")
            else:
                logger.info("Using CPU only (no GPU offload)")

            self.llm = Llama(
                model_path=model_path,
                n_ctx=4096,
                n_threads=8,
                n_gpu_layers=n_gpu_layers,
                verbose=False,
            )

            logger.info("Model loaded successfully")

        except ImportError:
            raise RuntimeError(
                "llama-cpp-python not installed. Install with: pip install llama-cpp-python"
            )

    def generate(
        self,
        prompt: str,
        tools: list[ToolSchema] | None = None,
        temperature: float | None = None,
        system_prompt: str | None = None,
    ) -> dict:
        """
        Generate a response from the LLM.

        Args:
            prompt: The user prompt to send to the LLM
            tools: Optional list of tools the LLM can call
            temperature: Optional temperature override
            system_prompt: Optional system prompt (sent as system message in chat)

        Returns:
            Dictionary with:
                - text: Generated text
                - tool_call: Parsed tool call (if tools provided)
                - tokens_used: Number of tokens generated
                - finish_reason: Why generation stopped
        """
        if not self.llm:
            raise RuntimeError("Model not loaded")

        try:
            messages: list[dict[str, str]] = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = self.llm.create_chat_completion(
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=self.max_tokens,
                top_p=self.top_p,
                top_k=self.top_k,
            )

            resp = cast(dict[str, Any], response)
            text = resp["choices"][0]["message"]["content"] or ""
            tokens_used = resp["usage"]["total_tokens"]
            finish_reason = str(resp["choices"][0].get("finish_reason", "stop"))

            # Parse tool calls if present
            tool_call = None
            if tools and text:
                tool_call = self._parse_tool_call(text)

            return {
                "text": text,
                "tool_call": tool_call,
                "tokens_used": tokens_used,
                "finish_reason": finish_reason,
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
        return self.llm is not None

    def unload(self) -> None:
        """Unload the model and free resources."""
        if self.llm:
            del self.llm
            self.llm = None
            logger.info("Model unloaded")
