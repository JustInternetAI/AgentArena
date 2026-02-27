"""
LLM Agent Eval Harness

Evaluate your agent's decisions against predefined scenarios or
custom observations — no Godot, no game connection needed.

Supports local models (llama-cpp), Claude API, and OpenAI API.

Usage:
    # All scenarios with Claude
    python eval_agent.py --provider claude

    # Single scenario
    python eval_agent.py --provider claude --scenario hazard_escape

    # Interactive mode — input your own observations
    python eval_agent.py --interactive --provider claude

    # With local model
    python eval_agent.py --model path/to/model.gguf

    # With OpenAI
    python eval_agent.py --provider openai --model gpt-4o
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Ensure SDK is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "python" / "sdk"))
sys.path.insert(0, str(Path(__file__).parent))

from agent_arena_sdk.testing import (
    mock_hazard,
    mock_observation,
    mock_resource,
    mock_station,
)
from agent import Agent


# ---------------------------------------------------------------------------
#  API Client wrappers (drop-in replacements for LLMClient.generate())
# ---------------------------------------------------------------------------


class ClaudeClient:
    """Drop-in for LLMClient using Anthropic API."""

    def __init__(self, model: str = "claude-sonnet-4-20250514", api_key: str | None = None):
        from anthropic import Anthropic

        self.client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
        self.model = model

    def generate(self, prompt, tools=None, temperature=None, system_prompt=None):
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system_prompt or "",
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
        return {
            "text": text,
            "tool_call": None,
            "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
            "finish_reason": response.stop_reason,
        }


class OpenAIClient:
    """Drop-in for LLMClient using OpenAI API."""

    def __init__(self, model: str = "gpt-4o", api_key: str | None = None):
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))
        self.model = model

    def generate(self, prompt, tools=None, temperature=None, system_prompt=None):
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=1024,
        )
        text = response.choices[0].message.content or ""
        return {
            "text": text,
            "tool_call": None,
            "tokens_used": response.usage.total_tokens if response.usage else 0,
            "finish_reason": response.choices[0].finish_reason,
        }


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


def make_agent(provider: str, model: str | None) -> Agent:
    """Create an Agent with the specified LLM backend."""
    if provider == "local":
        model_path = model or "models/llama-2-7b/gguf/q4/model.gguf"
        return Agent(model_path=model_path)
    elif provider == "claude":
        client = ClaudeClient(model=model or "claude-sonnet-4-20250514")
        return Agent(llm_client=client)
    elif provider == "openai":
        client = OpenAIClient(model=model or "gpt-4o")
        return Agent(llm_client=client)
    else:
        print(f"Unknown provider: {provider}")
        sys.exit(1)


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


def run_scenario(agent: Agent, name: str, scenario: dict, index: int, total: int) -> dict:
    """Run a single scenario and display the result."""
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
    if agent.last_trace:
        tokens = agent.last_trace.get("tokens_used", 0)
        if tokens:
            print(f"  Tokens: {tokens}")

    return {
        "scenario": name,
        "tool": decision.tool,
        "params": decision.params,
        "reasoning": decision.reasoning,
        "tokens": agent.last_trace.get("tokens_used", 0) if agent.last_trace else 0,
    }


def run_all_scenarios(agent: Agent, scenario_filter: str | None = None):
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
            # Just a type name with default position
            entities.append(factory(entry))
            continue
        type_name, coords = entry.split(":", 1)
        pos = parse_position(coords)
        # Calculate distance from origin (will be overridden if agent position differs)
        dist = (pos[0] ** 2 + pos[1] ** 2 + pos[2] ** 2) ** 0.5
        entities.append(factory(type_name.strip(), position=pos, distance=max(dist, 0.1)))
    return entities


def interactive_mode(agent: Agent):
    """Prompt user for observation params, run agent, display result. Loop."""
    print("\n== Interactive Eval Mode ==")
    print("Enter observation parameters (empty = default, 'q' to quit)\n")

    while True:
        try:
            # Gather inputs
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

            # Build observation
            obs = mock_observation(
                tick=1,
                position=position,
                health=health,
                energy=energy,
                nearby_resources=resources,
                nearby_hazards=hazards,
                nearby_stations=stations,
            )

            # Display observation
            print(f"\n--- Observation ---")
            print(f"  {format_observation_summary(obs)}")

            # Run agent
            decision = agent.decide(obs)

            # Display result
            print(f"\n--- Decision ---")
            print(f"  Tool: {decision.tool}")
            if decision.params:
                print(f"  Params: {json.dumps(decision.params)}")
            if decision.reasoning:
                print(f"  Reasoning: \"{decision.reasoning}\"")
            if agent.last_trace:
                tokens = agent.last_trace.get("tokens_used", 0)
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
        description="Evaluate LLM agent decisions against scenarios"
    )
    parser.add_argument(
        "--provider",
        choices=["local", "claude", "openai"],
        default="local",
        help="LLM provider (default: local)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model name or path (provider-specific)",
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

    # Determine display name
    if args.provider == "local":
        display_name = args.model or "local model"
    elif args.provider == "claude":
        display_name = args.model or "claude-sonnet-4-20250514"
    else:
        display_name = args.model or "gpt-4o"

    print(f"=== LLM Agent Eval ({display_name}) ===")

    agent = make_agent(args.provider, args.model)

    if args.interactive:
        interactive_mode(agent)
    else:
        run_all_scenarios(agent, args.scenario)


if __name__ == "__main__":
    main()
