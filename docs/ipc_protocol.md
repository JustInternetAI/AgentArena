# IPC Protocol Documentation

## Overview

Agent Arena uses HTTP/JSON for communication between the Godot simulation (C++/GDScript) and the Python agent runtime. This document defines the message format and protocol for both directions.

## Architecture

```
┌─────────────────┐                    ┌──────────────────┐
│  Godot Engine   │                    │  Python Runtime  │
│  (Simulation)   │                    │  (Agent Brain)   │
├─────────────────┤                    ├──────────────────┤
│                 │  Perception Data   │                  │
│  IPCClient      │───────────────────>│  FastAPI Server  │
│                 │                    │                  │
│  ToolRegistry   │<───────────────────│  AgentRuntime    │
│                 │   Action Commands  │                  │
└─────────────────┘                    └──────────────────┘
```

## Connection Setup

### Server (Python)
- **Protocol**: HTTP/1.1
- **Default Host**: `127.0.0.1`
- **Default Port**: `5000`
- **Framework**: FastAPI
- **Startup**: `python python/run_ipc_server.py`

### Client (Godot)
- **Node Type**: `IPCClient` (C++ GDExtension)
- **Methods**: `connect_to_server()`, `send_tick_request()`, `get_tick_response()`
- **Default URL**: `http://127.0.0.1:5000`

## Message Format

All messages use JSON encoding with UTF-8.

---

## 1. Perception Messages (Godot → Python)

Sent every simulation tick to provide agents with observations about the world.

### Endpoint
```
POST /tick
```

### Request Format

