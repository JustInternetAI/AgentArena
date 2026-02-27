"""
Adapter-Agnostic Agent Eval Harness

Evaluate any agent's decisions against predefined scenarios or
custom observations — no Godot, no game connection needed.

Works with any object that has a decide(obs) -> Decision method:
framework adapters (ClaudeAdapter, etc.), standalone agents
(beginner, intermediate, LLM starter), or your own custom agent.

Usage:
    # All scenarios with the Claude adapter
    python eval_agent.py --adapter claude

    # Single scenario with the beginner agent
    python eval_agent.py --adapter beginner --scenario hazard_escape

    # Interactive mode — input your own observations
    python eval_agent.py --adapter claude --interactive

    # LLM starter with a local model
    python eval_agent.py --adapter llm --model path/to/model.gguf

    # Intermediate starter
    python eval_agent.py --adapter intermediate
"""

import argparse
import importlib
import json
import sys
from pathlib import Path

# Ensure SDK and starters are importable
_repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_repo_root / "python" / "sdk"))

from agent_arena_sdk.testing import (
    mock_hazard,
    mock_observation,
    mock_resource,
    mock_station,
)

# ---------------------------------------------------------------------------
#  Adapter registry
# ---------------------------------------------------------------------------

# Each entry: (module_path_relative_to_starter_dir, class_name)
ADAPTERS: dict[str, tuple[str, str]] = {
    "claude": ("claude.agent", "ClaudeAdapter"),
    "beginner": ("beginner.agent", "Agent"),
    "intermediate": ("intermediate.agent", "Agent"),
    "llm": ("llm.agent", "Agent"),
}


def load_agent(adapter_name: str, model: str | None = None):
    """
    Load and instantiate an agent by adapter name.

    Adds the appropriate starter directory to sys.path, imports the
    module, and instantiates the agent class.
    """
    if adapter_name not in ADAPTERS:
        print(f"Unknown adapter: {adapter_name}")
        print(f"Available: {', '.join(ADAPTERS.keys())}")
        sys.exit(1)

    module_path, class_name = ADAPTERS[adapter_name]
    starters_dir = _repo_root / "starters"

    # Add starters root so "claude.agent" resolves to starters/claude/agent.py
    starters_str = str(starters_dir)
    if starters_str not in sys.path:
        sys.path.insert(0, starters_str)

    # For the LLM starter, also add its own directory (it has local imports)
    starter_subdir = str(starters_dir / adapter_name)
    if starter_subdir not in sys.path:
        sys.path.insert(0, starter_subdir)

    try:
        module = importlib.import_module(module_path)
    except ImportError as e:
        print(f"Failed to import {module_path}: {e}")
        print(f"Make sure the starter's dependencies are installed.")
        sys.exit(1)

    cls = getattr(module, class_name)

    # Instantiate with model if the adapter accepts it
    if adapter_name == "llm" and model:
        return cls(model_path=model)
    elif adapter_name == "claude" and model:
        return cls(model=model)
    else:
        return cls()


# ---------------------------------------------------------------------------
#  Predefined scenarios
# ---------------------------------------------------------------------------

SCENARIOS = {
    "hazard_escape": {
        "description": "Fire is 1.5 units away. Agent should flee.",
        "observation": mock_observation(
            tick=1,
            position=(0.0, 0.0, 0.0),
            health=80.0,
            nearby_hazards=[mock_hazard("fire", position=(1.0, 0.0, 0.0), distance=1.5)],
        ),
    },
    "resource_collection": {
        "description": "Berry 8 units away, no threats.",
        "observation": mock_observation(
            tick=1,
            position=(0.0, 0.0, 0.0),
            nearby_resources=[mock_resource("berry", position=(10.0, 0.0, 5.0), distance=8.0)],
        ),
    },
    "danger_vs_reward": {
        "description": "Fire 2 units away AND berry 3 units away. Safety vs reward tradeoff.",
        "observation": mock_observation(
            tick=1,
            position=(0.0, 0.0, 0.0),
            health=60.0,
            nearby_hazards=[mock_hazard("fire", position=(2.0, 0.0, 0.0), distance=2.0)],
            nearby_resources=[mock_resource("berry", position=(3.0, 0.0, 1.0), distance=3.0)],
        ),
    },
    "low_health_triage": {
        "description": "Health critical (15 HP), berry nearby. Should be cautious.",
        "observation": mock_observation(
            tick=1,
            position=(0.0, 0.0, 0.0),
            health=15.0,
            nearby_resources=[mock_resource("berry", position=(5.0, 0.0, 3.0), distance=4.0)],
        ),
    },
    "exploration": {
        "description": "Nothing visible, only 20% explored. Should explore.",
        "observation": mock_observation(
            tick=10,
            position=(0.0, 0.0, 0.0),
            health=100.0,
        ),
    },
    "crafting_opportunity": {
        "description": "Has wood + stone, workbench nearby. Should craft a torch.",
        "observation": mock_observation(
            tick=5,
            position=(0.0, 0.0, 0.0),
            inventory={"wood": 2, "stone": 1},
            nearby_stations=[mock_station("workbench", position=(1.0, 0.0, 0.0), distance=1.0)],
        ),
    },
}


# ---------------------------------------------------------------------------
#  Core eval logic
# ---------------------------------------------------------------------------


def format_observation_summary(obs) -> str:
    """One-line summary of an observation for display."""
    parts = [f"Position: {list(obs.position)}", f"Health: {obs.health}", f"Energy: {obs.energy}"]
    if obs.nearby_resources:
        res = ", ".join(f"{r.type} at {list(r.position)}" for r in obs.nearby_resources)
        parts.append(f"Resources: {res}")
    if obs.nearby_hazards:
        haz = ", ".join(f"{h.type} at {list(h.position)}" for h in obs.nearby_hazards)
        parts.append(f"Hazards: {haz}")
    if obs.nearby_stations:
        sta = ", ".join(f"{s.type} at {list(s.position)}" for s in obs.nearby_stations)
        parts.append(f"Stations: {sta}")
    if obs.inventory:
        inv = ", ".join(f"{item.name} x{item.quantity}" for item in obs.inventory)
        parts.append(f"Inventory: {inv}")
    return " | ".join(parts)


def run_scenario(agent, name: str, scenario: dict, index: int, total: int) -> dict:
    """Run a single scenario and display the result."""
    # Reset stateful agents between scenarios so memory doesn't bleed across
    if hasattr(agent, "memory") and hasattr(agent.memory, "clear"):
        agent.memory.clear()
    if hasattr(agent, "planner") and hasattr(agent.planner, "cancel"):
        agent.planner.cancel()
    if hasattr(agent, "visited_positions"):
        agent.visited_positions.clear()

    obs = scenario["observation"]
    print(f"\n[{index}/{total}] {name}")
    print(f"  {scenario['description']}")

    decision = agent.decide(obs)

    print(f"  Decision: {decision.tool}", end="")
    if decision.params:
        print(f" -> {json.dumps(decision.params)}", end="")
    print()
    if decision.reasoning:
        reasoning = decision.reasoning
        if len(reasoning) > 200:
            reasoning = reasoning[:200] + "..."
        print(f"  Reasoning: \"{reasoning}\"")

    # Token info is optional — only some adapters track it
    trace = getattr(agent, "last_trace", None)
    tokens = 0
    if trace:
        tokens = trace.get("tokens_used", 0)
        if tokens:
            print(f"  Tokens: {tokens}")

    return {
        "scenario": name,
        "tool": decision.tool,
        "params": decision.params,
        "reasoning": decision.reasoning,
        "tokens": tokens,
    }


def run_all_scenarios(agent, scenario_filter: str | None = None):
    """Run predefined scenarios and print a scorecard."""
    if scenario_filter:
        if scenario_filter not in SCENARIOS:
            print(f"Unknown scenario: {scenario_filter}")
            print(f"Available: {', '.join(SCENARIOS.keys())}")
            sys.exit(1)
        scenarios = {scenario_filter: SCENARIOS[scenario_filter]}
    else:
        scenarios = SCENARIOS

    total = len(scenarios)
    results = []

    for i, (name, scenario) in enumerate(scenarios.items(), 1):
        result = run_scenario(agent, name, scenario, i, total)
        results.append(result)

    # Summary
    total_tokens = sum(r["tokens"] for r in results)
    print(f"\n{'=' * 50}")
    print(f"Scenarios run: {len(results)}")
    if total_tokens:
        print(f"Total tokens: {total_tokens}")


