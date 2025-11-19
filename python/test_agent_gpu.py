"""
End-to-end test of Agent with GPU-accelerated backend and tools.

This test demonstrates:
1. Creating a ToolDispatcher with sample tools
2. Initializing an Agent with GPU-accelerated LlamaCppBackend
3. Agent perceiving observations
4. Agent deciding actions using tools via LLM
5. Executing those actions through the ToolDispatcher
"""

import json
import logging
from backends import LlamaCppBackend, BackendConfig
from agent_runtime.agent import Agent, Action
from agent_runtime.tool_dispatcher import ToolDispatcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================
# Step 1: Create Sample Tools
# ============================================================

def create_tool_dispatcher() -> ToolDispatcher:
    """Create a ToolDispatcher with sample game tools."""
    dispatcher = ToolDispatcher()

    # Tool 1: Move to position
    def move_to(target_x: float, target_y: float, speed: float = 1.0) -> dict:
        """Move agent to target position."""
        distance = ((target_x**2) + (target_y**2)) ** 0.5
        time_estimate = distance / speed
        return {
            "success": True,
            "message": f"Moving to ({target_x}, {target_y}) at speed {speed}",
            "estimated_time": time_estimate,
            "distance": distance
        }

    dispatcher.register_tool(
        name="move_to",
        function=move_to,
        description="Move the agent to a target position in 2D space",
        parameters={
            "type": "object",
            "properties": {
                "target_x": {
                    "type": "number",
                    "description": "Target X coordinate"
                },
                "target_y": {
                    "type": "number",
                    "description": "Target Y coordinate"
                },
                "speed": {
                    "type": "number",
                    "description": "Movement speed (default 1.0)",
                    "default": 1.0
                }
            },
            "required": ["target_x", "target_y"]
        },
        returns={
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "message": {"type": "string"},
                "estimated_time": {"type": "number"},
                "distance": {"type": "number"}
            }
        }
    )

    # Tool 2: Collect resource
    def collect_resource(resource_name: str) -> dict:
        """Collect a resource from the environment."""
        valid_resources = ["wood", "stone", "food"]
        if resource_name in valid_resources:
            return {
                "success": True,
                "message": f"Collected {resource_name}",
                "resource": resource_name,
                "quantity": 1
            }
        else:
            return {
                "success": False,
                "message": f"Unknown resource: {resource_name}",
                "error": "Invalid resource type"
            }

    dispatcher.register_tool(
        name="collect_resource",
        function=collect_resource,
        description="Collect a resource (wood, stone, or food) from the current location",
        parameters={
            "type": "object",
            "properties": {
                "resource_name": {
                    "type": "string",
                    "description": "Name of resource to collect (wood, stone, or food)",
                    "enum": ["wood", "stone", "food"]
                }
            },
            "required": ["resource_name"]
        },
        returns={
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "message": {"type": "string"},
                "resource": {"type": "string"},
                "quantity": {"type": "number"}
            }
        }
    )

    # Tool 3: Check inventory
    def check_inventory() -> dict:
        """Check current inventory (mock data for demo)."""
        return {
            "success": True,
            "inventory": {
                "wood": 5,
                "stone": 3,
                "food": 2
            },
            "total_items": 10
        }

    dispatcher.register_tool(
        name="check_inventory",
        function=check_inventory,
        description="Check the agent's current inventory",
        parameters={
            "type": "object",
            "properties": {}
        },
        returns={
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "inventory": {"type": "object"},
                "total_items": {"type": "number"}
            }
        }
    )

    logger.info(f"Created ToolDispatcher with {len(dispatcher.tools)} tools")
    return dispatcher


# ============================================================
# Step 2: Enhanced Agent with Backend Integration
# ============================================================

