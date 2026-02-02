"""
Memory Inspection CLI Tool for Agent Arena.

This tool provides command-line utilities for inspecting and debugging agent memory,
allowing developers to understand what the agent "remembers" about the world.

Usage:
    python -m tools.inspect_memory --dump [--agent AGENT_ID]
    python -m tools.inspect_memory --query "nearest resource" [--agent AGENT_ID]
    python -m tools.inspect_memory --export --prefix memory_export [--agent AGENT_ID]
    python -m tools.inspect_memory --stats [--agent AGENT_ID]
"""

import argparse
import csv
import json
import logging
import sys
from pathlib import Path

import requests  # type: ignore[import-untyped]

logging.basicConfig(
    level=logging.WARNING,
    format="%(message)s",
)
logger = logging.getLogger(__name__)


def _format_summary(data: dict) -> str:
    """Format memory dump as a human-readable summary."""
    lines = []
    memory_type = data.get("type", "Unknown")
    stats = data.get("stats", {})

    lines.append(f"Memory Type: {memory_type}")
    lines.append("")
    lines.append("Statistics:")

    for key, value in stats.items():
        # Format key nicely
        display_key = key.replace("_", " ").title()
        lines.append(f"  {display_key}: {value}")

    # Type-specific summaries
    if memory_type == "SpatialMemory":
        lines.append("")
        lines.append("Objects by Type:")

        objects_by_type = data.get("objects_by_type", {})
        for obj_type, objects in objects_by_type.items():
            lines.append(f"  {obj_type.title()}: {len(objects)}")
            # Show first few objects
            for obj in objects[:3]:
                name = obj.get("name", "unnamed")
                pos = obj.get("position", [0, 0, 0])
                status = obj.get("status", "active")
                lines.append(
                    f"    - {name} at ({pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f}) [{status}]"
                )
            if len(objects) > 3:
                lines.append(f"    ... and {len(objects) - 3} more")

        experiences = data.get("experiences", [])
        if experiences:
            lines.append("")
            lines.append(f"Recent Experiences ({len(experiences)} total):")
            for exp in experiences[-5:]:
                tick = exp.get("tick", 0)
                event_type = exp.get("event_type", "unknown")
                description = exp.get("description", "")
                lines.append(f"  Tick {tick}: [{event_type}] {description}")

    elif memory_type == "SlidingWindowMemory":
        observations = data.get("observations", [])
        if observations:
            lines.append("")
            lines.append(f"Recent Observations ({len(observations)} total):")
            for obs in observations[-5:]:
                tick = obs.get("tick", 0)
                pos = obs.get("position", [0, 0, 0])
                resources = len(obs.get("nearby_resources", []))
                hazards = len(obs.get("nearby_hazards", []))
                lines.append(
                    f"  Tick {tick}: pos=({pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f}), {resources} resources, {hazards} hazards"
                )

    elif memory_type == "SummarizingMemory":
        summary = data.get("summary", "")
        if summary:
            lines.append("")
            lines.append("Compressed Summary:")
            # Truncate long summaries
            if len(summary) > 500:
                lines.append(f"  {summary[:500]}...")
            else:
                lines.append(f"  {summary}")

    return "\n".join(lines)


def _get_memory_from_server(agent_id: str | None, host: str, port: int) -> dict | None:
    """
    Fetch memory dump from the IPC server.

    Args:
        agent_id: Agent ID to query, or None to auto-detect
        host: Server host
        port: Server port

    Returns:
        Memory dump dictionary or None on error
    """
    base_url = f"http://{host}:{port}"

    try:
        # If no agent specified, try to get list of agents
        if not agent_id:
            # Try the root endpoint to see available agents
            response = requests.get(f"{base_url}/", timeout=5)
            if response.status_code != 200:
                print(f"Error: Server returned status {response.status_code}")
                return None

            data = response.json()
            if data.get("agents", 0) == 0:
                print("No agents registered with the server.")
                return None

            # For now, we need an agent_id
            print("Error: Please specify --agent AGENT_ID")
            print("Hint: Check the server logs or scene to find agent IDs")
            return None

        # Fetch memory for specific agent
        response = requests.get(f"{base_url}/memory/{agent_id}", timeout=5)
        if response.status_code == 404:
            print(f"Error: Agent '{agent_id}' not found")
            return None
        elif response.status_code != 200:
            print(f"Error: Server returned status {response.status_code}")
            return None

        result = response.json()
        if not result.get("success"):
            print(f"Error: {result.get('error', 'Unknown error')}")
            return None

        memory: dict | None = result.get("memory")
        return memory

    except requests.exceptions.ConnectionError:
        print(f"Error: Cannot connect to server at {base_url}")
        print("Make sure the IPC server is running (python run_server.py)")
        return None
    except requests.exceptions.Timeout:
        print("Error: Server request timed out")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None


def cmd_dump(args: argparse.Namespace) -> int:
    """Dump memory state to stdout or file."""
    memory = _get_memory_from_server(args.agent, args.host, args.port)
    if not memory:
        return 1

    if args.format == "json":
        output = json.dumps(memory, indent=2)
    else:  # summary
        output = _format_summary(memory)

    if args.output:
        Path(args.output).write_text(output)
        print(f"Wrote memory dump to {args.output}")
    else:
        print(output)

    return 0


def cmd_query(args: argparse.Namespace) -> int:
    """Query memory semantically."""
    # This would require calling an endpoint that does semantic search
    # For now, we can implement a simple client-side filter
    memory = _get_memory_from_server(args.agent, args.host, args.port)
    if not memory:
        return 1

    memory_type = memory.get("type", "Unknown")
    query_lower = args.query.lower()

    print(f"Searching for: {args.query}")
    print(f"Memory type: {memory_type}")
    print("-" * 40)

    results = []

    if memory_type == "SpatialMemory":
        # Search through objects
        for obj in memory.get("objects", []):
            name = obj.get("name", "").lower()
            obj_type = obj.get("object_type", "").lower()
            subtype = obj.get("subtype", "").lower()

            # Simple text matching
            if query_lower in name or query_lower in obj_type or query_lower in subtype:
                results.append(obj)

        if results:
            print(f"Found {len(results)} matching objects:")
            for obj in results[: args.limit]:
                name = obj.get("name")
                obj_type = obj.get("object_type")
                subtype = obj.get("subtype")
                pos = obj.get("position", [0, 0, 0])
                status = obj.get("status", "active")
                print(
                    f"  - {name} ({obj_type}/{subtype}) at ({pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f}) [{status}]"
                )
        else:
            print("No matching objects found.")

    else:
        print(f"Query not supported for memory type: {memory_type}")
        print("Hint: Use --dump to see full memory contents")
        return 1

    return 0


