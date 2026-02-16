"""
Helper script to test the Prompt Inspector with a Godot simulation.

This script helps you monitor and analyze captured prompt data in real-time
while running a Godot simulation.

Usage:
1. Start your IPC server with LocalLLMBehavior (e.g., run_local_llm_forager.py)
2. Run this script: python test_inspector_with_godot.py
3. Start the Godot simulation
4. Use the interactive menu to view captured data

The script will continuously check for new captures and display them.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import requests

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))


def print_separator(char="=", length=80):
    """Print a separator line."""
    print(char * length)


def print_header(title: str):
    """Print a section header."""
    print(f"\n{title}")
    print_separator()


def check_inspector_status(base_url: str):
    """Check if inspector is available and enabled."""
    try:
        response = requests.get(f"{base_url}/inspector/config", timeout=2)
        if response.status_code == 200:
            config = response.json()
            return config
        return None
    except requests.RequestException:
        return None


def get_captures(base_url: str, agent_id: str = None, tick: int = None):
    """Get captures from the inspector."""
    params = {}
    if agent_id:
        params["agent_id"] = agent_id
    if tick is not None:
        params["tick"] = tick

    try:
        response = requests.get(f"{base_url}/inspector/requests", params=params, timeout=5)
        if response.status_code == 200:
            return response.json()
        return []
    except requests.RequestException as e:
        print(f"Error fetching captures: {e}")
        return []


def display_capture_summary(capture: dict):
    """Display a summary of a single capture."""
    print(f"\nAgent: {capture['agent_id']} | Tick: {capture['tick']}")
    print(f"Start time: {capture['start_time']}")
    print(f"Stages captured: {len(capture['entries'])}")

    for entry in capture["entries"]:
        stage = entry["stage"]
        data = entry["data"]

        if stage == "observation":
            print(f"  📍 Observation:")
            print(f"     Position: {data.get('position', 'N/A')}")
            print(f"     Health: {data.get('health', 'N/A')}")
            print(f"     Nearby resources: {len(data.get('nearby_resources', []))}")
            print(f"     Nearby hazards: {len(data.get('nearby_hazards', []))}")

        elif stage == "prompt_building":
            print(f"  📝 Prompt Building:")
            print(f"     Prompt length: {data.get('prompt_length', 'N/A')} chars")
            print(f"     Estimated tokens: {data.get('estimated_tokens', 'N/A')}")
            print(f"     Memory items: {data.get('memory_context', {}).get('count', 0)}")

        elif stage == "llm_request":
            print(f"  🔄 LLM Request:")
            print(f"     Model: {data.get('model', 'N/A')}")
            print(f"     Tools available: {len(data.get('tools', []))}")
            print(f"     Temperature: {data.get('temperature', 'N/A')}")

        elif stage == "llm_response":
            print(f"  💬 LLM Response:")
            print(f"     Tokens used: {data.get('tokens_used', 'N/A')}")
            print(f"     Latency: {data.get('latency_ms', 0):.0f}ms")
            print(f"     Finish reason: {data.get('finish_reason', 'N/A')}")
            raw_text = data.get("raw_text", "")
            preview = raw_text[:80] + "..." if len(raw_text) > 80 else raw_text
            print(f"     Response: {preview}")

        elif stage == "decision":
            print(f"  ✅ Decision:")
            print(f"     Tool: {data.get('tool', 'N/A')}")
            print(f"     Params: {data.get('params', {})}")
            reasoning = data.get("reasoning", "")
            preview = reasoning[:80] + "..." if len(reasoning) > 80 else reasoning
            print(f"     Reasoning: {preview}")
            print(f"     Total latency: {data.get('total_latency_ms', 0):.0f}ms")


def display_detailed_capture(capture: dict):
    """Display full details of a capture."""
    print_header(f"Capture Details: Agent {capture['agent_id']} - Tick {capture['tick']}")
    print(json.dumps(capture, indent=2))


def analyze_performance(captures: list):
    """Analyze performance metrics across captures."""
    if not captures:
        print("No captures to analyze.")
        return

    print_header("Performance Analysis")

    latencies = []
    token_counts = []
    decisions_by_tool = {}

    for capture in captures:
        for entry in capture["entries"]:
            if entry["stage"] == "llm_response":
                latencies.append(entry["data"].get("latency_ms", 0))
                token_counts.append(entry["data"].get("tokens_used", 0))

            if entry["stage"] == "decision":
                tool = entry["data"].get("tool", "unknown")
                decisions_by_tool[tool] = decisions_by_tool.get(tool, 0) + 1

    if latencies:
        print(f"Total decisions: {len(latencies)}")
        print(f"\nLatency (ms):")
        print(f"  Average: {sum(latencies) / len(latencies):.1f}")
        print(f"  Min: {min(latencies):.1f}")
        print(f"  Max: {max(latencies):.1f}")

        print(f"\nToken usage:")
        print(f"  Average: {sum(token_counts) / len(token_counts):.1f}")
        print(f"  Min: {min(token_counts)}")
        print(f"  Max: {max(token_counts)}")

        print(f"\nDecisions by tool:")
        for tool, count in sorted(decisions_by_tool.items(), key=lambda x: x[1], reverse=True):
            print(f"  {tool}: {count}")


def monitor_mode(base_url: str, agent_id: str, interval: int = 2):
    """Monitor for new captures in real-time."""
    print_header(f"Monitoring captures for agent: {agent_id}")
    print(f"Checking every {interval} seconds. Press Ctrl+C to stop.\n")

    last_tick = -1

    try:
        while True:
            captures = get_captures(base_url, agent_id=agent_id)

            if captures:
                # Find newest capture
                newest = max(captures, key=lambda c: c["tick"])
                if newest["tick"] > last_tick:
                    last_tick = newest["tick"]
                    print(f"\n[New Capture] Tick {newest['tick']}")
                    display_capture_summary(newest)

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")


def interactive_menu(base_url: str, agent_id: str):
    """Interactive menu for viewing captures."""
    while True:
        print_separator()
        print("\nPrompt Inspector - Interactive Menu")
        print_separator()
        print("1. View latest capture")
        print("2. View specific tick")
        print("3. View all captures (summary)")
        print("4. View all captures (detailed)")
        print("5. Analyze performance")
        print("6. Export to JSON file")
        print("7. Clear all captures")
        print("8. Monitor mode (real-time)")
        print("9. Change agent ID")
        print("0. Exit")
        print_separator()

        choice = input("\nEnter choice: ").strip()

        if choice == "0":
            print("Goodbye!")
            break

        elif choice == "1":
            captures = get_captures(base_url, agent_id=agent_id)
            if captures:
                latest = max(captures, key=lambda c: c["tick"])
                display_capture_summary(latest)
            else:
                print("No captures found.")

        elif choice == "2":
            tick = input("Enter tick number: ").strip()
            try:
                tick = int(tick)
                captures = get_captures(base_url, agent_id=agent_id, tick=tick)
                if captures:
                    display_capture_summary(captures[0])
                else:
                    print(f"No capture found for tick {tick}.")
            except ValueError:
                print("Invalid tick number.")

        elif choice == "3":
            captures = get_captures(base_url, agent_id=agent_id)
            if captures:
                print(f"\nFound {len(captures)} captures:")
                for capture in sorted(captures, key=lambda c: c["tick"]):
                    display_capture_summary(capture)
            else:
                print("No captures found.")

        elif choice == "4":
            captures = get_captures(base_url, agent_id=agent_id)
            if captures:
                for capture in sorted(captures, key=lambda c: c["tick"]):
                    display_detailed_capture(capture)
            else:
                print("No captures found.")

        elif choice == "5":
            captures = get_captures(base_url, agent_id=agent_id)
            analyze_performance(captures)

        elif choice == "6":
            captures = get_captures(base_url, agent_id=agent_id)
            if captures:
                filename = input("Enter filename (e.g., captures.json): ").strip()
                if not filename:
                    filename = "captures.json"
                with open(filename, "w") as f:
                    json.dump(captures, f, indent=2)
                print(f"Exported {len(captures)} captures to {filename}")
            else:
                print("No captures to export.")

        elif choice == "7":
            confirm = input("Clear all captures? (y/n): ").strip().lower()
            if confirm == "y":
                try:
                    response = requests.delete(f"{base_url}/inspector/requests", timeout=5)
                    if response.status_code == 200:
                        print("All captures cleared.")
                    else:
                        print("Failed to clear captures.")
                except requests.RequestException as e:
                    print(f"Error clearing captures: {e}")

        elif choice == "8":
            interval = input("Check interval in seconds (default: 2): ").strip()
            try:
                interval = int(interval) if interval else 2
                monitor_mode(base_url, agent_id, interval)
            except ValueError:
                print("Invalid interval.")

        elif choice == "9":
            agent_id = input("Enter new agent ID: ").strip()
            print(f"Changed to agent: {agent_id}")

        else:
            print("Invalid choice.")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test and monitor Prompt Inspector with Godot simulation"
    )
    parser.add_argument(
        "--host", type=str, default="127.0.0.1", help="IPC server host (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", type=int, default=5000, help="IPC server port (default: 5000)"
    )
    parser.add_argument(
        "--agent-id",
        type=str,
        default="foraging_agent_001",
        help="Agent ID to monitor (default: foraging_agent_001)",
    )
    parser.add_argument(
        "--monitor", action="store_true", help="Start in monitor mode (real-time)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=2,
        help="Check interval for monitor mode in seconds (default: 2)",
    )

    args = parser.parse_args()

    base_url = f"http://{args.host}:{args.port}"

    print_separator()
    print("Prompt Inspector - Godot Simulation Tester")
    print_separator()
    print(f"IPC Server: {base_url}")
    print(f"Agent ID: {args.agent_id}")
    print_separator()

    # Check if inspector is available
    print("\nChecking inspector status...")
    config = check_inspector_status(base_url)

    if config is None:
        print("❌ Could not connect to IPC server.")
        print("\nMake sure to:")
        print("1. Start the IPC server with LocalLLMBehavior")
        print("   Example: python run_local_llm_forager.py --model ...")
        print("2. Check that the server is running at the correct host/port")
        return 1

    print("✅ Inspector connected!")
    print(f"   Enabled: {config.get('enabled', False)}")
    print(f"   Max entries: {config.get('max_entries', 0)}")
    print(f"   Log to file: {config.get('log_to_file', False)}")

    if not config.get("enabled", False):
        print("\n⚠️  WARNING: Inspector is disabled!")
        print("   No captures will be available.")
        return 1

    # Check for existing captures
    captures = get_captures(base_url, agent_id=args.agent_id)
    print(f"\nExisting captures for {args.agent_id}: {len(captures)}")

    if args.monitor:
        # Start in monitor mode
        monitor_mode(base_url, args.agent_id, args.interval)
    else:
        # Start interactive menu
        print("\nStarting interactive menu...")
        interactive_menu(base_url, args.agent_id)

    return 0


if __name__ == "__main__":
    sys.exit(main())
