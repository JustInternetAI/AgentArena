"""
Decision schema - what the agent returns to the game.
"""

from dataclasses import dataclass, field


@dataclass
class Decision:
    """
    What the agent returns to the game each tick.

    This is a simplified decision format focused on tool selection.
    The agent picks a tool and provides parameters.

    Attributes:
        tool: Name of the tool to execute
        params: Dictionary of parameters for the tool
        reasoning: Optional reasoning explanation for debugging

    Example:
        # Move to a position
        Decision(
            tool="move_to",
            params={"target_position": [10.0, 0.0, 5.0]},
            reasoning="Moving toward nearest berry"
        )

        # Collect a resource
        Decision(
            tool="collect",
            params={"target_name": "berry_001"}
        )

        # Do nothing this tick
        Decision.idle("Waiting for resources to spawn")
    """

    tool: str
    params: dict = field(default_factory=dict)
    reasoning: str | None = None

    @classmethod
    def idle(cls, reasoning: str | None = None) -> "Decision":
        """
        Create an idle decision (do nothing this tick).

        Args:
            reasoning: Optional explanation for why idling

        Returns:
            Decision with idle tool
        """
        return cls(tool="idle", params={}, reasoning=reasoning)

    @classmethod
    def from_dict(cls, data: dict) -> "Decision":
        """
        Create Decision from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            Decision instance
        """
        return cls(
            tool=data["tool"],
            params=data.get("params", {}),
            reasoning=data.get("reasoning"),
        )

    def to_dict(self) -> dict:
        """
        Convert to dictionary for serialization.

        Returns:
            Dictionary representation
        """
        result = {
            "tool": self.tool,
            "params": self.params,
        }
        if self.reasoning is not None:
            result["reasoning"] = self.reasoning
        return result
