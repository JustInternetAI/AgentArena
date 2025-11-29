"""
Quick test script to verify the /observe endpoint works.

Run this after starting the IPC server to test the mock decision logic.
"""

import json

import requests

# Test observation data
test_observation = {
    "agent_id": "test_agent_001",
    "position": [0.0, 0.0, 0.0],
    "nearby_resources": [
        {"name": "Berry1", "type": "berry", "position": [5.0, 0.0, 3.0], "distance": 5.83},
        {"name": "Wood1", "type": "wood", "position": [-3.0, 0.0, 7.0], "distance": 7.62},
    ],
    "nearby_hazards": [
        {"name": "Fire1", "type": "fire", "position": [2.0, 0.0, 2.0], "distance": 2.83}
    ],
}


def test_observe_endpoint():
    """Test the /observe endpoint with sample data."""
    url = "http://127.0.0.1:5000/observe"

    print("Testing /observe endpoint...")
    print(f"URL: {url}")
    print("\nSending observation:")
    print(json.dumps(test_observation, indent=2))

    try:
        response = requests.post(url, json=test_observation)

        if response.status_code == 200:
            print("\n✓ Success!")
            print("\nDecision received:")
            decision = response.json()
            print(json.dumps(decision, indent=2))

            # Verify structure
            assert "agent_id" in decision
            assert "tool" in decision
            assert "params" in decision
            assert "reasoning" in decision

            print("\n✓ Response structure is valid!")
            print(
                "\nExpected behavior: Should use 'move_to' to avoid fire hazard (distance: 2.83 < 3.0)"
            )
            print(f"Actual decision: {decision['tool']} - {decision['reasoning']}")

            # Validate the decision makes sense
            if decision["tool"] == "move_to":
                print("\n✓ Correct tool used (move_to)")
                if "target_position" in decision["params"]:
                    print(f"  Target position: {decision['params']['target_position']}")
                    print("  (Should be moving away from fire at [2.0, 0.0, 2.0])")
            else:
                print(f"\n⚠ Unexpected tool: {decision['tool']}")

        else:
            print(f"\n✗ Failed with status code: {response.status_code}")
            print(f"Response: {response.text}")

    except requests.exceptions.ConnectionError:
        print("\n✗ Connection failed!")
        print("Make sure the IPC server is running:")
        print("  cd python")
        print("  venv\\Scripts\\activate")
        print("  python run_ipc_server.py")
    except Exception as e:
        print(f"\n✗ Error: {e}")


if __name__ == "__main__":
    test_observe_endpoint()
