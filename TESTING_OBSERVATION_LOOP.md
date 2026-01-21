# Observation-Decision Loop Test

## Overview

This test validates the complete observation-decision pipeline without executing actual agent movement. It demonstrates that game observations can be sent to the Python backend, processed into decisions, and returned to Godot.

**GitHub Issue:** [#28](https://github.com/JustInternetAI/AgentArena/issues/28)

## What This Tests

✅ **Observation Serialization** - Game data → JSON format
✅ **HTTP Communication** - Godot → Python backend
✅ **Mock Decision Logic** - Rule-based decision making
✅ **Response Handling** - JSON → Game data
✅ **Continuous Loop** - 10 ticks without errors

## Files Implemented

### Backend (Python)
- **`python/ipc/server.py`** - Added `/observe` endpoint (line 276)
- **`python/ipc/server.py`** - Added `_make_mock_decision()` method (line 71)
- **`python/test_observe_endpoint.py`** - Python test script
- **`python/OBSERVE_ENDPOINT.md`** - API documentation

### Frontend (Godot)
- **`scripts/tests/test_observation_loop.gd`** - Test script
- **`scenes/tests/test_observation_loop.tscn`** - Test scene
- **`scenes/tests/README.md`** - Updated documentation

## How to Run

### Step 1: Start Python Backend

```bash
cd python
venv\Scripts\activate
python run_ipc_server.py
```

**Expected output:**
```
Agent Arena IPC Server
Host: 127.0.0.1
Port: 5000
Max Workers: 4
Starting IPC server...
Registered 12 tools
```

### Step 2: Run Godot Test

1. Open Godot project
2. Navigate to `scenes/tests/test_observation_loop.tscn`
3. Press **F6** to run the scene
4. Watch the console output

### Step 3: Observe Results

**Godot Console** will show:
```
=== Observation-Decision Loop Test ===
✓ Connected to Python backend!

=== STARTING OBSERVATION LOOP TEST ===
Running 10 ticks...

[Initial State]
  Agent position: (0, 0, 0)
  Resources: 4
    - Berry1 (berry) at distance 5.83
    - Berry2 (berry) at distance 4.47
    - Wood1 (wood) at distance 7.62
    - Stone1 (stone) at distance 8.25
  Hazards: 2
    - Fire1 (fire) at distance 2.83
    - Pit1 (pit) at distance 5.10

--- Tick 0 ---
Sending observation:
  Position: (0, 0, 0)
  Nearby resources: 4
  Nearby hazards: 2
✓ Decision received:
  Tool: move_away
  Params: {from_position:[2, 0, 2]}
  Reasoning: Avoiding nearby fire hazard at distance 2.8
  → Simulated position update: (-0.707107, 0, -0.707107)

--- Tick 1 ---
...
```

**Python Backend** will log:
```
INFO:ipc.server:Agent test_forager_001 decision: move_away - Avoiding nearby fire hazard at distance 2.8
INFO:ipc.server:Agent test_forager_001 decision: move_to - Moving to collect berry (Berry2) at distance 4.5
...
```

## Mock Decision Logic

The backend uses a priority system:

### Priority 1: Avoid Hazards (distance < 3.0)
- Returns `move_away` tool
- Agent moves away from dangerous hazards

### Priority 2: Collect Resources (distance < 5.0)
- Returns `move_to` tool
- Agent moves toward nearest collectible resource

### Priority 3: Idle (default)
- Returns `idle` tool
- No immediate actions needed

## Success Criteria

After running the test, verify:

- [ ] Test runs for all 10 ticks without errors
- [ ] Each tick sends observation to backend
- [ ] Each tick receives decision from backend
- [ ] Decisions make logical sense:
  - Early ticks: Avoid fire (distance 2.83 < 3.0)
  - Later ticks: Move to resources (after moving away from hazard)
- [ ] Agent position updates (simulated, not real movement)
- [ ] No crashes or connection failures
- [ ] Python logs show all decisions

## Controls

- **T** - Run test again (resets position to origin)
- **Q** - Quit the test

## Expected Behavior

1. **Tick 0-2:** Agent should avoid fire hazard (distance 2.83 < 3.0)
2. **Tick 3-5:** Agent moves away from fire, distance increases
3. **Tick 6-9:** Agent should move toward nearest resource (Berry2 at 4.47)

## Troubleshooting

### "Connection failed"
- Ensure Python IPC server is running
- Check that port 5000 is not blocked
- Verify IPCService autoload is configured

### "No decision received"
- Check Python console for errors
- Verify `/observe` endpoint exists (check `python/ipc/server.py`)
- Test endpoint manually: `python test_observe_endpoint.py`

### JSON parse errors
- Check observation format in `build_observation()`
- Verify all position arrays are `[x, y, z]` format
- Check Python logs for validation errors

## What's Next

After this test passes:

1. **Integrate with foraging scene** - Add observation loop to `scripts/foraging.gd`
2. **Replace mock decisions** - Integrate real LLM backend
3. **Implement movement execution** - Actually move agents based on decisions
4. **Add multi-agent support** - Test with multiple agents simultaneously

## Metrics

View backend metrics:
```bash
curl http://127.0.0.1:5000/metrics
```

Should show:
```json
{
  "total_observations_processed": 10,
  "total_ticks": 0,
  "total_tools_executed": 0,
  ...
}
```

## Related Documentation

- **API Docs:** `python/OBSERVE_ENDPOINT.md`
- **Test Suite:** `scenes/tests/README.md`
- **GitHub Issue:** [#28](https://github.com/JustInternetAI/AgentArena/issues/28)