def parse_position(text: str, default: tuple = (0.0, 0.0, 0.0)) -> tuple:
    """Parse 'x, y, z' into a tuple of floats."""
    text = text.strip()
    if not text:
        return default
    parts = [float(p.strip()) for p in text.split(",")]
    if len(parts) == 2:
        return (parts[0], 0.0, parts[1])
    if len(parts) == 3:
        return tuple(parts)
    raise ValueError(f"Expected 2-3 numbers, got {len(parts)}")


def parse_entities(text: str, factory):
    """Parse 'type:x,y,z;type:x,y,z' into a list of mock entities."""
    text = text.strip()
    if not text:
        return []
    entities = []
    for entry in text.split(";"):
        entry = entry.strip()
        if not entry:
            continue
        if ":" not in entry:
            entities.append(factory(entry))
            continue
        type_name, coords = entry.split(":", 1)
        pos = parse_position(coords)
        dist = (pos[0] ** 2 + pos[1] ** 2 + pos[2] ** 2) ** 0.5
        entities.append(factory(type_name.strip(), position=pos, distance=max(dist, 0.1)))
    return entities


def interactive_mode(agent):
    """Prompt user for observation params, run agent, display result. Loop."""
    print("\n== Interactive Eval Mode ==")
    print("Enter observation parameters (empty = default, 'q' to quit)\n")

    while True:
        try:
            pos_input = input("Position [0, 0, 0]: ")
            if pos_input.strip().lower() == "q":
                break
            position = parse_position(pos_input)

            health_input = input("Health [100.0]: ").strip()
            health = float(health_input) if health_input else 100.0

            energy_input = input("Energy [100.0]: ").strip()
            energy = float(energy_input) if energy_input else 100.0

            res_input = input("Resources (type:x,y,z;type:x,y,z): ")
            resources = parse_entities(res_input, mock_resource) or None

            haz_input = input("Hazards (type:x,y,z;type:x,y,z): ")
            hazards = parse_entities(haz_input, mock_hazard) or None

            sta_input = input("Stations (type:x,y,z;type:x,y,z): ")
            stations = parse_entities(sta_input, mock_station) or None

            obs = mock_observation(
                tick=1,
                position=position,
                health=health,
                energy=energy,
                nearby_resources=resources,
                nearby_hazards=hazards,
                nearby_stations=stations,
            )

            print(f"\n--- Observation ---")
            print(f"  {format_observation_summary(obs)}")

            decision = agent.decide(obs)

            print(f"\n--- Decision ---")
            print(f"  Tool: {decision.tool}")
            if decision.params:
                print(f"  Params: {json.dumps(decision.params)}")
            if decision.reasoning:
                print(f"  Reasoning: \"{decision.reasoning}\"")

            trace = getattr(agent, "last_trace", None)
            if trace:
                tokens = trace.get("tokens_used", 0)
                if tokens:
                    print(f"  Tokens: {tokens}")

            print()
            again = input("Run another? [Y/n]: ").strip().lower()
            if again == "n":
                break
            print()

        except KeyboardInterrupt:
            print("\n")
            break
        except Exception as e:
            print(f"  Error: {e}\n")


# ---------------------------------------------------------------------------
#  CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate agent decisions against scenarios (adapter-agnostic)"
    )
    parser.add_argument(
        "--adapter",
        choices=list(ADAPTERS.keys()),
        default="beginner",
        help=f"Agent adapter to evaluate (default: beginner). Options: {', '.join(ADAPTERS.keys())}",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model name or path (adapter-specific, e.g. model.gguf for llm, claude-haiku-4-5-20251001 for claude)",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default=None,
        help=f"Run a single scenario: {', '.join(SCENARIOS.keys())}",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Interactive mode — input your own observations",
    )

    args = parser.parse_args()

    # Display name
    if args.model:
        display_name = f"{args.adapter} ({args.model})"
    else:
        display_name = args.adapter

    print(f"=== Agent Eval ({display_name}) ===")

    agent = load_agent(args.adapter, args.model)

    if args.interactive:
        interactive_mode(agent)
    else:
        run_all_scenarios(agent, args.scenario)


if __name__ == "__main__":
    main()
