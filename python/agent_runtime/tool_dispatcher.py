"""
Tool Dispatcher - manages tool registration and execution for agents.
"""

from typing import Any, Callable, Dict, Optional
from dataclasses import dataclass
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class ToolSchema:
    """Schema definition for a tool."""

    name: str
    description: str
    parameters: Dict[str, Any]  # JSON schema for parameters
    returns: Dict[str, Any]  # JSON schema for return value


class ToolDispatcher:
    """
    Manages tool registration and execution.

    Tools are callable functions that agents can use to interact with the world.
    Each tool has a schema defining its parameters and return values.
    """

    def __init__(self):
        """Initialize the tool dispatcher."""
        self.tools: Dict[str, Callable] = {}
        self.schemas: Dict[str, ToolSchema] = {}

        logger.info("Initialized ToolDispatcher")

    def register_tool(
        self,
        name: str,
        function: Callable,
        description: str,
        parameters: Dict[str, Any],
        returns: Dict[str, Any],
    ) -> None:
        """
        Register a tool with the dispatcher.

        Args:
            name: Unique tool name
            function: Callable function implementing the tool
            description: Human-readable description
            parameters: JSON schema for parameters
            returns: JSON schema for return value
        """
        schema = ToolSchema(
            name=name,
            description=description,
            parameters=parameters,
            returns=returns,
        )

        self.tools[name] = function
        self.schemas[name] = schema

        logger.info(f"Registered tool: {name}")

    def unregister_tool(self, name: str) -> None:
        """Unregister a tool."""
        if name in self.tools:
            del self.tools[name]
            del self.schemas[name]
            logger.info(f"Unregistered tool: {name}")

    def execute_tool(self, name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool with given parameters.

        Args:
            name: Tool name
            parameters: Tool parameters

        Returns:
            Dictionary with 'success' bool and 'result' or 'error'
        """
        if name not in self.tools:
            logger.error(f"Tool not found: {name}")
            return {
                "success": False,
                "error": f"Tool '{name}' not found",
            }

        try:
            # Validate parameters against schema
            if not self._validate_parameters(name, parameters):
                return {
                    "success": False,
                    "error": f"Invalid parameters for tool '{name}'",
                }

            # Execute the tool
            result = self.tools[name](**parameters)

            logger.debug(f"Executed tool {name} successfully")
            return {
                "success": True,
                "result": result,
            }

        except Exception as e:
            logger.error(f"Error executing tool {name}: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def _validate_parameters(self, tool_name: str, parameters: Dict[str, Any]) -> bool:
        """
        Validate parameters against tool schema.

        Args:
            tool_name: Name of the tool
            parameters: Parameters to validate

        Returns:
            True if valid, False otherwise
        """
        schema = self.schemas[tool_name]
        param_schema = schema.parameters

        # Basic validation - check required parameters exist
        required = param_schema.get("required", [])
        for param in required:
            if param not in parameters:
                logger.error(f"Missing required parameter '{param}' for tool {tool_name}")
                return False

        # TODO: More thorough JSON schema validation
        return True

    def get_tool_schema(self, name: str) -> Optional[ToolSchema]:
        """Get the schema for a tool."""
        return self.schemas.get(name)

    def get_all_schemas(self) -> Dict[str, ToolSchema]:
        """Get all tool schemas."""
        return self.schemas.copy()

    def export_schemas_json(self) -> str:
        """
        Export all tool schemas as JSON for LLM function calling.

        Returns:
            JSON string of all tool schemas
        """
        schemas = []
        for schema in self.schemas.values():
            schemas.append(
                {
                    "name": schema.name,
                    "description": schema.description,
                    "parameters": schema.parameters,
                    "returns": schema.returns,
                }
            )

        return json.dumps(schemas, indent=2)
