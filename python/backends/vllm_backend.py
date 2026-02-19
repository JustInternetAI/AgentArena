"""
vLLM backend adapter using OpenAI-compatible API.

vLLM is a high-throughput inference engine that provides an OpenAI-compatible
REST API. This backend connects to a vLLM server instance.
"""

import json
import logging
from typing import Any

from openai import OpenAI

from .base import BackendConfig, BaseBackend, GenerationResult

logger = logging.getLogger(__name__)


class VLLMBackendConfig(BackendConfig):
    """Extended configuration for vLLM backend."""

    def __init__(
        self,
        model_path: str,
        api_base: str = "http://localhost:8000/v1",
        api_key: str = "EMPTY",
        temperature: float = 0.7,
        max_tokens: int = 512,
        top_p: float = 0.9,
        top_k: int = 40,
    ):
        """
        Initialize vLLM backend config.

        Args:
            model_path: Model identifier (e.g., "meta-llama/Llama-2-7b-chat-hf")
            api_base: Base URL for vLLM server
            api_key: API key (vLLM uses "EMPTY" by default)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            top_k: Top-k sampling parameter
        """
        super().__init__(
            model_path=model_path,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            top_k=top_k,
        )
        self.api_base = api_base
        self.api_key = api_key


class VLLMBackend(BaseBackend):
    """
    Backend adapter for vLLM inference server.

    This backend connects to a running vLLM server using the OpenAI-compatible API.
    The vLLM server must be started separately before using this backend.

    Example:
        Start vLLM server:
        ```bash
        python -m vllm.entrypoints.openai.api_server \\
            --model meta-llama/Llama-2-7b-chat-hf \\
            --port 8000
        ```

        Then use this backend:
        ```python
        config = VLLMBackendConfig(
            model_path="meta-llama/Llama-2-7b-chat-hf",
            api_base="http://localhost:8000/v1"
        )
        backend = VLLMBackend(config)
        result = backend.generate("Hello, world!")
        ```
    """

    def __init__(self, config: VLLMBackendConfig):
        """
        Initialize vLLM backend.

        Args:
            config: vLLM backend configuration
        """
        super().__init__(config)
        self.config: VLLMBackendConfig = config
        self.client: OpenAI | None = None
        self._connect()

    def _connect(self) -> None:
        """Connect to vLLM server."""
        try:
            logger.info(f"Connecting to vLLM server at {self.config.api_base}")

            self.client = OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.api_base,
            )

            # Test connection with a simple request
            try:
                models = self.client.models.list()
                logger.info(f"Connected to vLLM. Available models: {[m.id for m in models.data]}")
            except Exception as e:
                logger.warning(f"Could not list models (server may not be ready): {e}")

        except Exception as e:
            logger.error(f"Failed to connect to vLLM server: {e}")
            raise

    def generate(
        self,
        prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
    ) -> GenerationResult:
        """
        Generate text from prompt using vLLM.

        Args:
            prompt: Input prompt
            temperature: Override temperature (optional)
            max_tokens: Override max tokens (optional)
            system_prompt: Optional system message (not used for completion API)

        Returns:
            GenerationResult with generated text and metadata
        """
        if not self.client:
            raise RuntimeError("vLLM client not connected")

        temp = temperature if temperature is not None else self.config.temperature
        max_tok = max_tokens if max_tokens is not None else self.config.max_tokens

        try:
            response = self.client.completions.create(
                model=self.config.model_path,
                prompt=prompt,
                temperature=temp,
                max_tokens=max_tok,
                top_p=self.config.top_p,
                extra_body={"top_k": self.config.top_k},
            )

            text = response.choices[0].text
            tokens_used = response.usage.total_tokens if response.usage else 0

            return GenerationResult(
                text=text,
                tokens_used=tokens_used,
                finish_reason=response.choices[0].finish_reason or "stop",
                metadata={
                    "model": self.config.model_path,
                    "api_base": self.config.api_base,
                },
            )

        except Exception as e:
            logger.error(f"Generation error: {e}")
            return GenerationResult(
                text="",
                tokens_used=0,
                finish_reason="error",
                metadata={"error": str(e)},
            )

    def generate_with_tools(
        self,
        prompt: str,
        tools: list[dict[str, Any]],
        temperature: float | None = None,
    ) -> GenerationResult:
        """
        Generate with function calling support.

        vLLM supports OpenAI-style function calling for compatible models.

        Args:
            prompt: Input prompt
            tools: List of available tool schemas
            temperature: Override temperature (optional)

        Returns:
            GenerationResult with tool call or text
        """
        if not self.client:
            raise RuntimeError("vLLM client not connected")

        temp = temperature if temperature is not None else self.config.temperature

        try:
            # Convert tool schemas to OpenAI format
            openai_tools = []
            for tool in tools:
                openai_tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": tool["name"],
                            "description": tool["description"],
                            "parameters": tool.get("parameters", {}),
                        },
                    }
                )

            # Use chat completions API for function calling
            response = self.client.chat.completions.create(  # type: ignore[call-overload]
                model=self.config.model_path,
                messages=[{"role": "user", "content": prompt}],
                tools=openai_tools,
                tool_choice="auto",
                temperature=temp,
                max_tokens=self.config.max_tokens,
            )

            choice = response.choices[0]
            tokens_used = response.usage.total_tokens if response.usage else 0

            # Check if model returned a tool call
            if choice.message.tool_calls:
                tool_call = choice.message.tool_calls[0]
                text = choice.message.content or ""

                return GenerationResult(
                    text=text,
                    tokens_used=tokens_used,
                    finish_reason=choice.finish_reason or "stop",
                    metadata={
                        "model": self.config.model_path,
                        "tool_call": {
                            "name": tool_call.function.name,
                            "arguments": json.loads(tool_call.function.arguments),
                        },
                    },
                )
            else:
                # No tool call, return regular text
                text = choice.message.content or ""
                return GenerationResult(
                    text=text,
                    tokens_used=tokens_used,
                    finish_reason=choice.finish_reason or "stop",
                    metadata={"model": self.config.model_path},
                )

        except Exception as e:
            logger.error(f"Tool generation error: {e}")

            # Fallback to prompt-based tool calling
            logger.info("Falling back to prompt-based tool calling")
            return self._generate_with_tools_fallback(prompt, tools, temp)

    def _generate_with_tools_fallback(
        self,
        prompt: str,
        tools: list[dict[str, Any]],
        temperature: float,
    ) -> GenerationResult:
        """
        Fallback method for tool calling using prompt engineering.

        Used when the model doesn't support native function calling.

        Args:
            prompt: Input prompt
            tools: List of available tool schemas
            temperature: Sampling temperature

        Returns:
            GenerationResult with tool call attempt
        """
        # Build a prompt that includes tool schemas
        tool_descriptions = []
        for tool in tools:
            tool_desc = f"- {tool['name']}: {tool['description']}"
            if "parameters" in tool:
                tool_desc += f"\n  Parameters: {json.dumps(tool['parameters'])}"
            tool_descriptions.append(tool_desc)

        tools_text = "\n".join(tool_descriptions)

        enhanced_prompt = f"""{prompt}

Available tools:
{tools_text}

Respond with a JSON object in the format:
{{"tool": "tool_name", "params": {{}}, "reasoning": "why this tool"}}

Or if no tool is needed:
{{"tool": "none", "reasoning": "explanation"}}
"""

        result = self.generate(enhanced_prompt, temperature)

        # Try to parse JSON from result
        try:
            text = result.text.strip()
            # Remove markdown code blocks if present
            if text.startswith("```json"):
                text = text[7:]
            elif text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]

            parsed = json.loads(text.strip())
            result.metadata["parsed_tool_call"] = parsed

        except json.JSONDecodeError:
            # This is expected for Chain-of-Thought format (THINKING: ... ACTION: ...)
            # The downstream AgentDecision.from_llm_response() handles CoT parsing
            logger.debug("Backend JSON parse failed (expected for CoT format)")
            result.metadata["parse_error"] = True

        return result

    def is_available(self) -> bool:
        """
        Check if vLLM server is available and ready.

        Returns:
            True if server is connected and responsive
        """
        if not self.client:
            return False

        try:
            # Try to list models as a health check
            self.client.models.list()
            return True
        except Exception as e:
            logger.debug(f"vLLM availability check failed: {e}")
            return False

    def unload(self) -> None:
        """
        Disconnect from vLLM server.

        Note: This only closes the client connection. The vLLM server
        continues running and must be stopped separately if needed.
        """
        if self.client:
            self.client.close()
            self.client = None
            logger.info("Disconnected from vLLM server")