def cmd_export(args: argparse.Namespace) -> int:
    """Export memory to CSV files."""
    memory = _get_memory_from_server(args.agent, args.host, args.port)
    if not memory:
        return 1

    memory_type = memory.get("type", "Unknown")

    if memory_type == "SpatialMemory":
        # Export objects
        objects = memory.get("objects", [])
        if objects:
            objects_file = f"{args.prefix}_objects.csv"
            with open(objects_file, "w", newline="", encoding="utf-8") as f:
                fieldnames = [
                    "name",
                    "type",
                    "subtype",
                    "position_x",
                    "position_y",
                    "position_z",
                    "status",
                    "last_seen_tick",
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for obj in objects:
                    pos = obj.get("position", [0, 0, 0])
                    writer.writerow(
                        {
                            "name": obj.get("name", ""),
                            "type": obj.get("object_type", ""),
                            "subtype": obj.get("subtype", ""),
                            "position_x": pos[0] if len(pos) > 0 else 0,
                            "position_y": pos[1] if len(pos) > 1 else 0,
                            "position_z": pos[2] if len(pos) > 2 else 0,
                            "status": obj.get("status", "active"),
                            "last_seen_tick": obj.get("last_seen_tick", 0),
                        }
                    )
            print(f"Exported {len(objects)} objects to {objects_file}")

        # Export experiences
        experiences = memory.get("experiences", [])
        if experiences:
            exp_file = f"{args.prefix}_experiences.csv"
            with open(exp_file, "w", newline="", encoding="utf-8") as f:
                fieldnames = [
                    "tick",
                    "event_type",
                    "description",
                    "position_x",
                    "position_y",
                    "position_z",
                    "object_name",
                    "damage_taken",
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for exp in experiences:
                    pos = exp.get("position", [0, 0, 0])
                    writer.writerow(
                        {
                            "tick": exp.get("tick", 0),
                            "event_type": exp.get("event_type", ""),
                            "description": exp.get("description", ""),
                            "position_x": pos[0] if len(pos) > 0 else 0,
                            "position_y": pos[1] if len(pos) > 1 else 0,
                            "position_z": pos[2] if len(pos) > 2 else 0,
                            "object_name": exp.get("object_name", ""),
                            "damage_taken": exp.get("damage_taken", 0),
                        }
                    )
            print(f"Exported {len(experiences)} experiences to {exp_file}")

    elif memory_type in ("SlidingWindowMemory", "RAGMemory", "RAGMemoryV2"):
        # Export observations
        observations = memory.get("observations", []) or memory.get("recent_observations", [])
        if observations:
            obs_file = f"{args.prefix}_observations.csv"
            with open(obs_file, "w", newline="", encoding="utf-8") as f:
                fieldnames = [
                    "tick",
                    "position_x",
                    "position_y",
                    "position_z",
                    "health",
                    "energy",
                    "resource_count",
                    "hazard_count",
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for obs in observations:
                    pos = obs.get("position", [0, 0, 0])
                    writer.writerow(
                        {
                            "tick": obs.get("tick", 0),
                            "position_x": pos[0] if len(pos) > 0 else 0,
                            "position_y": pos[1] if len(pos) > 1 else 0,
                            "position_z": pos[2] if len(pos) > 2 else 0,
                            "health": obs.get("health", 100),
                            "energy": obs.get("energy", 100),
                            "resource_count": len(obs.get("nearby_resources", [])),
                            "hazard_count": len(obs.get("nearby_hazards", [])),
                        }
                    )
            print(f"Exported {len(observations)} observations to {obs_file}")

    else:
        print(f"Export not implemented for memory type: {memory_type}")
        return 1

    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    """Show memory statistics."""
    memory = _get_memory_from_server(args.agent, args.host, args.port)
    if not memory:
        return 1

    memory_type = memory.get("type", "Unknown")
    stats = memory.get("stats", {})

    print(f"Memory Type: {memory_type}")
    print("")
    print("Statistics:")
    for key, value in stats.items():
        display_key = key.replace("_", " ").title()
        print(f"  {display_key}: {value}")

    return 0


def main() -> int:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Memory Inspection Tool for Agent Arena",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dump memory as JSON
  python -m tools.inspect_memory --dump --agent foraging_agent_001

  # Dump memory summary
  python -m tools.inspect_memory --dump --format summary --agent foraging_agent_001

  # Save dump to file
  python -m tools.inspect_memory --dump -o memory.json --agent foraging_agent_001

  # Query memory for resources
  python -m tools.inspect_memory --query "wood" --agent foraging_agent_001

  # Export to CSV for spreadsheet analysis
  python -m tools.inspect_memory --export --prefix agent001 --agent foraging_agent_001

  # Show memory statistics
  python -m tools.inspect_memory --stats --agent foraging_agent_001
""",
    )

    # Commands (mutually exclusive)
    commands = parser.add_mutually_exclusive_group(required=True)
    commands.add_argument(
        "--dump",
        action="store_true",
        help="Dump full memory state",
    )
    commands.add_argument(
        "--query",
        "-q",
        type=str,
        metavar="TEXT",
        help="Query memory for matching objects",
    )
    commands.add_argument(
        "--export",
        action="store_true",
        help="Export memory to CSV files",
    )
    commands.add_argument(
        "--stats",
        action="store_true",
        help="Show memory statistics",
    )

    # Options
    parser.add_argument(
        "--agent",
        "-a",
        type=str,
        metavar="AGENT_ID",
        help="Agent ID to inspect",
    )
    parser.add_argument(
        "--format",
        choices=["json", "summary"],
        default="json",
        help="Output format for dump (default: json)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output file (default: stdout)",
    )
    parser.add_argument(
        "--prefix",
        default="memory",
        help="Prefix for CSV export files (default: memory)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Limit results for query (default: 10)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="IPC server host (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="IPC server port (default: 5000)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Dispatch to command handler
    if args.dump:
        return cmd_dump(args)
    elif args.query:
        return cmd_query(args)
    elif args.export:
        return cmd_export(args)
    elif args.stats:
        return cmd_stats(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
