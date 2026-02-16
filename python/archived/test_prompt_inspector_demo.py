"""
Demo script for testing the Prompt Inspector functionality.

This script simulates agent decisions and demonstrates how to view captured prompts.
Run this to see the Prompt Inspector in action without needing a full simulation.
"""

import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import only what we absolutely need to avoid optional dependencies
import sys  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))

# Standalone imports
from dataclasses import dataclass, field  # noqa: E402


# Copy minimal classes to avoid importing agent_runtime.__init__
@dataclass
class Observation:
    """Minimal observation for demo."""

    agent_id: str
    tick: int
    position: tuple[float, float, float]
    health: float = 100.0
    energy: float = 100.0
    nearby_resources: list = field(default_factory=list)
    nearby_hazards: list = field(default_factory=list)
    inventory: list = field(default_factory=list)
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    velocity: tuple[float, float, float] = (0.0, 0.0, 0.0)


@dataclass
class ResourceInfo:
    """Resource information."""

    name: str
    type: str
    position: tuple[float, float, float]
    distance: float


@dataclass
class HazardInfo:
    """Hazard information."""

    name: str
    type: str
    position: tuple[float, float, float]
    distance: float
    damage: float = 0.0


@dataclass
class ToolSchema:
    """Tool schema."""

    name: str
    description: str
    parameters: dict


@dataclass
class AgentDecision:
    """Agent decision."""

    tool: str
    params: dict = field(default_factory=dict)
    reasoning: str = ""

    @staticmethod
    def idle(reasoning: str = ""):
        return AgentDecision(tool="idle", params={}, reasoning=reasoning)

    @staticmethod
    def from_llm_response(text: str):
        """Parse from JSON text."""
        import json

        try:
            data = json.loads(text)
            return AgentDecision(
                tool=data.get("tool", "idle"),
                params=data.get("params", {}),
                reasoning=data.get("reasoning", ""),
            )
        except Exception:
            raise ValueError("Invalid JSON")


@dataclass
class GenerationResult:
    """LLM generation result."""

    text: str
    tokens_used: int
    finish_reason: str
    metadata: dict = field(default_factory=dict)


@dataclass
class BackendConfig:
    """Backend config."""

    model_path: str


class BaseBackend:
    """Base backend."""

    def __init__(self, config):
        self.config = config


class SlidingWindowMemory:
    """Simple sliding window memory."""

    def __init__(self, capacity: int = 10):
        self.capacity = capacity
        self.observations = []

    def store(self, observation):
        self.observations.append(observation)
        if len(self.observations) > self.capacity:
            self.observations.pop(0)

    def retrieve(self, limit: int = None):
        if limit:
            return self.observations[-limit:]
        return self.observations


# Now import the prompt inspector
from agent_runtime.prompt_inspector import (  # noqa: E402
    InspectorStage,
    PromptInspector,
    get_global_inspector,
)


