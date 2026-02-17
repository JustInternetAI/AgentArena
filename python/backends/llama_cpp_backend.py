"""
llama.cpp backend adapter.
"""

import json
import logging
from typing import TYPE_CHECKING, Any, cast

from .base import BackendConfig, BaseBackend, GenerationResult

if TYPE_CHECKING:
    from llama_cpp import Llama

logger = logging.getLogger(__name__)


class LlamaCppBackend(BaseBackend):
    """Backend adapter for llama.cpp."""

    llm: "Llama | None"

    def __init__(self, config: BackendConfig):
        """Initialize llama.cpp backend."""
        super().__init__(config)
        self.llm = None
        self._load_model()

    def _load_model(self) -> None:
        """Load the llama.cpp model."""
        try:
            from llama_cpp import Llama

            logger.info(f"Loading model from {self.config.model_path}")

            # Use GPU layers from config
            n_gpu_layers = getattr(self.config, "n_gpu_layers", 0)

            if n_gpu_layers > 0:
                logger.info(f"Offloading {n_gpu_layers} layers to GPU")
            elif n_gpu_layers == -1:
                logger.info("Offloading all layers to GPU")
            else:
                logger.info("Using CPU only (no GPU offload)")

            self.llm = Llama(
                model_path=self.config.model_path,
                n_ctx=4096,  # Context window
                n_threads=8,  # CPU threads
                n_gpu_layers=n_gpu_layers,  # GPU layers (0 = CPU only, -1 = all)
                verbose=False,  # Reduce output noise
            )

            logger.info("Model loaded successfully")

        except ImportError:
            logger.error(
                "llama-cpp-python not installed. Install with: pip install llama-cpp-python"
            )
            raise
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def generate(
        self,
        prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        system_prompt: str | None = None,
    ) -> GenerationResult:
        """Generate text from prompt using chat completion API.

        Args:
            prompt: The user message / prompt text
            temperature: Sampling temperature override
            max_tokens: Max tokens override
            system_prompt: Optional system message (prepended to chat)
        """
        if not self.llm:
            raise RuntimeError("Model not loaded")

        temp = temperature if temperature is not None else self.config.temperature
        max_tok = max_tokens if max_tokens is not None else self.config.max_tokens

        try:
            # Build chat messages so llama.cpp applies the correct chat template
            messages: list[dict[str, str]] = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = self.llm.create_chat_completion(
                messages=messages,
                temperature=temp,
                max_tokens=max_tok,
                top_p=self.config.top_p,
                top_k=self.config.top_k,
            )

            # Cast response to dict since we're not streaming
            resp = cast(dict[str, Any], response)
            text = resp["choices"][0]["message"]["content"] or ""
            tokens_used = resp["usage"]["total_tokens"]
            finish_reason = str(resp["choices"][0].get("finish_reason", "stop"))

            return GenerationResult(
                text=text,
                tokens_used=tokens_used,
                finish_reason=finish_reason,
                metadata={"model": self.config.model_path},
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
        """Generate with function calling support."""
        if not self.llm:
            raise RuntimeError("Model not loaded")

        # The prompt already contains the system instructions and user data.
        # Just pass it through to generate() — the caller (agent.py) builds
        # the full prompt with system + decision template.
        result = self.generate(prompt, temperature)

        # Try to parse JSON from result
        try:
            text = result.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]

            parsed = json.loads(text.strip())
            result.metadata["parsed_tool_call"] = parsed

        except json.JSONDecodeError:
            logger.debug("Backend JSON parse failed (expected for CoT format)")
            result.metadata["parse_error"] = True

        return result

    def is_available(self) -> bool:
        """Check if backend is ready."""
        return self.llm is not None

    def unload(self) -> None:
        """Unload the model."""
        if self.llm:
            del self.llm
            self.llm = None
            logger.info("Model unloaded")
