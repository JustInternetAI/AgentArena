# GitHub Issues for Agent Arena

This document contains pre-written GitHub issues that can be created for dividing work. Copy the markdown below each issue into GitHub's issue creation form.

---

## Python Environment & Setup Issues

### Issue 1: Setup Python Environment and Requirements

**Title**: Setup Python environment and requirements.txt

**Labels**: `python`, `setup`, `good-first-issue`

**Assignee**: Your colleague

**Body**:
```markdown
## Description
Set up the Python development environment for the Agent Arena project, including virtual environment and dependency management.

## Tasks
- [ ] Create Python virtual environment in `python/venv/`
- [ ] Create `python/requirements.txt` with initial dependencies
- [ ] Add `.gitignore` entry for `python/venv/`
- [ ] Document setup steps in `docs/python_development.md`
- [ ] Test installation on fresh environment

## Dependencies
```txt
fastapi>=0.100.0
uvicorn>=0.23.0
pydantic>=2.0.0
requests>=2.31.0
pytest>=7.4.0
hydra-core>=1.3.0
omegaconf>=2.3.0
numpy>=1.24.0
```

## Acceptance Criteria
- Virtual environment can be created and activated
- `pip install -r requirements.txt` completes without errors
- Documentation includes setup instructions for Windows, Linux, macOS
- CI/CD can install dependencies (future)

## References
- [Python Development Docs](../docs/python_development.md) (to be created)
- [Architecture](../docs/architecture.md)
```

---

### Issue 2: Implement BaseBackend Abstract Class

**Title**: Implement BaseBackend abstract class for LLM backends

**Labels**: `python`, `architecture`, `backend`

**Assignee**: Your colleague

**Body**:
```markdown
## Description
Create the abstract base class that all LLM backends will inherit from. This establishes the interface contract for different inference engines (llama.cpp, vLLM, TensorRT-LLM).

## Tasks
- [ ] Create `python/backends/base_backend.py`
- [ ] Define abstract methods: `generate()`, `generate_with_tools()`, `is_available()`, `unload()`
- [ ] Add type hints and docstrings
- [ ] Create unit tests in `tests/test_base_backend.py`
- [ ] Add example mock backend for testing

## Implementation Details

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseBackend(ABC):
    """Abstract base class for LLM inference backends."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize backend with configuration."""
        self.config = config

    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 512,
                 temperature: float = 0.7) -> str:
        """Generate text from a prompt."""
        pass

    @abstractmethod
    def generate_with_tools(self, prompt: str, tools: List[Dict],
                           **kwargs) -> Dict[str, Any]:
        """Generate with tool/function calling support."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if backend is ready for inference."""
        pass

    @abstractmethod
    def unload(self):
        """Unload model and free resources."""
        pass
```

## Acceptance Criteria
- BaseBackend class is abstract and cannot be instantiated
- All required methods are defined with proper type hints
- Docstrings follow Google or NumPy style
- Unit tests achieve >80% coverage
- Mock backend can be used for testing without real LLM

## References
- [Architecture - Backend Module](../docs/architecture.md#backends)
```

---

### Issue 3: Implement FastAPI IPC Server

**Title**: Implement FastAPI IPC server for Godot-Python communication

**Labels**: `python`, `ipc`, `critical`

**Assignee**: Your colleague

**Body**:
```markdown
## Description
Create the FastAPI server that receives perception data from Godot and returns agent actions.

## Tasks
- [ ] Create `python/run_ipc_server.py`
- [ ] Implement `/tick` POST endpoint
- [ ] Implement `/health` GET endpoint
- [ ] Implement `/echo` POST endpoint for testing
- [ ] Add Pydantic models for request/response validation
- [ ] Add error handling and logging
- [ ] Support multiple agents in single request
- [ ] Add CLI arguments (--host, --port, --workers, --debug)
- [ ] Create integration test with mock Godot client

## Implementation Guide

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import uvicorn

app = FastAPI(title="Agent Arena IPC Server")

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

@app.post("/tick", response_model=ActionResponse)
async def process_tick(request: PerceptionRequest):
    # Process agent observations
    # Generate actions using agent runtime
    # Return actions
    pass

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5000)
```

## Acceptance Criteria
- Server starts successfully on port 5000
- `/health` endpoint returns 200 OK
- `/tick` endpoint accepts valid perception data
- Response matches ActionResponse schema
- Invalid requests return proper HTTP error codes
- Server logs all requests when --debug flag is used
- Can handle 60+ requests/second (simulation tick rate)

## References
- [IPC Protocol Documentation](../docs/ipc_protocol.md)
- [Architecture - Communication Protocol](../docs/architecture.md#communication-protocol)
```

---

## Agent Runtime Issues

### Issue 4: Implement AgentRuntime Class

**Title**: Implement AgentRuntime for managing agent lifecycle

**Labels**: `python`, `agent`, `core`

**Assignee**: Your colleague

**Body**:
```markdown
## Description
Create the main agent runtime class that manages multiple agents, coordinates their perception-reasoning-action loops, and interfaces with LLM backends.

## Tasks
- [ ] Create `python/agent_runtime/agent_runtime.py`
- [ ] Implement agent registration and management
- [ ] Add async execution support for multiple agents
- [ ] Integrate with BaseBackend for decision-making
- [ ] Add memory system integration hooks
- [ ] Implement tool dispatcher integration
- [ ] Add basic logging and metrics
- [ ] Create unit tests

## Key Methods

```python
class AgentRuntime:
    def __init__(self, backend: BaseBackend, config: Dict[str, Any]):
        self.backend = backend
        self.agents = {}

    def register_agent(self, agent_id: str, agent_config: Dict):
        """Register a new agent."""

    async def process_observations(self, observations: List[Dict]) -> List[Dict]:
        """Process observations for all agents and return actions."""

    def get_agent_memory(self, agent_id: str) -> Any:
        """Get agent's memory state."""

    def reset_agent(self, agent_id: str):
        """Reset agent state."""
```

## Acceptance Criteria
- Can manage multiple agents simultaneously
- Processes observations and returns actions asynchronously
- Integrates with backend for LLM inference
- Handles agent registration and deregistration
- Includes error handling for individual agent failures
- Unit tests cover all major methods

## References
- [Architecture - Agent Runtime](../docs/architecture.md#2-python-agent-runtime)
```

---

### Issue 5: Implement Short-Term Memory System

**Title**: Implement short-term memory (scratchpad) for agents

**Labels**: `python`, `memory`, `agent`

**Assignee**: Your colleague

**Body**:
```markdown
## Description
Create a short-term memory system that stores recent observations for each agent using a FIFO queue with configurable capacity.

## Tasks
- [ ] Create `python/memory/short_term_memory.py`
- [ ] Implement FIFO queue with max capacity
- [ ] Add priority-based eviction (optional)
- [ ] Support serialization/deserialization
- [ ] Add memory retrieval with filtering
- [ ] Create unit tests
- [ ] Add configuration via Hydra config

## Implementation

```python
from collections import deque
from typing import List, Dict, Any, Optional

class ShortTermMemory:
    """FIFO queue for recent agent observations."""

    def __init__(self, capacity: int = 10):
        self.capacity = capacity
        self.memory = deque(maxlen=capacity)

    def add(self, observation: Dict[str, Any]):
        """Add observation to memory."""
        self.memory.append(observation)

    def get_recent(self, n: int = 5) -> List[Dict[str, Any]]:
        """Get n most recent observations."""
        return list(self.memory)[-n:]

    def clear(self):
        """Clear all memories."""
        self.memory.clear()

    def to_context_string(self) -> str:
        """Convert memories to LLM context string."""
        pass
```

## Acceptance Criteria
- FIFO queue respects capacity limit
- Old memories are evicted when capacity is reached
- Can retrieve N most recent observations
- Supports clearing memory
- Can serialize memory state for replay
- Unit tests verify FIFO behavior

## References
- [Architecture - Memory System](../docs/architecture.md#memory-system)
```

---

### Issue 6: Implement Tool Dispatcher

**Title**: Implement ToolDispatcher for agent tool execution

**Labels**: `python`, `tools`, `agent`

**Assignee**: Your colleague

**Body**:
```markdown
## Description
Create the tool dispatcher that registers available tools, validates tool calls from LLM, and formats them for execution in Godot.

## Tasks
- [ ] Create `python/agent_runtime/tool_dispatcher.py`
- [ ] Implement tool registration with JSON schemas
- [ ] Add tool call validation against schemas
- [ ] Support dynamic tool discovery
- [ ] Parse LLM output for tool calls (JSON, function calling)
- [ ] Create unit tests
- [ ] Add example tools (movement, collection)

## Implementation

```python
from typing import Dict, List, Any, Callable
import json

