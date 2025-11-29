# /observe Endpoint Documentation

## Overview

The `/observe` endpoint provides a simplified interface for testing the observation-decision loop without requiring full LLM integration. It uses rule-based mock logic to generate agent decisions based on observations.

## Endpoint Details

**URL:** `POST /observe`
**Content-Type:** `application/json`

## Request Format

```json
{
  "agent_id": "test_agent_001",
  "position": [0.0, 0.0, 0.0],
  "nearby_resources": [
    {
      "name": "Berry1",
      "type": "berry",
      "position": [5.0, 0.0, 3.0],
      "distance": 5.83
    }
  ],
  "nearby_hazards": [
    {
      "name": "Fire1",
      "type": "fire",
      "position": [2.0, 0.0, 2.0],
      "distance": 2.83
    }
  ]
}
```

## Response Format

```json
{
  "agent_id": "test_agent_001",
  "tool": "move_away",
  "params": {
    "from_position": [2.0, 0.0, 2.0]
  },
  "reasoning": "Avoiding nearby fire hazard at distance 2.8"
}
```

## Mock Decision Logic

The endpoint uses a simple priority system:

### Priority 1: Avoid Hazards (distance < 3.0)
If any hazard is within 3.0 units:
- **Tool:** `move_away`
- **Params:** `{"from_position": [x, y, z]}`
- **Reasoning:** Describes hazard type and distance

### Priority 2: Collect Resources (distance < 5.0)
If resources exist and closest is within 5.0 units:
- **Tool:** `move_to`
- **Params:** `{"target_position": [x, y, z], "speed": 1.5}`
- **Reasoning:** Describes resource type and distance

### Priority 3: Idle (default)
If no actions needed:
- **Tool:** `idle`
- **Params:** `{}`
- **Reasoning:** "No immediate actions needed - exploring environment"

## Testing

### Manual Test (Python)

```bash
cd python
venv\Scripts\activate
python test_observe_endpoint.py
```

### Manual Test (curl)

```bash
curl -X POST http://127.0.0.1:5000/observe \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "test",
    "position": [0,0,0],
    "nearby_resources": [{"name": "Berry", "type": "berry", "position": [5,0,3], "distance": 5.83}],
    "nearby_hazards": [{"name": "Fire", "type": "fire", "position": [2,0,2], "distance": 2.83}]
  }'
```

## Metrics

The endpoint tracks `total_observations_processed` in server metrics:

```bash
curl http://127.0.0.1:5000/metrics
```

## Implementation Files

- **Endpoint:** `python/ipc/server.py` (line 276)
- **Decision Logic:** `python/ipc/server.py::_make_mock_decision()` (line 71)
- **Test Script:** `python/test_observe_endpoint.py`

## Related

- GitHub Issue: #28
- Test Scene: `scenes/tests/test_observation_loop.tscn` (pending)
- Documentation: `scenes/tests/README.md` (pending)
