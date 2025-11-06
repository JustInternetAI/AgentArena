"""
Base backend interface for LLM backends.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class BackendConfig:
    """Configuration for LLM backend."""
    model_path: str
    temperature: float = 0.7
    max_tokens: int = 512
    top_p: float = 0.9
    top_k: int = 40


@dataclass
class GenerationResult:
    """Result from LLM generation."""
    text: str
    tokens_used: int
    finish_reason: str  # "stop", "length", "error"
    metadata: Dict[str, Any]


class BaseBackend(ABC):
    """
    Abstract base class for LLM backends.

    All backend implementations must inherit from this class.
    """

    def __init__(self, config: BackendConfig):
        """
        Initialize the backend.

        Args:
            config: Backend configuration
        """
        self.config = config

    @abstractmethod
    def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> GenerationResult:
        """
        Generate text from prompt.

        Args:
            prompt: Input prompt
            temperature: Override temperature (optional)
            max_tokens: Override max tokens (optional)

        Returns:
            GenerationResult with generated text and metadata
        """
        pass

    @abstractmethod
    def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        temperature: Optional[float] = None,
    ) -> GenerationResult:
        """
        Generate with function/tool calling support.

        Args:
            prompt: Input prompt
            tools: List of available tool schemas
            temperature: Override temperature (optional)

        Returns:
            GenerationResult with tool call or text
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if backend is available and ready.

        Returns:
            True if backend is loaded and ready
        """
        pass

    @abstractmethod
    def unload(self) -> None:
        """Unload the model and free resources."""
        pass
