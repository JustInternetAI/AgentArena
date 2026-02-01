"""Observation Inspector - Debug tool to inspect observations sent to agents.

This tool creates a simple server that logs every observation received,
showing exactly what the agent "sees" at each tick.

Usage:
    python -m tools.observe_inspector [--port 5001] [--output observations.jsonl]

The tool acts as a proxy - run your normal agent on a different port and
point this inspector at the observation endpoint to see what's being sent.

Or use it standalone to just log observations without an agent responding.
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request

app = Flask(__name__)

# Storage for observations
observation_log: list[dict] = []
log_file: Path | None = None
verbose: bool = True
last_visible_resources: set[str] = set()
last_visible_hazards: set[str] = set()


def log_observation(obs: dict) -> dict:
    """Log and analyze an observation."""
    global last_visible_resources, last_visible_hazards

    tick = obs.get("tick", obs.get("custom_data", {}).get("tick", "?"))
    agent_id = obs.get("agent_id", "unknown")
    position = obs.get("position", [0, 0, 0])

    # Extract resources and hazards
    # They might be in custom_data or at top level depending on format
    custom = obs.get("custom_data", {})
    nearby_resources = obs.get("nearby_resources", custom.get("nearby_resources", []))
    nearby_hazards = obs.get("nearby_hazards", custom.get("nearby_hazards", []))

    current_resources = {r.get("name", str(r)) for r in nearby_resources}
    current_hazards = {h.get("name", str(h)) for h in nearby_hazards}

    # Detect changes
    gained_resources = current_resources - last_visible_resources
    lost_resources = last_visible_resources - current_resources
    gained_hazards = current_hazards - last_visible_hazards
    lost_hazards = last_visible_hazards - current_hazards

    # Update tracking
    last_visible_resources = current_resources
    last_visible_hazards = current_hazards

    # Build analysis
    analysis = {
        "tick": tick,
        "agent_id": agent_id,
        "position": position,
        "visible_resources": list(current_resources),
        "visible_hazards": list(current_hazards),
        "gained_resources": list(gained_resources),
        "lost_resources": list(lost_resources),
        "gained_hazards": list(gained_hazards),
        "lost_hazards": list(lost_hazards),
        "timestamp": datetime.now().isoformat(),
        "raw_observation": obs,
    }

    # Print to console
    if verbose:
        print(f"\n{'='*60}")
        print(f"[OBSERVATION] Tick {tick} | Agent: {agent_id}")
        print(f"  Position: ({position[0]:.1f}, {position[1]:.1f}, {position[2]:.1f})")
        print(f"  Visible: {len(current_resources)} resources, {len(current_hazards)} hazards")

        if current_resources:
            print(f"    Resources: {', '.join(sorted(current_resources))}")
        if current_hazards:
            print(f"    Hazards: {', '.join(sorted(current_hazards))}")

        if gained_resources:
            print(f"  >> GAINED: {', '.join(sorted(gained_resources))}")
        if lost_resources:
            print(f"  << LOST: {', '.join(sorted(lost_resources))}")
        if gained_hazards:
            print(f"  >> GAINED HAZARD: {', '.join(sorted(gained_hazards))}")
        if lost_hazards:
            print(f"  << LOST HAZARD: {', '.join(sorted(lost_hazards))}")

    # Store and optionally write to file
    observation_log.append(analysis)
    if log_file:
        with open(log_file, "a") as f:
            f.write(json.dumps(analysis) + "\n")

    return analysis


@app.route("/observe", methods=["POST"])
def observe():
    """Receive observation from Godot and log it."""
    obs = request.get_json()
    log_observation(obs)

    # Return idle action - the agent does nothing, we're just inspecting
    return jsonify(
        {"tool": "idle", "params": {}, "reasoning": "Observation inspector - logging only"}
    )


@app.route("/tick", methods=["POST"])
def tick():
    """Alternative endpoint name for observation."""
    return observe()


@app.route("/status", methods=["GET"])
def status():
    """Return current observation state."""
    return jsonify(
        {
            "observations_logged": len(observation_log),
            "last_visible_resources": list(last_visible_resources),
            "last_visible_hazards": list(last_visible_hazards),
            "last_observation": observation_log[-1] if observation_log else None,
        }
    )


@app.route("/history", methods=["GET"])
def history():
    """Return observation history."""
    limit = request.args.get("limit", 50, type=int)
    return jsonify(observation_log[-limit:])


@app.route("/changes", methods=["GET"])
def changes():
    """Return only observations where visibility changed."""
    changed = [
        obs
        for obs in observation_log
        if obs["gained_resources"]
        or obs["lost_resources"]
        or obs["gained_hazards"]
        or obs["lost_hazards"]
    ]
    limit = request.args.get("limit", 50, type=int)
    return jsonify(changed[-limit:])


@app.route("/reset", methods=["POST"])
def reset():
    """Reset observation tracking."""
    global observation_log, last_visible_resources, last_visible_hazards
    observation_log = []
    last_visible_resources = set()
    last_visible_hazards = set()
    return jsonify({"status": "reset"})


def main():
    global log_file, verbose

    parser = argparse.ArgumentParser(
        description="Observation Inspector - Debug tool to inspect agent observations"
    )
    parser.add_argument("--port", type=int, default=5000, help="Port to listen on (default: 5000)")
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output file for observation log (JSONL format)",
    )
    parser.add_argument("--quiet", "-q", action="store_true", help="Reduce console output")
    args = parser.parse_args()

    if args.output:
        log_file = Path(args.output)
        print(f"Logging observations to: {log_file}")

    verbose = not args.quiet

    print(
        f"""
{'='*60}
  OBSERVATION INSPECTOR
{'='*60}
  Listening on port {args.port}

  This tool logs every observation sent from Godot.
  Use it to debug what your agent "sees" each tick.

  Endpoints:
    POST /observe  - Receive and log observation
    GET  /status   - Current visibility state
    GET  /history  - All logged observations
    GET  /changes  - Only observations with visibility changes
    POST /reset    - Clear observation history

  In Godot, observations are sent to http://127.0.0.1:{args.port}/observe
{'='*60}
"""
    )

    app.run(host="127.0.0.1", port=args.port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
