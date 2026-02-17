"""
Scenario loader utilities.

Provides functions to load, register, and access scenario definitions.
"""

import json
import logging
from pathlib import Path

from agent_runtime.schemas import ScenarioDefinition

logger = logging.getLogger(__name__)

# Registry of all available scenarios
_SCENARIO_REGISTRY: dict[str, ScenarioDefinition] = {}


def register_scenario(scenario: ScenarioDefinition) -> None:
    """
    Register a scenario definition.

    Args:
        scenario: The scenario to register
    """
    if scenario.id in _SCENARIO_REGISTRY:
        logger.warning(f"Overwriting existing scenario: {scenario.id}")
    _SCENARIO_REGISTRY[scenario.id] = scenario
    logger.debug(f"Registered scenario: {scenario.id}")


def get_scenario(scenario_id: str) -> ScenarioDefinition:
    """
    Get a scenario by ID.

    Args:
        scenario_id: The scenario identifier (e.g., "foraging")

    Returns:
        The scenario definition

    Raises:
        KeyError: If scenario not found
    """
    if scenario_id not in _SCENARIO_REGISTRY:
        available = ", ".join(_SCENARIO_REGISTRY.keys())
        raise KeyError(f"Unknown scenario: {scenario_id}. Available: {available}")
    return _SCENARIO_REGISTRY[scenario_id]


def list_scenarios() -> list[str]:
    """
    List all registered scenario IDs.

    Returns:
        List of scenario identifiers
    """
    return list(_SCENARIO_REGISTRY.keys())


def get_all_scenarios() -> dict[str, ScenarioDefinition]:
    """
    Get all registered scenarios.

    Returns:
        Dictionary mapping scenario ID to definition
    """
    return dict(_SCENARIO_REGISTRY)


def load_scenario_from_json(path: str | Path) -> ScenarioDefinition:
    """
    Load a scenario from a JSON file.

    Args:
        path: Path to JSON file

    Returns:
        ScenarioDefinition instance
    """
    path = Path(path)
    with open(path) as f:
        data = json.load(f)
    return ScenarioDefinition.from_dict(data)


def save_scenario_to_json(scenario: ScenarioDefinition, path: str | Path) -> None:
    """
    Save a scenario to a JSON file.

    Args:
        scenario: The scenario to save
        path: Path to save to
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(scenario.to_dict(), f, indent=2)


def generate_scenario_docs(scenario: ScenarioDefinition, output_dir: str | Path) -> Path:
    """
    Generate markdown documentation for a scenario.

    Args:
        scenario: The scenario to document
        output_dir: Directory to write documentation

    Returns:
        Path to generated markdown file
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{scenario.id}.md"
    with open(output_path, "w") as f:
        f.write(scenario.to_markdown())

    logger.info(f"Generated docs: {output_path}")
    return output_path


def generate_all_scenario_docs(output_dir: str | Path) -> list[Path]:
    """
    Generate documentation for all registered scenarios.

    Args:
        output_dir: Directory to write documentation

    Returns:
        List of paths to generated files
    """
    paths = []
    for scenario in _SCENARIO_REGISTRY.values():
        path = generate_scenario_docs(scenario, output_dir)
        paths.append(path)
    return paths
