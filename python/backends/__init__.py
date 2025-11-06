"""
LLM Backend Adapters for Agent Arena
"""

from .base import BaseBackend
from .llama_cpp_backend import LlamaCppBackend

__all__ = ["BaseBackend", "LlamaCppBackend"]