class ToolDispatcher:
    """Manages tool registration and execution."""

    def __init__(self):
        self.tools = {}

    def register_tool(self, name: str, schema: Dict[str, Any],
                     handler: Optional[Callable] = None):
        """Register a tool with its schema."""
        self.tools[name] = {
            "schema": schema,
            "handler": handler
        }

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get all tool schemas for LLM context."""
        return [tool["schema"] for tool in self.tools.values()]

    def validate_tool_call(self, tool_name: str, params: Dict) -> bool:
        """Validate tool call parameters against schema."""
        pass

    def parse_tool_call(self, llm_output: str) -> Dict[str, Any]:
        """Parse tool call from LLM output."""
        pass
```

## Acceptance Criteria
- Can register tools with JSON schemas
- Validates parameters against schema
- Parses tool calls from LLM output (JSON format)
- Returns properly formatted action for Godot
- Handles invalid tool calls gracefully
- Unit tests cover all parsing scenarios

## References
- [IPC Protocol - Available Tools](../docs/ipc_protocol.md#3-available-tools)
- [Architecture - Tool System](../docs/architecture.md#extensibility)
```

---

### Issue 7: Implement LlamaCppBackend

**Title**: Implement llama.cpp backend for local LLM inference

**Labels**: `python`, `backend`, `llm`

**Assignee**: Your colleague

**Body**:
```markdown
## Description
Create a backend implementation for llama.cpp to enable local LLM inference with GGUF models.

## Tasks
- [ ] Create `python/backends/llama_cpp_backend.py`
- [ ] Install llama-cpp-python dependency
- [ ] Implement all BaseBackend abstract methods
- [ ] Add model loading/unloading
- [ ] Support function calling / tool use
- [ ] Add configurable inference parameters (temp, top_p, etc.)
- [ ] Create config file `configs/backend/llama_cpp.yaml`
- [ ] Add integration tests with small model
- [ ] Document model download and setup

## Dependencies

Add to `requirements.txt`:
```
llama-cpp-python>=0.2.0
```

## Configuration

`configs/backend/llama_cpp.yaml`:
```yaml
backend:
  type: llama_cpp
  model_path: models/phi-2.Q4_K_M.gguf
  n_ctx: 2048
  n_threads: 4
  n_gpu_layers: 0
  temperature: 0.7
  top_p: 0.9
  max_tokens: 512
```

## Acceptance Criteria
- Can load GGUF models successfully
- Generates coherent text from prompts
- Supports function/tool calling
- Handles model loading errors gracefully
- Can unload model to free memory
- Integration test runs with small model (~1GB)

## References
- [llama-cpp-python docs](https://github.com/abetlen/llama-cpp-python)
- [Architecture - Backends](../docs/architecture.md#backends)
```

---

## Testing & Integration Issues

### Issue 8: Create Python Unit Test Suite

**Title**: Create comprehensive Python unit test suite

**Labels**: `python`, `testing`, `quality`

**Assignee**: Your colleague

**Body**:
```markdown
## Description
Set up pytest-based unit testing infrastructure for the Python codebase.

## Tasks
- [ ] Create `tests/` directory structure
- [ ] Set up pytest configuration (`pytest.ini`)
- [ ] Create fixtures for common test data
- [ ] Add tests for BaseBackend
- [ ] Add tests for AgentRuntime
- [ ] Add tests for ToolDispatcher
- [ ] Add tests for ShortTermMemory
- [ ] Add tests for IPC server
- [ ] Set up coverage reporting
- [ ] Document testing practices

## Directory Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── test_backends/
│   ├── test_base_backend.py
│   └── test_llama_cpp_backend.py
├── test_agent_runtime/
│   ├── test_agent_runtime.py
│   └── test_tool_dispatcher.py
├── test_memory/
│   └── test_short_term_memory.py
└── test_ipc/
    └── test_ipc_server.py
```

## pytest.ini

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --verbose
    --cov=python
    --cov-report=html
    --cov-report=term
```

## Acceptance Criteria
- All tests pass with `pytest`
- Code coverage > 80%
- Tests run in CI/CD pipeline (future)
- Mock objects used where appropriate
- Documentation includes testing guide

## References
- [pytest documentation](https://docs.pytest.org/)
```

---

### Issue 9: Create End-to-End Integration Test

**Title**: Create end-to-end integration test (Godot + Python)

**Labels**: `integration`, `testing`, `critical`

**Assignee**: Both (collaborative)

**Body**:
```markdown
## Description
Create an integration test that verifies the full pipeline: Godot sends perception → Python processes → Returns action → Godot executes.

## Tasks
- [ ] Create test script that starts IPC server
- [ ] Create minimal Godot test scene
- [ ] Send mock perception data from Godot
- [ ] Verify Python receives and processes it
- [ ] Verify action is returned and executed
- [ ] Test all three benchmark scenes
- [ ] Document integration testing process
- [ ] Add to CI/CD (future)

## Test Scenarios

1. **Basic IPC**: Send perception, receive action
2. **Movement**: Agent moves to target position
3. **Collection**: Agent collects resource
4. **Crafting**: Agent crafts item at station
5. **Team Capture**: Multiple agents coordinate
6. **Error Handling**: Invalid tool call, LLM timeout

## Acceptance Criteria
- Full perception → action → execution loop works
- All benchmark scenes work end-to-end
- Error cases handled gracefully
- Documentation includes troubleshooting guide
- Can run without manual intervention

## References
- [IPC Protocol](../docs/ipc_protocol.md)
- [Testing Guide](../TESTING.md)
```

---

## Documentation Issues

### Issue 10: Create Python Development Documentation

**Title**: Create Python development documentation

**Labels**: `documentation`, `python`

**Assignee**: Your colleague

**Body**:
```markdown
## Description
Create comprehensive documentation for Python development on Agent Arena.

## Tasks
- [ ] Create `docs/python_development.md`
- [ ] Document environment setup
- [ ] Document project structure
- [ ] Add backend development guide
- [ ] Add tool creation guide
- [ ] Add memory system guide
- [ ] Include code examples
- [ ] Add troubleshooting section

## Sections

1. **Setup**: venv, dependencies, IDE configuration
2. **Project Structure**: Explanation of `python/` directory
3. **Adding a Backend**: Step-by-step guide
4. **Creating Tools**: How to add new agent tools
5. **Memory Systems**: Short-term, long-term, episode
6. **Testing**: Running tests, writing tests
7. **Debugging**: Common issues and solutions
8. **Code Style**: Formatting, linting, type hints

## Acceptance Criteria
- New developer can set up Python environment from docs
- All major components are documented
- Includes working code examples
- Covers common pitfalls and solutions

## References
- [Architecture](../docs/architecture.md)
- [IPC Protocol](../docs/ipc_protocol.md)
```

---

## Quick Create Commands

To create these issues quickly, use the GitHub CLI:

```bash
# Make sure you're in the repo directory
cd "c:\Projects\Agent Arena"

# Create all issues at once (copy/paste each block)

# Issue 1
gh issue create --title "Setup Python environment and requirements.txt" \
  --label "python,setup,good-first-issue" \
  --body-file docs/issue_bodies/issue_1.md

# Issue 2
gh issue create --title "Implement BaseBackend abstract class for LLM backends" \
  --label "python,architecture,backend" \
  --body-file docs/issue_bodies/issue_2.md

# ... etc for all issues
```

Or create them manually via GitHub web interface and copy the markdown body from each section above.

---

## Issue Assignment Strategy

**Week 1 Focus** (Your colleague):
- Issue 1: Setup Python environment
- Issue 2: BaseBackend
- Issue 3: FastAPI IPC server

**Week 2 Focus** (Your colleague):
- Issue 4: AgentRuntime
- Issue 5: Short-term memory
- Issue 6: Tool dispatcher

**Week 3 Focus** (Your colleague):
- Issue 7: LlamaCppBackend
- Issue 8: Unit tests

**Week 4 Focus** (Collaborative):
- Issue 9: Integration testing
- Issue 10: Documentation

**Your Focus** (Parallel):
- Debug benchmark scenes
- Implement tool execution in Godot
- Add collision detection
- Improve visuals
- Refine IPC client
