"""
llama.cpp backend adapter.
"""

from typing import Any, Dict, List, Optional
import logging
import json

from .base import BaseBackend, BackendConfig, GenerationResult

logger = logging.getLogger(__name__)


class LlamaCppBackend(BaseBackend):
    """Backend adapter for llama.cpp."""

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

            self.llm = Llama(
                model_path=self.config.model_path,
                n_ctx=4096,  # Context window
                n_threads=8,  # CPU threads
                n_gpu_layers=0,  # GPU layers (0 = CPU only)
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
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> GenerationResult:
        """Generate text from prompt."""
        if not self.llm:
            raise RuntimeError("Model not loaded")

        temp = temperature if temperature is not None else self.config.temperature
        max_tok = max_tokens if max_tokens is not None else self.config.max_tokens

        try:
            response = self.llm(
                prompt,
                temperature=temp,
                max_tokens=max_tok,
                top_p=self.config.top_p,
                top_k=self.config.top_k,
                echo=False,
            )

            text = response["choices"][0]["text"]
            tokens_used = response["usage"]["total_tokens"]

            return GenerationResult(
                text=text,
                tokens_used=tokens_used,
                finish_reason=response["choices"][0]["finish_reason"],
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
        tools: List[Dict[str, Any]],
        temperature: Optional[float] = None,
    ) -> GenerationResult:
        """Generate with function calling support."""
        if not self.llm:
            raise RuntimeError("Model not loaded")

        # Build a prompt that includes tool schemas
        tool_descriptions = []
        for tool in tools:
            tool_desc = f"- {tool['name']}: {tool['description']}"
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
            # Extract JSON from the response
            text = result.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]

            parsed = json.loads(text.strip())
            result.metadata["parsed_tool_call"] = parsed

        except json.JSONDecodeError:
            logger.warning("Failed to parse tool call JSON from response")
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
