"""
Tests for ToolDispatcher.
"""

import pytest
from agent_runtime.tool_dispatcher import ToolDispatcher


def dummy_tool(x: int, y: int) -> int:
    """Simple test tool."""
    return x + y


def test_tool_registration():
    """Test registering a tool."""
    dispatcher = ToolDispatcher()

    dispatcher.register_tool(
        name="add",
        function=dummy_tool,
        description="Adds two numbers",
        parameters={
            "type": "object",
            "properties": {
                "x": {"type": "integer"},
                "y": {"type": "integer"},
            },
            "required": ["x", "y"],
        },
        returns={"type": "integer"},
    )

    assert "add" in dispatcher.tools
    assert "add" in dispatcher.schemas


def test_tool_execution():
    """Test executing a registered tool."""
    dispatcher = ToolDispatcher()

    dispatcher.register_tool(
        name="add",
        function=dummy_tool,
        description="Adds two numbers",
        parameters={
            "type": "object",
            "properties": {
                "x": {"type": "integer"},
                "y": {"type": "integer"},
            },
            "required": ["x", "y"],
        },
        returns={"type": "integer"},
    )

    result = dispatcher.execute_tool("add", {"x": 5, "y": 3})

    assert result["success"] is True
    assert result["result"] == 8


def test_tool_not_found():
    """Test executing non-existent tool."""
    dispatcher = ToolDispatcher()

    result = dispatcher.execute_tool("nonexistent", {})

    assert result["success"] is False
    assert "not found" in result["error"]


def test_tool_validation():
    """Test parameter validation."""
    dispatcher = ToolDispatcher()

    dispatcher.register_tool(
        name="add",
        function=dummy_tool,
        description="Adds two numbers",
        parameters={
            "type": "object",
            "properties": {
                "x": {"type": "integer"},
                "y": {"type": "integer"},
            },
            "required": ["x", "y"],
        },
        returns={"type": "integer"},
    )

    # Missing required parameter
    result = dispatcher.execute_tool("add", {"x": 5})

    assert result["success"] is False
    assert "Invalid parameters" in result["error"]


def test_tool_unregistration():
    """Test unregistering a tool."""
    dispatcher = ToolDispatcher()

    dispatcher.register_tool(
        name="add",
        function=dummy_tool,
        description="Test",
        parameters={"type": "object"},
        returns={"type": "integer"},
    )

    assert "add" in dispatcher.tools

    dispatcher.unregister_tool("add")

    assert "add" not in dispatcher.tools
    assert "add" not in dispatcher.schemas


def test_get_tool_schema():
    """Test retrieving tool schema."""
    dispatcher = ToolDispatcher()

    dispatcher.register_tool(
        name="add",
        function=dummy_tool,
        description="Adds numbers",
        parameters={"type": "object"},
        returns={"type": "integer"},
    )

    schema = dispatcher.get_tool_schema("add")

    assert schema is not None
    assert schema.name == "add"
    assert schema.description == "Adds numbers"


def test_export_schemas_json():
    """Test exporting schemas as JSON."""
    dispatcher = ToolDispatcher()

    dispatcher.register_tool(
        name="tool1",
        function=dummy_tool,
        description="First tool",
        parameters={"type": "object"},
        returns={"type": "integer"},
    )

    dispatcher.register_tool(
        name="tool2",
        function=dummy_tool,
        description="Second tool",
        parameters={"type": "object"},
        returns={"type": "string"},
    )

    json_str = dispatcher.export_schemas_json()

    assert "tool1" in json_str
    assert "tool2" in json_str
    assert "First tool" in json_str


def test_tool_error_handling():
    """Test error handling in tool execution."""

    def error_tool():
        raise ValueError("Test error")

    dispatcher = ToolDispatcher()

    dispatcher.register_tool(
        name="error_tool",
        function=error_tool,
        description="Tool that errors",
        parameters={"type": "object"},
        returns={"type": "null"},
    )

    result = dispatcher.execute_tool("error_tool", {})

    assert result["success"] is False
    assert "Test error" in result["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