class EnhancedAgent(Agent):
    """
    Enhanced Agent that properly integrates with LLM backend and tools.

    This extends the base Agent class to implement actual backend communication.
    """

    def __init__(self, agent_id: str, backend, tool_dispatcher: ToolDispatcher, goals: list[str] | None = None):
        # Get available tool names from dispatcher
        available_tools = list(tool_dispatcher.tools.keys())

        super().__init__(
            agent_id=agent_id,
            backend=backend,
            tools=available_tools,
            goals=goals
        )

        self.tool_dispatcher = tool_dispatcher

    def _query_llm(self, context: str) -> str:
        """
        Query the LLM backend with context and tool information.

        This overrides the placeholder in the base Agent class.
        """
        # Get tool schemas for the prompt
        tool_schemas = self.tool_dispatcher.export_schemas_json()

        # Build the prompt with Llama-2 chat format
        prompt = f"""[INST] You are an autonomous agent in a game world. You can use tools to interact with the environment.

{context}

Available tools (JSON format):
{tool_schemas}

Respond with ONLY a JSON object in this exact format:
{{"tool": "tool_name", "params": {{"param1": value1}}, "reasoning": "why you chose this action"}}

Choose the most appropriate tool based on your current observations and goals.
Your response (JSON only): [/INST]"""

        logger.debug(f"Querying LLM with prompt length: {len(prompt)} chars")

        # Query backend
        result = self.backend.generate(
            prompt=prompt,
            temperature=0.3,  # Lower temperature for more consistent JSON
            max_tokens=150
        )

        # Extract JSON from response
        response_text = result.text.strip()
        logger.info(f"LLM Response: {response_text}")

        # Try to extract JSON if model added extra text
        return self._extract_json(response_text)

    def _extract_json(self, text: str) -> str:
        """Extract JSON object from text that might contain extra content."""
        import re

        # Try to find JSON object in the response
        start = text.find('{')
        end = text.rfind('}')

        if start != -1 and end != -1:
            json_str = text[start:end+1]

            # Try to validate and return if valid
            try:
                json.loads(json_str)
                return json_str
            except json.JSONDecodeError as e:
                logger.debug(f"JSON parse error: {e}")

                # Common issue: missing comma between fields
                # Pattern: "value"\n"field" should be "value",\n"field"
                fixed_json = re.sub(r'([\d"])\s*\n\s*("(?:reasoning|tool|params))', r'\1,\n\2', json_str)

                try:
                    json.loads(fixed_json)
                    logger.debug("Fixed JSON by adding missing commas")
                    return fixed_json
                except json.JSONDecodeError:
                    # Fallback: extract key-value pairs manually
                    tool_match = re.search(r'"tool"\s*:\s*"([^"]+)"', text)
                    resource_match = re.search(r'"resource_name"\s*:\s*"([^"]+)"', text)
                    target_x_match = re.search(r'"target_x"\s*:\s*([\d.]+)', text)
                    target_y_match = re.search(r'"target_y"\s*:\s*([\d.]+)', text)

                    if tool_match:
                        tool = tool_match.group(1)
                        params = {}

                        # Extract parameters based on tool type
                        if tool == "collect_resource" and resource_match:
                            params = {"resource_name": resource_match.group(1)}
                        elif tool == "move_to" and target_x_match and target_y_match:
                            params = {
                                "target_x": float(target_x_match.group(1)),
                                "target_y": float(target_y_match.group(1))
                            }
                        elif tool == "check_inventory":
                            params = {}

                        reconstructed = {
                            "tool": tool,
                            "params": params
                        }

                        logger.debug(f"Reconstructed JSON from pattern matching: {reconstructed}")
                        return json.dumps(reconstructed)

        # Fallback: return original text
        logger.warning(f"Could not extract valid JSON from: {text[:200]}...")
        return text

    def execute_action(self, action: Action) -> dict:
        """Execute an action through the tool dispatcher."""
        if action is None:
            return {"success": False, "error": "No action provided"}

        logger.info(f"Executing action: {action.tool_name} with params {action.parameters}")
        result = self.tool_dispatcher.execute_tool(action.tool_name, action.parameters)

        return result


# ============================================================
# Step 3: Test Scenarios
# ============================================================

def test_scenario_1_resource_collection():
    """
    Scenario: Agent sees wood nearby and should collect it.
    """
    print("\n" + "="*60)
    print("SCENARIO 1: Resource Collection")
    print("="*60)

    # Setup
    dispatcher = create_tool_dispatcher()

    config = BackendConfig(
        model_path="../models/llama-2-7b-chat.Q4_K_M.gguf",
        temperature=0.3,
        max_tokens=150,
        n_gpu_layers=-1  # Full GPU acceleration
    )
    backend = LlamaCppBackend(config)

    agent = EnhancedAgent(
        agent_id="forager_001",
        backend=backend,
        tool_dispatcher=dispatcher,
        goals=["collect resources for crafting"]
    )

    # Simulate observations
    print("\n[Simulation] Agent observes environment...")
    agent.perceive({
        "position": {"x": 0, "y": 0},
        "visible_objects": [
            {"type": "wood", "distance": 2.5, "position": {"x": 2, "y": 1}},
            {"type": "tree", "distance": 5.0}
        ],
        "inventory_count": 10
    }, source="vision")

    # Agent decides action
    print("\n[Agent] Deciding action based on observations and goals...")
    action = agent.decide_action()

    if action:
        print(f"\n[Agent] Decided to use: {action.tool_name}")
        print(f"[Agent] Parameters: {action.parameters}")
        if action.reasoning:
            print(f"[Agent] Reasoning: {action.reasoning}")

        # Execute the action
        print("\n[Execution] Running tool...")
        result = agent.execute_action(action)
        print(f"[Result] {result}")
    else:
        print("\n[Agent] Failed to decide action")

    backend.unload()
    print("\n" + "="*60)


