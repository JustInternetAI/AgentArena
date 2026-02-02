"""
Agent Inspection CLI Tool for Agent Arena.

This tool provides command-line utilities for inspecting agent reasoning traces,
allowing developers to debug and understand their agent's decision-making process.

Usage:
    python -m tools.inspect_agent --last-decision [--agent AGENT_ID]
    python -m tools.inspect_agent --watch [--agent AGENT_ID]
    python -m tools.inspect_agent --episode EPISODE_ID [--agent AGENT_ID]
    python -m tools.inspect_agent --list-agents
    python -m tools.inspect_agent --list-episodes --agent AGENT_ID
"""

import argparse
import importlib.util
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

# Add parent directory to path for imports
python_dir = Path(__file__).parent.parent
sys.path.insert(0, str(python_dir))


def _load_reasoning_trace_module():
    """Load the reasoning_trace module directly to avoid heavy dependencies."""
    spec = importlib.util.spec_from_file_location(
        "agent_runtime.reasoning_trace", python_dir / "agent_runtime" / "reasoning_trace.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["agent_runtime.reasoning_trace"] = module
    spec.loader.exec_module(module)
    return module


_rt = _load_reasoning_trace_module()
ReasoningTrace = _rt.ReasoningTrace
TraceStore = _rt.TraceStore

logging.basicConfig(
    level=logging.WARNING,  # Suppress INFO logs from TraceStore
    format="%(message)s",  # Simple format for CLI output
)
logger = logging.getLogger(__name__)

# Suppress TraceStore initialization logs
logging.getLogger("agent_runtime.reasoning_trace").setLevel(logging.WARNING)


def print_trace_tree(trace: Any, max_data_length: int = 100) -> None:
    """Print a trace in tree format."""
    print(trace.format_tree(max_data_length))
    print()


def print_trace_json(trace: Any) -> None:
    """Print a trace as JSON."""
    print(json.dumps(trace.to_dict(), indent=2, default=str))
    print()


def cmd_last_decision(args: argparse.Namespace) -> int:
    """Show the last decision trace for an agent."""
    store = TraceStore(args.traces_dir) if args.traces_dir else TraceStore.get_instance()

    # If no agent specified, try to find one
    agent_id = args.agent
    if not agent_id:
        agents = store.list_agents()
        if not agents:
            print("No agents found. Run an agent with tracing enabled first.")
            return 1
        agent_id = agents[0]
        print(f"Using agent: {agent_id}")

    trace = store.get_last_decision(agent_id)
    if trace is None:
        print(f"No traces found for agent '{agent_id}'")
        return 1

    if args.format == "json":
        print_trace_json(trace)
    else:
        print_trace_tree(trace, args.max_length)

    return 0


def cmd_watch(args: argparse.Namespace) -> int:
    """Watch for new traces in real-time."""
    store = TraceStore(args.traces_dir) if args.traces_dir else TraceStore.get_instance()

    # If no agent specified, try to find one
    agent_id = args.agent
    if not agent_id:
        agents = store.list_agents()
        if not agents:
            print("No agents found. Start an agent with tracing enabled.")
            print("Waiting for traces...")
            # Wait for an agent to appear
            while not agents:
                time.sleep(1)
                agents = store.list_agents()
        agent_id = agents[0]

    print(f"Watching traces for agent: {agent_id}")
    print("Press Ctrl+C to stop\n")
    print("=" * 60)

    def on_trace(trace: Any) -> None:
        if args.format == "json":
            print_trace_json(trace)
        else:
            print_trace_tree(trace, args.max_length)
        print("-" * 60)

    stop = store.watch(agent_id, on_trace, poll_interval=args.poll_interval)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping watch...")
        stop()

    return 0


def cmd_episode(args: argparse.Namespace) -> int:
    """Show all traces for a specific episode."""
    store = TraceStore(args.traces_dir) if args.traces_dir else TraceStore.get_instance()

    if not args.agent:
        print("Error: --agent is required for --episode")
        return 1

    traces = store.get_episode_traces(args.agent, args.episode)
    if not traces:
        print(f"No traces found for episode '{args.episode}' of agent '{args.agent}'")
        return 1

    print(f"Episode: {args.episode}")
    print(f"Agent: {args.agent}")
    print(f"Traces: {len(traces)}")
    print("=" * 60)

    for trace in traces:
        if args.format == "json":
            print_trace_json(trace)
        else:
            print_trace_tree(trace, args.max_length)
        print("-" * 60)

    return 0


def cmd_list_agents(args: argparse.Namespace) -> int:
    """List all agents with traces."""
    store = TraceStore(args.traces_dir) if args.traces_dir else TraceStore.get_instance()

    agents = store.list_agents()
    if not agents:
        print("No agents found.")
        return 0

    print("Agents with traces:")
    for agent_id in agents:
        episodes = store.list_episodes(agent_id)
        print(f"  {agent_id} ({len(episodes)} episodes)")

    return 0


def cmd_list_episodes(args: argparse.Namespace) -> int:
    """List all episodes for an agent."""
    store = TraceStore(args.traces_dir) if args.traces_dir else TraceStore.get_instance()

    if not args.agent:
        print("Error: --agent is required for --list-episodes")
        return 1

    episodes = store.list_episodes(args.agent)
    if not episodes:
        print(f"No episodes found for agent '{args.agent}'")
        return 0

    print(f"Episodes for {args.agent}:")
    for episode_id in episodes:
        traces = store.get_episode_traces(args.agent, episode_id)
        print(f"  {episode_id} ({len(traces)} traces)")

    return 0


def main() -> int:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Agent Inspection Tool for Agent Arena",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # View the last decision trace
  python -m tools.inspect_agent --last-decision

  # Watch traces in real-time
  python -m tools.inspect_agent --watch --agent foraging_agent_001

  # View all traces for an episode
  python -m tools.inspect_agent --episode ep_123456 --agent foraging_agent_001

  # List all agents with traces
  python -m tools.inspect_agent --list-agents

  # List episodes for an agent
  python -m tools.inspect_agent --list-episodes --agent foraging_agent_001
""",
    )

    # Commands (mutually exclusive)
    commands = parser.add_mutually_exclusive_group(required=True)
    commands.add_argument(
        "--last-decision",
        action="store_true",
        help="Show the last decision trace",
    )
    commands.add_argument(
        "--watch",
        action="store_true",
        help="Watch for new traces in real-time",
    )
    commands.add_argument(
        "--episode",
        type=str,
        metavar="EPISODE_ID",
        help="Show all traces for a specific episode",
    )
    commands.add_argument(
        "--list-agents",
        action="store_true",
        help="List all agents with traces",
    )
    commands.add_argument(
        "--list-episodes",
        action="store_true",
        help="List all episodes for an agent",
    )

    # Options
    parser.add_argument(
        "--agent",
        type=str,
        metavar="AGENT_ID",
        help="Agent ID to inspect (auto-detected if only one agent)",
    )
    parser.add_argument(
        "--format",
        choices=["tree", "json"],
        default="tree",
        help="Output format (default: tree)",
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=100,
        help="Maximum length for data previews in tree view (default: 100)",
    )
    parser.add_argument(
        "--traces-dir",
        type=Path,
        help="Directory where traces are stored (default: ~/.agent_arena/traces)",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=0.5,
        help="Poll interval for watch mode in seconds (default: 0.5)",
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
    if args.last_decision:
        return cmd_last_decision(args)
    elif args.watch:
        return cmd_watch(args)
    elif args.episode:
        return cmd_episode(args)
    elif args.list_agents:
        return cmd_list_agents(args)
    elif args.list_episodes:
        return cmd_list_episodes(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
