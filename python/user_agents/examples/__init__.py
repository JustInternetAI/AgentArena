"""
Example agent implementations.

These agents demonstrate how to use the Agent Arena framework:
- SimpleForager: Full AgentBehavior implementation with memory and reasoning
- SimpleForagerSimple: Beginner-friendly SimpleAgentBehavior version

Use these as starting points for your own agents!
"""

from .simple_forager import SimpleForager
from .simple_forager_simple import SimpleForagerSimple

__all__ = ["SimpleForager", "SimpleForagerSimple"]