def test_scenario_2_navigation():
    """
    Scenario: Agent needs to move to a target location.
    """
    print("\n" + "="*60)
    print("SCENARIO 2: Navigation")
    print("="*60)

    # Setup
    dispatcher = create_tool_dispatcher()

    config = BackendConfig(
        model_path="../models/llama-2-7b-chat.Q4_K_M.gguf",
        temperature=0.3,
        max_tokens=150,
        n_gpu_layers=-1
    )
    backend = LlamaCppBackend(config)

    agent = EnhancedAgent(
        agent_id="explorer_001",
        backend=backend,
        tool_dispatcher=dispatcher,
        goals=["explore the map", "find the tower at (10, 15)"]
    )

    # Simulate observations
    print("\n[Simulation] Agent receives navigation task...")
    agent.perceive({
        "position": {"x": 0, "y": 0},
        "target_location": {"x": 10, "y": 15},
        "obstacles": []
    }, source="navigation")

    # Agent decides action
    print("\n[Agent] Deciding navigation action...")
    action = agent.decide_action()

    if action:
        print(f"\n[Agent] Decided to use: {action.tool_name}")
        print(f"[Agent] Parameters: {action.parameters}")
        if action.reasoning:
            print(f"[Agent] Reasoning: {action.reasoning}")

        # Execute the action
        print("\n[Execution] Running tool...")
        result = agent.execute_action(action)
        print(f"[Result] {result}")
    else:
        print("\n[Agent] Failed to decide action")

    backend.unload()
    print("\n" + "="*60)


def test_scenario_3_inventory_check():
    """
    Scenario: Agent checks inventory before crafting.
    """
    print("\n" + "="*60)
    print("SCENARIO 3: Inventory Management")
    print("="*60)

    # Setup
    dispatcher = create_tool_dispatcher()

    config = BackendConfig(
        model_path="../models/llama-2-7b-chat.Q4_K_M.gguf",
        temperature=0.3,
        max_tokens=150,
        n_gpu_layers=-1
    )
    backend = LlamaCppBackend(config)

    agent = EnhancedAgent(
        agent_id="crafter_001",
        backend=backend,
        tool_dispatcher=dispatcher,
        goals=["craft a wooden tool", "check if we have enough materials"]
    )

    # Simulate observations
    print("\n[Simulation] Agent wants to craft something...")
    agent.perceive({
        "crafting_station": "workbench",
        "recipe_requires": {"wood": 3, "stone": 1},
        "action": "prepare_crafting"
    }, source="crafting")

    # Agent decides action
    print("\n[Agent] Deciding what to do before crafting...")
    action = agent.decide_action()

    if action:
        print(f"\n[Agent] Decided to use: {action.tool_name}")
        print(f"[Agent] Parameters: {action.parameters}")
        if action.reasoning:
            print(f"[Agent] Reasoning: {action.reasoning}")

        # Execute the action
        print("\n[Execution] Running tool...")
        result = agent.execute_action(action)
        print(f"[Result] {result}")
    else:
        print("\n[Agent] Failed to decide action")

    backend.unload()
    print("\n" + "="*60)


# ============================================================
# Main Test Runner
# ============================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("Agent + GPU Backend + Tools Integration Test")
    print("="*60)
    print("\nThis test demonstrates an autonomous agent using:")
    print("  - GPU-accelerated Llama-2-7B backend (113 tok/s)")
    print("  - ToolDispatcher with 3 sample tools")
    print("  - Perception-Reasoning-Action loop")
    print("\nRunning 3 scenarios...\n")

    try:
        # Run test scenarios
        test_scenario_1_resource_collection()
        test_scenario_2_navigation()
        test_scenario_3_inventory_check()

        print("\n" + "="*60)
        print("All scenarios completed!")
        print("="*60)

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print(f"\nTest failed: {e}")
