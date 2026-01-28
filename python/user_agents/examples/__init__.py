"""
Example agent implementations for the three-tier learning progression.

BEGINNER TIER:
    SimpleForagerSimple - Uses SimpleAgentBehavior
    - Returns tool names only
    - Framework infers parameters
    - Focus: Understanding the decision loop

INTERMEDIATE TIER:
    SimpleForager - Uses AgentBehavior
    - Returns full AgentDecision with params
    - Manages memory with SlidingWindowMemory
    - Focus: State tracking and explicit parameters

ADVANCED TIER:
    LLMForager - Uses LLMAgentBehavior
    - Integrates LLM for reasoning
    - Custom prompt engineering
    - Focus: LLM-based decision making

Use these as starting points for your own agents!
"""

from .llm_forager import LLMForager
from .simple_forager import SimpleForager
from .simple_forager_simple import SimpleForagerSimple

__all__ = ["SimpleForager", "SimpleForagerSimple", "LLMForager"]
