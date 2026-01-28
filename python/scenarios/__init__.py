"""
Scenario definitions for Agent Arena.

Each scenario defines goals, tools, constraints, and metrics that
both LLM agents and learners can use.

Usage:
    from scenarios import get_scenario, list_scenarios, FORAGING

    # Get a scenario by ID
    scenario = get_scenario("foraging")

    # Generate system prompt for LLM
    prompt = scenario.to_system_prompt()

    # Generate documentation
    docs = scenario.to_markdown()
"""

from .foraging import FORAGING_SCENARIO
from .loader import get_scenario, list_scenarios, register_scenario

# Register built-in scenarios
register_scenario(FORAGING_SCENARIO)

# Convenient aliases
FORAGING = FORAGING_SCENARIO

__all__ = [
    "get_scenario",
    "list_scenarios",
    "register_scenario",
    "FORAGING",
    "FORAGING_SCENARIO",
]
