"""
Framework adapters for Agent Arena SDK.

Adapters provide a structured interface for integrating LLM frameworks
(Anthropic, LangGraph, OpenAI, etc.) with Agent Arena.
"""

from .base import FrameworkAdapter

__all__ = ["FrameworkAdapter"]