```json
{
  "tick": 1234,
  "timestamp": 1234567890.123,
  "agents": [
    {
      "agent_id": "foraging_agent_001",
      "observations": {
        "position": [10.5, 0.0, 5.2],
        "rotation": [0.0, 90.0, 0.0],
        "velocity": [1.0, 0.0, 0.5],
        "health": 100.0,
        "inventory": {
          "berries": 3,
          "wood": 2,
          "stone": 1
        },
        "visible_entities": [
          {
            "entity_id": "berry_001",
            "type": "resource",
            "resource_type": "berry",
            "position": [12.0, 0.5, 6.0],
            "distance": 2.1
          },
          {
            "entity_id": "fire_hazard_002",
            "type": "hazard",
            "hazard_type": "fire",
            "position": [7.0, 0.5, -3.0],
            "distance": 9.8
          }
        ],
        "nearby_agents": [
          {
            "agent_id": "blue_agent_002",
            "team": "blue",
            "position": [8.0, 1.0, 7.0],
            "distance": 3.5
          }
        ],
        "scene_specific": {
          "foraging": {
            "resources_collected": 6,
            "resources_remaining": 1,
            "damage_taken": 15.0
          },
          "crafting": {
            "available_stations": [
              {
                "name": "Furnace",
                "type": "furnace",
                "position": [0.0, 0.5, -5.0],
                "distance": 12.3
              }
            ],
            "recipes": {
              "iron_ingot": {
                "inputs": {"iron_ore": 1, "coal": 1},
                "station": "Furnace",
                "time": 3.0
              }
            }
          },
          "team_capture": {
            "team": "blue",
            "team_score": 45,
            "enemy_score": 38,
            "objectives": [
              {
                "name": "CapturePointA",
                "owner": "blue",
                "capturing_team": null,
                "capture_progress": 0.0,
                "position": [-15.0, 0.5, -15.0],
                "distance": 8.2
              }
            ]
          }
        }
      }
    }
  ]
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `tick` | integer | Current simulation tick number |
| `timestamp` | float | Unix timestamp in seconds |
| `agents` | array | List of agent observations |
| `agent_id` | string | Unique identifier for the agent |
| `observations` | object | Agent's perception data |
| `position` | [float, float, float] | Agent position (x, y, z) |
| `rotation` | [float, float, float] | Agent rotation in degrees (pitch, yaw, roll) |
| `velocity` | [float, float, float] | Current velocity vector |
| `health` | float | Agent's health (0-100) |
| `inventory` | object | Dict of item_name: quantity |
| `visible_entities` | array | Entities within perception range |
| `nearby_agents` | array | Other agents within communication range |
| `scene_specific` | object | Benchmark-specific data |

---

## 2. Action Messages (Python → Godot)

Response containing agent action decisions.

### Response Format

```json
{
  "tick": 1234,
  "actions": [
    {
      "agent_id": "foraging_agent_001",
      "action": {
        "tool": "move_to",
        "params": {
          "target_x": 12.0,
          "target_y": 0.0,
          "target_z": 6.0,
          "speed": 1.5
        }
      },
      "reasoning": "Moving towards berry at (12, 0, 6) to collect resources"
    },
    {
      "agent_id": "blue_agent_001",
      "action": {
        "tool": "capture_point",
        "params": {
          "point_name": "CapturePointC"
        }
      },
      "reasoning": "Capturing neutral objective to gain team points"
    }
  ]
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `tick` | integer | Must match the request tick |
| `actions` | array | List of agent actions |
| `agent_id` | string | Agent that performs this action |
| `action` | object | Action specification |
| `tool` | string | Name of the tool to execute |
| `params` | object | Tool-specific parameters |
| `reasoning` | string | (Optional) LLM's reasoning for debugging |

---

## 3. Available Tools

Tools are registered in the `ToolRegistry` and available to agents. Each tool has a JSON schema defining its parameters.

### Movement Tools

#### `move_to`
Move the agent to a target position.

```json
{
  "tool": "move_to",
  "params": {
    "target_x": 15.0,
    "target_y": 0.0,
    "target_z": 8.0,
    "speed": 1.5
  }
}
```

**Parameters**:
- `target_x` (float): Target X coordinate
- `target_y` (float): Target Y coordinate
- `target_z` (float): Target Z coordinate
- `speed` (float, optional): Movement speed multiplier (default: 1.0)

#### `rotate_to`
Rotate the agent to face a direction.

```json
{
  "tool": "rotate_to",
  "params": {
    "yaw": 90.0
  }
}
```

**Parameters**:
- `yaw` (float): Target rotation in degrees

### Collection Tools

#### `collect`
Collect a nearby resource.

```json
{
  "tool": "collect",
  "params": {
    "resource_name": "Berry1"
  }
}
```

**Parameters**:
- `resource_name` (string): Name of the resource to collect

### Crafting Tools

#### `craft`
Craft an item at a crafting station.

```json
{
  "tool": "craft",
  "params": {
    "item_name": "iron_ingot",
    "station_name": "Furnace"
  }
}
```

**Parameters**:
- `item_name` (string): Name of item to craft (must match recipe)
- `station_name` (string): Name of crafting station

### Query Tools

#### `query_world`
Get information about nearby entities.

```json
{
  "tool": "query_world",
  "params": {
    "radius": 10.0
  }
}
```

**Parameters**:
- `radius` (float): Search radius in meters

#### `query_inventory`
Check current inventory contents.

```json
{
  "tool": "query_inventory",
  "params": {}
}
```

**Parameters**: None

#### `query_recipes`
Get available crafting recipes.

```json
{
  "tool": "query_recipes",
  "params": {}
}
```

**Parameters**: None

### Communication Tools (Team Capture)

#### `send_message`
Send a message to nearby teammates.

```json
{
  "tool": "send_message",
  "params": {
    "message": "Capturing point C, need backup!",
    "target_agent": "blue_agent_002"
  }
}
```

**Parameters**:
- `message` (string): Message content
- `target_agent` (string, optional): Specific agent ID or "all" for broadcast

#### `capture_point`
Attempt to capture an objective.

```json
{
  "tool": "capture_point",
  "params": {
    "point_name": "CapturePointC"
  }
}
```

**Parameters**:
- `point_name` (string): Name of the capture point

---

## 4. Error Handling

### Error Response Format

If an error occurs, the Python server returns an error response:

```json
{
  "tick": 1234,
  "error": {
    "code": "TOOL_EXECUTION_FAILED",
    "message": "Agent foraging_agent_001 attempted invalid action: tool 'invalid_tool' not registered",
    "agent_id": "foraging_agent_001"
  },
  "actions": []
}
```

### Error Codes

| Code | Description |
|------|-------------|
| `TOOL_NOT_FOUND` | Requested tool not registered |
| `INVALID_PARAMETERS` | Tool parameters don't match schema |
| `AGENT_NOT_FOUND` | Agent ID doesn't exist |
| `LLM_TIMEOUT` | LLM failed to respond in time |
| `PARSING_ERROR` | Failed to parse LLM output |
| `TOOL_EXECUTION_FAILED` | Tool execution failed in Godot |

---

## 5. Timing & Performance

### Recommended Timing
- **Tick Rate**: 60 ticks/second (16.67ms per tick)
- **IPC Latency Budget**: < 5ms per request
- **LLM Response Time**: 100-1000ms (run async, queue actions)

### Async Pattern (Recommended)

For LLM backends with high latency:

1. **Godot**: Send perception data (non-blocking)
2. **Python**: Queue perception, return previous action or "wait"
3. **Python**: Process LLM inference async in background
4. **Python**: Cache action for next tick
5. **Godot**: Use cached action on subsequent tick

### Example Async Response

```json
{
  "tick": 1234,
  "actions": [
    {
      "agent_id": "foraging_agent_001",
      "action": {
        "tool": "wait",
        "params": {}
      },
      "processing": true
    }
  ]
}
```

---

## 6. Testing & Debugging

### Test Endpoints

#### Health Check
```
GET /health
```

**Response**:
```json
{
  "status": "ok",
  "backend": "llama_cpp",
  "agents_active": 3,
  "uptime_seconds": 1234.5
}
```

#### Echo Test
```
POST /echo
```

**Request**: Any JSON
**Response**: Same JSON echoed back

### Debug Logging

Enable verbose IPC logging:

**Godot** ([scripts/foraging.gd:112](scripts/foraging.gd#L112)):
```gdscript
# In _on_tick_advanced()
print("[IPC] Sending perception: ", perception_data)
```

**Python**:
```python
# In run_ipc_server.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Mock Testing

**Test Python without Godot**:
```python
# tests/test_ipc.py
import requests

perception = {
    "tick": 1,
    "agents": [{...}]
}

response = requests.post("http://127.0.0.1:5000/tick", json=perception)
print(response.json())
```

**Test Godot without Python**:
Use the IPC test scene: [scenes/test_IPC.tscn](scenes/test_IPC.tscn)

---

## 7. Future Enhancements

### Planned Features
- **WebSocket support**: For lower latency bidirectional streaming
- **Compression**: MessagePack or protobuf for binary encoding
- **Batch processing**: Multiple ticks in single request
- **State synchronization**: Full world state snapshots
- **Replay streaming**: Send recorded events for analysis

### Protocol Versioning

Include version in all messages:

```json
{
  "protocol_version": "0.1.0",
  "tick": 1234,
  ...
}
```

---

## 8. Schema Validation

### Python Side (FastAPI)

Use Pydantic models for validation:

```python
from pydantic import BaseModel
from typing import List, Dict, Any

class AgentObservation(BaseModel):
    agent_id: str
    observations: Dict[str, Any]

class PerceptionRequest(BaseModel):
    tick: int
    timestamp: float
    agents: List[AgentObservation]

class ActionResponse(BaseModel):
    tick: int
    actions: List[Dict[str, Any]]
```

### Godot Side

Validate in GDScript before sending:

```gdscript
func validate_perception(data: Dictionary) -> bool:
    return data.has("tick") and data.has("agents")
```

---

## Reference Implementation

See:
- **Godot**: [scripts/tests/ipc_test.gd](scripts/tests/ipc_test.gd)
- **Python**: `python/run_ipc_server.py`
- **C++ IPCClient**: `godot/src/agent_arena.cpp`

---

## Contact & Support

Questions about the IPC protocol? Open an issue on GitHub:
https://github.com/JustInternetAI/AgentArena/issues
