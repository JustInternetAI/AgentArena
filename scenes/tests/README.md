# Test Scenes

Test scenes for verifying different parts of the Agent Arena system.

## Test Scenes

### test_observation_loop.tscn ⭐ NEW
**Observation-decision loop test (End-to-end pipeline)**

- **Purpose**: Validate complete observation-decision pipeline
- **Tests**: Game observations → Python backend → Mock decisions → Game
- **Output**: 10 ticks of observation/decision pairs
- **Best for**: Validating the full game-to-LLM pipeline

**How to run:**
1. Start Python server: `START_IPC_SERVER.bat`
2. Open this scene in Godot
3. Press F6
4. Watch console for observation/decision flow

**What it tests:**
- Observation serialization (game data → JSON)
- Backend processing (observations → decisions)
- Mock decision logic (rule-based AI)
- Continuous tick loop (10 iterations)

### test_tool_execution_simple.tscn
**Direct HTTP test of Python IPC server**

- **Purpose**: Verify Python server and tool execution works
- **Tests**: HTTP `/tools/execute` endpoint directly
- **Output**: Clear pass/fail for each tool
- **Best for**: Initial verification, debugging

**How to run:**
1. Start Python server: `START_IPC_SERVER.bat`
2. Open this scene in Godot
3. Press F6
4. Watch console for results

### test_tool_execution.tscn
**Full integration test**

- **Purpose**: Test complete Agent → Python pipeline
- **Tests**: C++ classes, IPC, Python integration
- **Output**: Async responses via signals
- **Best for**: Integration testing, realistic scenarios

**How to run:**
1. Start Python server: `START_IPC_SERVER.bat`
2. Open this scene in Godot
3. Press F6
4. Check both consoles for async responses

## Controls

Both tests support:
- **T** - Run tests again
- **Q** - Quit

## Prerequisites

Python IPC server must be running:
```bash
START_IPC_SERVER.bat
```

Or manually:
```bash
cd python
venv\Scripts\activate
python run_ipc_server.py
```

## Expected Results

All 5 tools should pass:
1. `move_to`
2. `pickup_item`
3. `stop_movement`
4. `get_inventory`
5. `navigate_to`

## Troubleshooting

See `TESTING_TOOL_EXECUTION.md` in project root for detailed troubleshooting.
