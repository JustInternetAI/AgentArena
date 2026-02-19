"""
CLI tool for inspecting agent reasoning traces from the SDK debug API.

Usage:
    python -m tools.inspect_agent --agent agent_001 --tick 42
    python -m tools.inspect_agent --agent agent_001 --tick-range 40-50
    python -m tools.inspect_agent --all --tick-range 0-100
    python -m tools.inspect_agent --agent agent_001 --latest 5
    python -m tools.inspect_agent --tool move_to
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:
    print("Error: 'requests' library not found. Install with: pip install requests")
    sys.exit(1)


# ── Formatters ───────────────────────────────────────────────────

STAGE_LABELS = {
    "observation": "OBSERVATION",
    "prompt": "PROMPT",
    "llm_response": "LLM RESPONSE",
    "parse": "PARSE",
    "decision": "DECISION",
}


def format_step_header(name: str) -> str:
    label = STAGE_LABELS.get(name, name.upper())
    return f"\n{'=' * 72}\n  {label}\n{'=' * 72}"


def format_observation_step(data: dict[str, Any]) -> str:
    lines = []
    if data.get("position"):
        pos = data["position"]
        lines.append(
            f"Position: [{', '.join(f'{v:.1f}' if isinstance(v, float) else str(v) for v in pos)}]"
        )
    if data.get("health") is not None:
        lines.append(f"Health: {data['health']}")
    if data.get("energy") is not None:
        lines.append(f"Energy: {data['energy']}")
    if data.get("nearby_resources") is not None:
        lines.append(f"Nearby Resources: {data['nearby_resources']}")
    if data.get("nearby_hazards") is not None:
        lines.append(f"Nearby Hazards: {data['nearby_hazards']}")
    return "\n".join(lines)


def format_prompt_step(data: dict[str, Any]) -> str:
    lines = []
    sys_prompt = data.get("system_prompt", "")
    if sys_prompt:
        lines.append(f"System Prompt: {sys_prompt[:100]}{'...' if len(sys_prompt) > 100 else ''}")
    user_prompt = data.get("user_prompt", "")
    if user_prompt:
        lines.append(f"\nUser Prompt:\n{'-' * 72}")
        lines.append(user_prompt)
        lines.append("-" * 72)
    return "\n".join(lines)


def format_llm_response_step(data: dict[str, Any]) -> str:
    lines = []
    if data.get("tokens_used"):
        lines.append(f"Tokens Used: {data['tokens_used']}")
    if data.get("finish_reason"):
        lines.append(f"Finish Reason: {data['finish_reason']}")
    raw = data.get("raw_output", "")
    if raw:
        lines.append(f"\nRaw Output:\n{'-' * 72}")
        lines.append(raw)
        lines.append("-" * 72)
    return "\n".join(lines)


def format_parse_step(data: dict[str, Any]) -> str:
    lines = []
    lines.append(f"Parse Method: {data.get('method', 'unknown')}")
    parsed = data.get("parsed_json")
    if parsed:
        lines.append(f"Parsed JSON: {json.dumps(parsed, indent=2)}")
    return "\n".join(lines)


def format_decision_step(data: dict[str, Any]) -> str:
    lines = []
    lines.append(f"Tool: {data.get('tool')}")
    lines.append(f"Parameters: {json.dumps(data.get('params', {}), indent=2)}")
    if data.get("reasoning"):
        lines.append(f"Reasoning: {data['reasoning']}")
    return "\n".join(lines)


STEP_FORMATTERS = {
    "observation": format_observation_step,
    "prompt": format_prompt_step,
    "llm_response": format_llm_response_step,
    "parse": format_parse_step,
    "decision": format_decision_step,
}


def format_trace(trace: dict[str, Any], verbose: bool = False) -> str:
    lines = []
    lines.append(f"\n{'#' * 72}")
    lines.append(
        f"  TRACE: Agent {trace['agent_id']} - Tick {trace['tick']}  (id: {trace.get('trace_id', '?')})"
    )
    lines.append(f"{'#' * 72}")

    for step in trace.get("steps", []):
        name = step.get("name", "unknown")
        data = step.get("data", {})
        elapsed = step.get("elapsed_ms", 0)

        lines.append(format_step_header(name))
        lines.append(f"  +{elapsed:.1f}ms\n")

        formatter = STEP_FORMATTERS.get(name)
        if formatter:
            lines.append(formatter(data))
        elif verbose:
            lines.append(json.dumps(data, indent=2))
        else:
            summary = json.dumps(data)
            lines.append(summary[:200] + ("..." if len(summary) > 200 else ""))

    return "\n".join(lines)


# ── API ──────────────────────────────────────────────────────────


def fetch_traces(
    base_url: str,
    agent_id: str | None = None,
    tick_start: int | None = None,
    tick_end: int | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Fetch reasoning traces from the SDK debug API."""
    url = f"{base_url}/debug/traces"
    params: dict[str, str | int] = {"limit": limit}

    if agent_id:
        params["agent_id"] = agent_id
    if tick_start is not None:
        params["tick_start"] = tick_start
    if tick_end is not None:
        params["tick_end"] = tick_end

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return list(data.get("traces", []))
    except requests.exceptions.RequestException as e:
        print(f"Error fetching traces: {e}", file=sys.stderr)
        sys.exit(1)


# ── Main ─────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Inspect agent reasoning traces from the SDK debug API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # View a specific agent's traces at tick 42
  python -m tools.inspect_agent --agent agent_001 --tick 42

  # View all traces in a tick range
  python -m tools.inspect_agent --agent agent_001 --tick-range 40-50

  # View the latest 5 traces
  python -m tools.inspect_agent --agent agent_001 --latest 5

  # Filter by tool used
  python -m tools.inspect_agent --tool move_to

  # Export to JSON file
  python -m tools.inspect_agent --agent agent_001 --output traces.json
        """,
    )

    parser.add_argument("--agent", type=str, help="Agent ID to filter by")
    parser.add_argument("--tick", type=int, help="Specific tick number")
    parser.add_argument("--tick-range", type=str, help="Tick range (e.g., 40-50)")
    parser.add_argument(
        "--tool", type=str, help="Filter by tool name (e.g., move_to, collect, idle)"
    )
    parser.add_argument("--latest", type=int, help="Show latest N traces")
    parser.add_argument("--all", action="store_true", help="Show all traces")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")
    parser.add_argument("--output", "-o", type=str, help="Output to JSON file instead of stdout")
    parser.add_argument(
        "--url",
        type=str,
        default="http://127.0.0.1:5000",
        help="IPC server URL (default: http://127.0.0.1:5000)",
    )

    args = parser.parse_args()

    # Parse tick range
    tick_start = None
    tick_end = None
    if args.tick:
        tick_start = args.tick
        tick_end = args.tick
    elif args.tick_range:
        try:
            parts = args.tick_range.split("-")
            tick_start = int(parts[0])
            tick_end = int(parts[1])
        except (ValueError, IndexError):
            print("Error: Invalid tick range format. Use: 40-50", file=sys.stderr)
            sys.exit(1)

    # Fetch traces
    traces = fetch_traces(
        base_url=args.url,
        agent_id=args.agent,
        tick_start=tick_start,
        tick_end=tick_end,
    )

    # Filter by tool if requested
    if args.tool:
        filtered = []
        for t in traces:
            for step in t.get("steps", []):
                if step.get("name") == "decision" and step.get("data", {}).get("tool") == args.tool:
                    filtered.append(t)
                    break
        traces = filtered

    if not traces:
        print("No traces found matching the criteria.", file=sys.stderr)
        sys.exit(0)

    # Apply latest filter
    if args.latest:
        traces = traces[-args.latest :]

    # Output to JSON file
    if args.output:
        output_path = Path(args.output)
        with open(output_path, "w") as f:
            json.dump(traces, f, indent=2)
        print(f"Exported {len(traces)} traces to {output_path}")
        sys.exit(0)

    # Display traces
    print(f"\nFound {len(traces)} trace(s)\n")
    for trace in traces:
        print(format_trace(trace, verbose=args.verbose))
        print()


if __name__ == "__main__":
    main()
