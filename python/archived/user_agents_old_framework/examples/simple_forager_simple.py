"""
Simple Foraging Agent - Beginner-Friendly Example.

This demonstrates the SimpleAgentBehavior interface which:
- Automatically handles memory
- Infers tool parameters from context
- Requires minimal code
- Perfect for learning the basics
"""

from agent_runtime import SimpleAgentBehavior


class SimpleForagerSimple(SimpleAgentBehavior):
    """
    Beginner-friendly foraging agent using SimpleAgentBehavior.

    This agent shows how easy it is to create an agent with the simplified interface.
    You only need to implement decide() and return a tool name - the framework
    handles everything else!

    Behavior:
    - Avoid hazards if too close
    - Pick up resources if nearby
    - Move to resources if visible
    - Idle otherwise
    """

    # Customize these class attributes
    system_prompt = "You are a foraging agent. Collect resources and avoid hazards."
    memory_capacity = 5

    def decide(self, context):
        """
        Decide which tool to use based on the current context.

        The framework will automatically infer parameters based on your choice!

        Args:
            context: SimpleContext with position, resources, hazards, inventory

        Returns:
            Tool name (string): "move_to", "pickup", "drop", "use", or "idle"
        """
        # Priority 1: Avoid hazards
        if context.nearby_hazards:
            nearest_hazard = min(context.nearby_hazards, key=lambda h: h["distance"])
            if nearest_hazard["distance"] < 3.0:
                # Framework will infer escape direction
                return "move_to"

        # Priority 2: Pick up nearby resources
        if context.nearby_resources:
            nearest = min(context.nearby_resources, key=lambda r: r["distance"])
            if nearest["distance"] < 1.0:
                # Framework will infer which item to pick up
                return "pickup"

            # Move to resource
            # Framework will infer target position
            return "move_to"

        # Default: Idle
        return "idle"