class DemoLLMBehavior:
    """Simplified LocalLLMBehavior for demo purposes (avoids optional dependencies)."""

    def __init__(
        self,
        backend: BaseBackend,
        system_prompt: str = "You are an autonomous agent in a simulation environment.",
        memory_capacity: int = 10,
        temperature: float = 0.7,
        max_tokens: int = 256,
        inspector: PromptInspector = None,
    ):
        self.backend = backend
        self.system_prompt = system_prompt
        self.memory = SlidingWindowMemory(capacity=memory_capacity)
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.inspector = inspector or get_global_inspector()

    def decide(self, observation: Observation, tools: list[ToolSchema]) -> AgentDecision:
        """Make a decision based on the observation."""
        # Start inspector capture
        capture = self.inspector.start_capture(observation.agent_id, observation.tick)

        try:
            # Store observation in memory
            self.memory.store(observation)

            # Capture observation stage
            if capture:
                capture.add_entry(
                    InspectorStage.OBSERVATION,
                    {
                        "agent_id": observation.agent_id,
                        "tick": observation.tick,
                        "position": observation.position,
                        "health": observation.health,
                        "energy": observation.energy,
                        "nearby_resources": [
                            {
                                "name": r.name,
                                "type": r.type,
                                "distance": r.distance,
                                "position": r.position,
                            }
                            for r in observation.nearby_resources
                        ],
                        "nearby_hazards": [
                            {
                                "name": h.name,
                                "type": h.type,
                                "distance": h.distance,
                                "damage": h.damage,
                            }
                            for h in observation.nearby_hazards
                        ],
                        "inventory": [
                            {"name": item.name, "quantity": item.quantity}
                            for item in observation.inventory
                        ],
                    },
                )

            # Build simple prompt
            prompt = self._build_prompt(observation)

            # Capture prompt building stage
            if capture:
                memory_items = self.memory.retrieve(limit=5)
                capture.add_entry(
                    InspectorStage.PROMPT_BUILDING,
                    {
                        "system_prompt": self.system_prompt,
                        "memory_context": {
                            "count": len(memory_items),
                            "items": [
                                {"tick": obs.tick, "position": obs.position} for obs in memory_items
                            ],
                        },
                        "final_prompt": prompt,
                        "prompt_length": len(prompt),
                        "estimated_tokens": len(prompt) // 4,
                    },
                )

            # Convert tools to dict format
            tool_dicts = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                }
                for tool in tools
            ]

            # Capture LLM request stage
            if capture:
                capture.add_entry(
                    InspectorStage.LLM_REQUEST,
                    {
                        "model": getattr(self.backend, "model_name", "unknown"),
                        "prompt": prompt,
                        "tools": tool_dicts,
                        "temperature": self.temperature,
                        "max_tokens": self.max_tokens,
                    },
                )

            # Generate response
            import time

            start_time = time.time()
            result = self.backend.generate_with_tools(
                prompt=prompt, tools=tool_dicts, temperature=self.temperature
            )
            elapsed_ms = (time.time() - start_time) * 1000

            # Capture LLM response stage
            if capture:
                capture.add_entry(
                    InspectorStage.LLM_RESPONSE,
                    {
                        "raw_text": result.text,
                        "tokens_used": result.tokens_used,
                        "finish_reason": result.finish_reason,
                        "metadata": result.metadata,
                        "latency_ms": elapsed_ms,
                    },
                )

            # Parse decision
            if "tool_call" in result.metadata:
                tool_call = result.metadata["tool_call"]
                decision = AgentDecision(
                    tool=tool_call["name"],
                    params=tool_call["arguments"],
                    reasoning=result.text or "LLM tool call",
                )
            else:
                try:
                    decision = AgentDecision.from_llm_response(result.text)
                except ValueError:
                    decision = AgentDecision.idle(reasoning="Parse error")

            # Capture final decision stage
            if capture:
                capture.add_entry(
                    InspectorStage.DECISION,
                    {
                        "tool": decision.tool,
                        "params": decision.params,
                        "reasoning": decision.reasoning,
                        "total_latency_ms": elapsed_ms,
                    },
                )

            self.inspector.finish_capture(observation.agent_id, observation.tick)
            return decision

        except Exception as e:
            if capture:
                capture.add_entry(
                    InspectorStage.DECISION,
                    {"tool": "idle", "params": {}, "reasoning": f"Error: {e}", "error": str(e)},
                )
                self.inspector.finish_capture(observation.agent_id, observation.tick)
            return AgentDecision.idle(reasoning=f"Error: {e}")

    def _build_prompt(self, observation: Observation) -> str:
        """Build a simple prompt."""
        sections = [self.system_prompt, ""]
        sections.append("## Current Situation")
        sections.append(f"Position: {observation.position}")
        sections.append(f"Health: {observation.health}")
        sections.append(f"Energy: {observation.energy}")
        sections.append(f"Tick: {observation.tick}")

        if observation.nearby_resources:
            sections.append("\n## Nearby Resources")
            for r in observation.nearby_resources[:5]:
                sections.append(
                    f"- {r.name} ({r.type}) at distance {r.distance:.1f}, position {r.position}"
                )
        else:
            sections.append("\n## Nearby Resources\nNone visible")

        if observation.nearby_hazards:
            sections.append("\n## Nearby Hazards")
            for h in observation.nearby_hazards[:5]:
                sections.append(
                    f"- {h.name} ({h.type}) at distance {h.distance:.1f}, damage: {h.damage}, position {h.position}"
                )
        else:
            sections.append("\n## Nearby Hazards\nNone visible")

        sections.append("\n## Inventory")
        if observation.inventory:
            for item in observation.inventory:
                sections.append(f"- {item.name} x{item.quantity}")
        else:
            sections.append("Empty")

        sections.append("\n## Instructions")
        sections.append("Based on the current situation, decide what action to take.")
        sections.append("Consider your goals, nearby resources, and any hazards.")

        return "\n".join(sections)


class DemoBackend(BaseBackend):
    """Mock backend for demonstration purposes."""

    def __init__(self, config: BackendConfig):
        super().__init__(config)
        self.decision_count = 0
        self.model_name = "demo-llm-v1"

    def is_available(self) -> bool:
        return True

    def generate(self, prompt: str, temperature=None, max_tokens=None) -> GenerationResult:
        self.decision_count += 1
        return GenerationResult(
            text=f'{{"tool": "idle", "params": {{}}, "reasoning": "Demo decision #{self.decision_count}"}}',
            tokens_used=42,
            finish_reason="stop",
            metadata={},
        )

    def generate_with_tools(
        self, prompt: str, tools: list[dict], temperature=None
    ) -> GenerationResult:
        self.decision_count += 1

        # Simulate different decisions based on count
        if self.decision_count == 1:
            return GenerationResult(
                text="I see an apple nearby. I should move closer to collect it.",
                tokens_used=50,
                finish_reason="stop",
                metadata={
                    "tool_call": {
                        "name": "move_to",
                        "arguments": {"target_position": [5.0, 0.0, 0.0]},
                    }
                },
            )
        elif self.decision_count == 2:
            return GenerationResult(
                text='{"tool": "pickup", "params": {"item_name": "apple"}, "reasoning": "Picking up the apple I just reached"}',
                tokens_used=35,
                finish_reason="stop",
                metadata={},
            )
        elif self.decision_count == 3:
            return GenerationResult(
                text="There's a fire hazard nearby. I should move away to safety.",
                tokens_used=45,
                finish_reason="stop",
                metadata={
                    "tool_call": {
                        "name": "move_to",
                        "arguments": {"target_position": [15.0, 0.0, 5.0]},
                    }
                },
            )
        else:
            return GenerationResult(
                text='{"tool": "idle", "params": {}, "reasoning": "Waiting and observing the environment"}',
                tokens_used=30,
                finish_reason="stop",
                metadata={},
            )

    def unload(self) -> None:
        pass


def create_observation(
    agent_id: str, tick: int, has_resources=False, has_hazards=False
) -> Observation:
    """Create a sample observation for testing."""
    resources = []
    hazards = []

    if has_resources:
        resources.append(
            ResourceInfo(
                name="apple",
                type="food",
                position=(5.0, 0.0, 0.0),
                distance=5.0,
            )
        )

    if has_hazards:
        hazards.append(
            HazardInfo(
                name="fire",
                type="hazard",
                position=(8.0, 0.0, 2.0),
                distance=8.5,
                damage=10.0,
            )
        )

    return Observation(
        agent_id=agent_id,
        tick=tick,
        position=(0.0, 0.0, 0.0),
        health=100.0,
        energy=95.0,
        nearby_resources=resources,
        nearby_hazards=hazards,
    )


def create_sample_tools() -> list[ToolSchema]:
    """Create sample tool schemas."""
    return [
        ToolSchema(
            name="move_to",
            description="Move to a target position",
            parameters={
                "type": "object",
                "properties": {
                    "target_position": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Target [x, y, z] position",
                    }
                },
                "required": ["target_position"],
            },
        ),
        ToolSchema(
            name="pickup",
            description="Pick up an item",
            parameters={
                "type": "object",
                "properties": {
                    "item_name": {"type": "string", "description": "Name of item to pick up"}
                },
                "required": ["item_name"],
            },
        ),
        ToolSchema(
            name="idle",
            description="Do nothing for this tick",
            parameters={"type": "object", "properties": {}},
        ),
    ]


def print_separator(title: str):
    """Print a section separator."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_capture_summary(capture):
    """Print a summary of a single capture."""
    print(f"Agent: {capture.agent_id}, Tick: {capture.tick}")
    print(f"Captured {len(capture.entries)} stages:")

    for entry in capture.entries:
        print(f"  - {entry.stage.value.upper()}")

        if entry.stage.value == "llm_response":
            data = entry.data
            print(f"    Latency: {data.get('latency_ms', 0):.0f}ms")
            print(f"    Tokens: {data.get('tokens_used', 0)}")
            print(f"    Response: {data.get('raw_text', '')[:60]}...")

        elif entry.stage.value == "decision":
            data = entry.data
            print(f"    Tool: {data.get('tool')}")
            print(f"    Reasoning: {data.get('reasoning')}")


def main():
    """Run the Prompt Inspector demo."""
    print_separator("Prompt Inspector Demo")

    # Configure inspector with file logging
    log_dir = Path("logs/inspector_demo")
    inspector = PromptInspector(
        enabled=True,
        max_entries=100,
        log_to_file=True,
        log_dir=log_dir,
    )

    print("[OK] Inspector configured")
    print(f"  - Enabled: {inspector.enabled}")
    print(f"  - Max entries: {inspector.max_entries}")
    print(f"  - Logging to: {log_dir}")

    # Create backend and behavior
    config = BackendConfig(model_path="demo_model")
    backend = DemoBackend(config)
    behavior = DemoLLMBehavior(
        backend=backend,
        system_prompt="You are a foraging agent. Collect resources and avoid hazards.",
        memory_capacity=5,
        inspector=inspector,
    )

    print("\n[OK] Created DemoLLMBehavior with DemoBackend")

    # Create sample tools
    tools = create_sample_tools()

    print_separator("Simulating Agent Decisions")

    # Simulate a sequence of decisions
    scenarios = [
        (1, True, False, "Agent sees an apple"),
        (2, True, False, "Agent is near the apple"),
        (3, False, True, "Agent encounters a fire hazard"),
        (4, False, False, "Agent is in safe area"),
    ]

    for tick, has_resources, has_hazards, description in scenarios:
        print(f"Tick {tick}: {description}")

        # Create observation
        observation = create_observation(
            agent_id="demo_agent",
            tick=tick,
            has_resources=has_resources,
            has_hazards=has_hazards,
        )

        # Make decision (this will be captured by the inspector)
        decision = behavior.decide(observation, tools)

        print(f"  -> Decision: {decision.tool}")
        print(f"  -> Reasoning: {decision.reasoning}")
        print()

    print_separator("Captured Data Summary")

    # Retrieve and display captures
    captures = inspector.get_captures_for_agent("demo_agent")
    print(f"Total captures: {len(captures)}\n")

    for capture in captures:
        print_capture_summary(capture)
        print()

    # Show JSON export
    print_separator("JSON Export Example")

    # Export first capture as JSON
    if captures:
        first_capture = captures[0]
        json_data = first_capture.to_dict()
        print(f"Capture for Tick {first_capture.tick}:")
        print(json.dumps(json_data, indent=2)[:500] + "...")

    # Show file logging results
    print_separator("File Logging Results")

    if log_dir.exists():
        log_files = list(log_dir.glob("*.json"))
        print(f"Created {len(log_files)} log file(s) in {log_dir}:")
        for log_file in sorted(log_files):
            print(f"  - {log_file.name}")
    else:
        print("No log files created (log directory doesn't exist)")

    # Demonstrate filtering
    print_separator("Filtering Examples")

    # Get captures for a specific tick range
    filtered = inspector.get_captures_for_agent("demo_agent", tick_start=2, tick_end=3)
    print(f"Captures for ticks 2-3: {len(filtered)}")
    for capture in filtered:
        print(f"  - Tick {capture.tick}")

    # Show how to access specific stages
    print_separator("Accessing Specific Stages")

    if captures:
        capture = captures[0]
        print(f"Examining Tick {capture.tick}:\n")

        for entry in capture.entries:
            print(f"{entry.stage.value.upper()}:")

            if entry.stage.value == "observation":
                print(f"  Position: {entry.data.get('position')}")
                print(f"  Health: {entry.data.get('health')}")
                print(f"  Resources: {len(entry.data.get('nearby_resources', []))}")

            elif entry.stage.value == "prompt_building":
                print(f"  Prompt length: {entry.data.get('prompt_length')} chars")
                print(f"  Estimated tokens: {entry.data.get('estimated_tokens')}")
                print(f"  Memory items: {entry.data.get('memory_context', {}).get('count', 0)}")

            elif entry.stage.value == "llm_request":
                print(f"  Model: {entry.data.get('model')}")
                print(f"  Temperature: {entry.data.get('temperature')}")
                print(f"  Available tools: {len(entry.data.get('tools', []))}")

            elif entry.stage.value == "llm_response":
                print(f"  Tokens used: {entry.data.get('tokens_used')}")
                print(f"  Latency: {entry.data.get('latency_ms', 0):.0f}ms")
                print(f"  Finish reason: {entry.data.get('finish_reason')}")

            elif entry.stage.value == "decision":
                print(f"  Tool: {entry.data.get('tool')}")
                print(f"  Params: {entry.data.get('params')}")
                print(f"  Reasoning: {entry.data.get('reasoning')}")

            print()

    print_separator("Demo Complete!")

    print("Next steps:")
    print("1. View log files in:", log_dir)
    print("2. Use CLI tool: python -m tools.inspect_prompts --agent demo_agent")
    print("3. Access via API (if IPC server running): GET /inspector/requests?agent_id=demo_agent")
    print()
    print("For more information, see: docs/prompt_inspector.md")


if __name__ == "__main__":
    main()
