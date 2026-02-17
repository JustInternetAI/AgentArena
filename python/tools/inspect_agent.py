"""
CLI tool for inspecting agent reasoning traces captured by the TraceStore.

Usage:
    python -m tools.inspect_agent --agent agent_001 --tick 42
    python -m tools.inspect_agent --agent agent_001 --tick-range 40-50
    python -m tools.inspect_agent --all --tick-range 0-100
    python -m tools.inspect_agent --agent agent_001 --latest 5
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


def format_stage_header(stage: str) -> str:
    """Format a stage header with visual separation."""
    stage_names = {
        "observation": "📋 OBSERVATION",
        "prompt_building": "🔨 PROMPT BUILDING",
        "llm_request": "📤 LLM REQUEST",
        "llm_response": "📥 LLM RESPONSE",
        "decision": "✅ DECISION"
    }
    name = stage_names.get(stage, stage.upper())
    return f"\n{'=' * 80}\n{name}\n{'=' * 80}"


def format_observation(data: dict[str, Any]) -> str:
    """Format observation data for display."""
    lines = []
    lines.append(f"Agent: {data.get('agent_id')}")
    lines.append(f"Tick: {data.get('tick')}")
    lines.append(f"Position: {data.get('position')}")
    lines.append(f"Health: {data.get('health')}")
    lines.append(f"Energy: {data.get('energy')}")

    resources = data.get('nearby_resources', [])
    if resources:
        lines.append(f"\nNearby Resources ({len(resources)}):")
        for r in resources[:5]:  # Limit to first 5
            lines.append(f"  - {r['name']} ({r['type']}) at distance {r['distance']:.1f}")

    hazards = data.get('nearby_hazards', [])
    if hazards:
        lines.append(f"\nNearby Hazards ({len(hazards)}):")
        for h in hazards[:5]:  # Limit to first 5
            lines.append(f"  - {h['name']} ({h['type']}) at distance {h['distance']:.1f}")

    inventory = data.get('inventory', [])
    if inventory:
        lines.append(f"\nInventory ({len(inventory)} items):")
        for item in inventory:
            lines.append(f"  - {item['name']} x{item['quantity']}")

    return "\n".join(lines)


def format_prompt_building(data: dict[str, Any]) -> str:
    """Format prompt building data for display."""
    lines = []
    lines.append(f"System Prompt: {data.get('system_prompt', '')[:100]}...")

    memory = data.get('memory_context', {})
    lines.append(f"\nMemory Context: {memory.get('count', 0)} observations")
    if memory.get('items'):
        for item in memory['items'][:3]:
            lines.append(f"  - Tick {item['tick']}: {item['position']}")

    lines.append(f"\nPrompt Length: {data.get('prompt_length')} chars (~{data.get('estimated_tokens')} tokens)")
    lines.append("\nFull Prompt:")
    lines.append("-" * 80)
    lines.append(data.get('final_prompt', ''))
    lines.append("-" * 80)

    return "\n".join(lines)


def format_llm_request(data: dict[str, Any]) -> str:
    """Format LLM request data for display."""
    lines = []
    lines.append(f"Model: {data.get('model', 'unknown')}")
    lines.append(f"Temperature: {data.get('temperature')}")
    lines.append(f"Max Tokens: {data.get('max_tokens')}")

    tools = data.get('tools', [])
    lines.append(f"\nAvailable Tools ({len(tools)}):")
    for tool in tools:
        lines.append(f"  - {tool['name']}: {tool['description']}")

    return "\n".join(lines)


def format_llm_response(data: dict[str, Any]) -> str:
    """Format LLM response data for display."""
    lines = []
    lines.append(f"Latency: {data.get('latency_ms', 0):.0f}ms")
    lines.append(f"Tokens Used: {data.get('tokens_used')}")
    lines.append(f"Finish Reason: {data.get('finish_reason')}")

    metadata = data.get('metadata', {})
    if metadata:
        lines.append("\nMetadata:")
        if 'parsed_tool_call' in metadata:
            lines.append(f"  Parsed Tool Call: {json.dumps(metadata['parsed_tool_call'], indent=2)}")
        elif 'tool_call' in metadata:
            lines.append(f"  Tool Call: {json.dumps(metadata['tool_call'], indent=2)}")

    lines.append("\nRaw LLM Response:")
    lines.append("-" * 80)
    lines.append(data.get('raw_text', ''))
    lines.append("-" * 80)

    return "\n".join(lines)


def format_decision(data: dict[str, Any]) -> str:
    """Format decision data for display."""
    lines = []
    lines.append(f"Tool: {data.get('tool')}")
    lines.append(f"Parameters: {json.dumps(data.get('params', {}), indent=2)}")
    lines.append(f"Reasoning: {data.get('reasoning')}")
    lines.append(f"Total Latency: {data.get('total_latency_ms', 0):.0f}ms")

    if 'error' in data:
        lines.append(f"\n⚠️  Error: {data['error']}")

    return "\n".join(lines)


def format_capture(capture: dict[str, Any], verbose: bool = False) -> str:
    """Format a complete decision capture for display."""
    lines = []
    lines.append("\n" + "=" * 80)
    lines.append(f"DECISION CAPTURE: Agent {capture['agent_id']} - Tick {capture['tick']}")
    lines.append(f"Start Time: {capture['start_time']}")
    lines.append("=" * 80)

    # Format each stage
    for entry in capture.get('entries', []):
        stage = entry['stage']
        data = entry['data']

        lines.append(format_stage_header(stage))
        lines.append(f"Timestamp: {entry['timestamp']}\n")

        if stage == 'observation':
            lines.append(format_observation(data))
        elif stage == 'prompt_building':
            lines.append(format_prompt_building(data))
        elif stage == 'llm_request':
            if verbose:
                lines.append(format_llm_request(data))
            else:
                lines.append(f"Model: {data.get('model')}, Tools: {len(data.get('tools', []))}")
        elif stage == 'llm_response':
            lines.append(format_llm_response(data))
        elif stage == 'decision':
            lines.append(format_decision(data))

    return "\n".join(lines)


def fetch_captures(
    base_url: str,
    agent_id: str | None = None,
    tick: int | None = None,
    tick_start: int | None = None,
    tick_end: int | None = None
) -> list[dict[str, Any]]:
    """Fetch captures from the IPC server."""
    url = f"{base_url}/inspector/requests"
    params = {}

    if agent_id:
        params['agent_id'] = agent_id
    if tick is not None:
        params['tick'] = tick
    if tick_start is not None:
        params['tick_start'] = tick_start
    if tick_end is not None:
        params['tick_end'] = tick_end

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get('captures', [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching captures: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Inspect agent reasoning traces captured by the TraceStore",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # View a specific agent decision at tick 42
  python -m tools.inspect_agent --agent agent_001 --tick 42

  # View all decisions for an agent in a tick range
  python -m tools.inspect_agent --agent agent_001 --tick-range 40-50

  # View the latest 5 decisions for an agent
  python -m tools.inspect_agent --agent agent_001 --latest 5

  # View all captures in verbose mode
  python -m tools.inspect_agent --all --verbose

  # Export to JSON file
  python -m tools.inspect_agent --agent agent_001 --output decisions.json
        """
    )

    parser.add_argument('--agent', type=str, help='Agent ID to filter by')
    parser.add_argument('--tick', type=int, help='Specific tick number')
    parser.add_argument('--tick-range', type=str, help='Tick range (e.g., 40-50)')
    parser.add_argument('--latest', type=int, help='Show latest N captures')
    parser.add_argument('--all', action='store_true', help='Show all captures')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed output')
    parser.add_argument('--output', '-o', type=str, help='Output to JSON file instead of stdout')
    parser.add_argument('--url', type=str, default='http://127.0.0.1:5000',
                        help='IPC server URL (default: http://127.0.0.1:5000)')

    args = parser.parse_args()

    # Parse tick range if provided
    tick_start = None
    tick_end = None
    if args.tick_range:
        try:
            parts = args.tick_range.split('-')
            tick_start = int(parts[0])
            tick_end = int(parts[1])
        except (ValueError, IndexError):
            print("Error: Invalid tick range format. Use: 40-50", file=sys.stderr)
            sys.exit(1)

    # Fetch captures
    captures = fetch_captures(
        base_url=args.url,
        agent_id=args.agent,
        tick=args.tick,
        tick_start=tick_start,
        tick_end=tick_end
    )

    if not captures:
        print("No captures found matching the criteria.", file=sys.stderr)
        sys.exit(0)

    # Apply latest filter if requested
    if args.latest:
        captures = captures[-args.latest:]

    # Output to JSON file if requested
    if args.output:
        output_path = Path(args.output)
        with open(output_path, 'w') as f:
            json.dump(captures, f, indent=2)
        print(f"Exported {len(captures)} captures to {output_path}")
        sys.exit(0)

    # Display captures
    print(f"\nFound {len(captures)} capture(s)\n")
    for capture in captures:
        print(format_capture(capture, verbose=args.verbose))
        print("\n")


if __name__ == '__main__':
    main()
