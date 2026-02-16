"""
Tool schemas for defining available actions.
"""

from dataclasses import dataclass


@dataclass
class ToolSchema:
    """
    Schema for an available tool/action.

    Attributes:
        name: Tool identifier
        description: Human-readable description
        parameters: JSON Schema format parameters
    """

    name: str
    description: str
    parameters: dict  # JSON Schema format

    def to_openai_format(self) -> dict:
        """
        Convert to OpenAI function calling format.

        Returns:
            Dictionary in OpenAI function calling format
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def to_anthropic_format(self) -> dict:
        """
        Convert to Anthropic tool calling format.

        Returns:
            Dictionary in Anthropic tool calling format
        """
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ToolSchema":
        """Create ToolSchema from dictionary."""
        return cls(
            name=data["name"],
            description=data["description"],
            parameters=data["parameters"],
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }
