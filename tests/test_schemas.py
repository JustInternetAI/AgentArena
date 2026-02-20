"""
Tests for core schemas and data contracts.
"""

import json
import pytest

from agent_runtime.schemas import (
    AgentDecision,
    EntityInfo,
    HazardInfo,
    ItemInfo,
    Observation,
    ResourceInfo,
    SimpleContext,
    StationInfo,
    ToolSchema,
)


class TestEntityInfo:
    """Tests for EntityInfo dataclass."""

    def test_create_entity_info(self):
        """Test basic EntityInfo creation."""
        entity = EntityInfo(
            id="enemy_1",
            type="hostile",
            position=(10.0, 0.0, 5.0),
            distance=11.2,
            metadata={"health": 50},
        )
        assert entity.id == "enemy_1"
        assert entity.type == "hostile"
        assert entity.position == (10.0, 0.0, 5.0)
        assert entity.distance == 11.2
        assert entity.metadata == {"health": 50}

    def test_entity_info_default_metadata(self):
        """Test EntityInfo with default metadata."""
        entity = EntityInfo(
            id="npc_1",
            type="friendly",
            position=(0.0, 0.0, 0.0),
            distance=0.0,
        )
        assert entity.metadata == {}


class TestResourceInfo:
    """Tests for ResourceInfo dataclass."""

    def test_create_resource_info(self):
        """Test basic ResourceInfo creation."""
        resource = ResourceInfo(
            name="apple",
            type="food",
            position=(5.0, 1.0, 3.0),
            distance=6.0,
        )
        assert resource.name == "apple"
        assert resource.type == "food"
        assert resource.position == (5.0, 1.0, 3.0)
        assert resource.distance == 6.0


class TestHazardInfo:
    """Tests for HazardInfo dataclass."""

    def test_create_hazard_info(self):
        """Test basic HazardInfo creation."""
        hazard = HazardInfo(
            name="lava_pit",
            type="environmental",
            position=(10.0, 0.0, 10.0),
            distance=14.1,
            damage=50.0,
        )
        assert hazard.name == "lava_pit"
        assert hazard.type == "environmental"
        assert hazard.damage == 50.0

    def test_hazard_info_default_damage(self):
        """Test HazardInfo with default damage."""
        hazard = HazardInfo(
            name="spike_trap",
            type="trap",
            position=(0.0, 0.0, 0.0),
            distance=0.0,
        )
        assert hazard.damage == 0.0


class TestStationInfo:
    """Tests for StationInfo dataclass."""

    def test_create_station_info(self):
        """Test basic StationInfo creation."""
        station = StationInfo(
            name="Workbench",
            type="workbench",
            position=(12.0, 0.0, 10.0),
            distance=5.5,
        )
        assert station.name == "Workbench"
        assert station.type == "workbench"
        assert station.position == (12.0, 0.0, 10.0)
        assert station.distance == 5.5

    def test_station_info_anvil(self):
        """Test StationInfo for anvil type."""
        station = StationInfo(
            name="Anvil",
            type="anvil",
            position=(-10.0, 0.0, -8.0),
            distance=12.8,
        )
        assert station.type == "anvil"


class TestItemInfo:
    """Tests for ItemInfo dataclass."""

    def test_create_item_info(self):
        """Test basic ItemInfo creation."""
        item = ItemInfo(id="item_1", name="sword", quantity=1)
        assert item.id == "item_1"
        assert item.name == "sword"
        assert item.quantity == 1

    def test_item_info_default_quantity(self):
        """Test ItemInfo with default quantity."""
        item = ItemInfo(id="item_2", name="potion")
        assert item.quantity == 1


class TestToolSchema:
    """Tests for ToolSchema dataclass."""

    def test_create_tool_schema(self):
        """Test basic ToolSchema creation."""
        schema = ToolSchema(
            name="move_to",
            description="Move to a target position",
            parameters={
                "type": "object",
                "properties": {
                    "x": {"type": "number"},
                    "y": {"type": "number"},
                },
                "required": ["x", "y"],
            },
        )
        assert schema.name == "move_to"
        assert schema.description == "Move to a target position"
        assert "properties" in schema.parameters

    def test_to_openai_format(self):
        """Test conversion to OpenAI format."""
        schema = ToolSchema(
            name="pickup",
            description="Pick up an item",
            parameters={
                "type": "object",
                "properties": {"item_id": {"type": "string"}},
                "required": ["item_id"],
            },
        )
        openai_format = schema.to_openai_format()
        assert openai_format["type"] == "function"
        assert openai_format["function"]["name"] == "pickup"
        assert openai_format["function"]["description"] == "Pick up an item"
        assert openai_format["function"]["parameters"] == schema.parameters

    def test_to_anthropic_format(self):
        """Test conversion to Anthropic format."""
        schema = ToolSchema(
            name="drop",
            description="Drop an item",
            parameters={
                "type": "object",
                "properties": {"item_id": {"type": "string"}},
            },
        )
        anthropic_format = schema.to_anthropic_format()
        assert anthropic_format["name"] == "drop"
        assert anthropic_format["description"] == "Drop an item"
        assert anthropic_format["input_schema"] == schema.parameters

    def test_from_dict(self):
        """Test creating ToolSchema from dictionary."""
        data = {
            "name": "attack",
            "description": "Attack a target",
            "parameters": {
                "type": "object",
                "properties": {"target_id": {"type": "string"}},
            },
        }
        schema = ToolSchema.from_dict(data)
        assert schema.name == "attack"
        assert schema.description == "Attack a target"
        assert schema.parameters == data["parameters"]


class TestObservation:
    """Tests for Observation dataclass."""

    def test_create_minimal_observation(self):
        """Test creating observation with minimal required fields."""
        obs = Observation(
            agent_id="agent_1",
            tick=10,
            position=(0.0, 0.0, 0.0),
        )
        assert obs.agent_id == "agent_1"
        assert obs.tick == 10
        assert obs.position == (0.0, 0.0, 0.0)
        assert obs.rotation is None
        assert obs.velocity is None
        assert obs.visible_entities == []
        assert obs.nearby_resources == []
        assert obs.nearby_hazards == []
        assert obs.inventory == []
        assert obs.health == 100.0
        assert obs.energy == 100.0
        assert obs.custom == {}

    def test_create_full_observation(self):
        """Test creating observation with all fields."""
        obs = Observation(
            agent_id="agent_1",
            tick=10,
            position=(1.0, 2.0, 3.0),
            rotation=(0.0, 90.0, 0.0),
            velocity=(1.0, 0.0, 0.0),
            visible_entities=[
                EntityInfo(
                    id="enemy_1",
                    type="hostile",
                    position=(10.0, 0.0, 5.0),
                    distance=11.2,
                )
            ],
            nearby_resources=[
                ResourceInfo(
                    name="apple",
                    type="food",
                    position=(5.0, 1.0, 3.0),
                    distance=6.0,
                )
            ],
            nearby_hazards=[
                HazardInfo(
                    name="fire",
                    type="environmental",
                    position=(15.0, 0.0, 0.0),
                    distance=15.0,
                    damage=10.0,
                )
            ],
            inventory=[ItemInfo(id="item_1", name="sword", quantity=1)],
            health=85.0,
            energy=70.0,
            custom={"score": 100},
        )
        assert obs.agent_id == "agent_1"
        assert len(obs.visible_entities) == 1
        assert len(obs.nearby_resources) == 1
        assert len(obs.nearby_hazards) == 1
        assert len(obs.inventory) == 1
        assert obs.health == 85.0
        assert obs.energy == 70.0
        assert obs.custom["score"] == 100

    def test_observation_to_dict(self):
        """Test converting observation to dictionary."""
        obs = Observation(
            agent_id="agent_1",
            tick=5,
            position=(1.0, 2.0, 3.0),
            rotation=(0.0, 45.0, 0.0),
            health=90.0,
        )
        data = obs.to_dict()
        assert data["agent_id"] == "agent_1"
        assert data["tick"] == 5
        assert data["position"] == [1.0, 2.0, 3.0]
        assert data["rotation"] == [0.0, 45.0, 0.0]
        assert data["health"] == 90.0
        assert isinstance(data["position"], list)

    def test_observation_from_dict(self):
        """Test creating observation from dictionary."""
        data = {
            "agent_id": "agent_2",
            "tick": 15,
            "position": [5.0, 0.0, 10.0],
            "rotation": [0.0, 0.0, 0.0],
            "velocity": [2.0, 0.0, 1.0],
            "visible_entities": [
                {
                    "id": "tree_1",
                    "type": "obstacle",
                    "position": [6.0, 0.0, 11.0],
                    "distance": 1.4,
                    "metadata": {"height": 10},
                }
            ],
            "nearby_resources": [
                {
                    "name": "wood",
                    "type": "material",
                    "position": [6.0, 0.0, 11.0],
                    "distance": 1.4,
                }
            ],
            "nearby_hazards": [
                {
                    "name": "poison_cloud",
                    "type": "environmental",
                    "position": [20.0, 0.0, 20.0],
                    "distance": 28.3,
                    "damage": 5.0,
                }
            ],
            "inventory": [
                {"id": "item_1", "name": "axe", "quantity": 1},
                {"id": "item_2", "name": "apple", "quantity": 3},
            ],
            "health": 75.0,
            "energy": 50.0,
            "custom": {"level": 5},
        }
        obs = Observation.from_dict(data)
        assert obs.agent_id == "agent_2"
        assert obs.tick == 15
        assert obs.position == (5.0, 0.0, 10.0)
        assert obs.rotation == (0.0, 0.0, 0.0)
        assert obs.velocity == (2.0, 0.0, 1.0)
        assert len(obs.visible_entities) == 1
        assert obs.visible_entities[0].id == "tree_1"
        assert obs.visible_entities[0].metadata["height"] == 10
        assert len(obs.nearby_resources) == 1
        assert obs.nearby_resources[0].name == "wood"
        assert len(obs.nearby_hazards) == 1
        assert obs.nearby_hazards[0].damage == 5.0
        assert len(obs.inventory) == 2
        assert obs.inventory[1].quantity == 3
        assert obs.health == 75.0
        assert obs.energy == 50.0
        assert obs.custom["level"] == 5

    def test_observation_from_dict_with_stations(self):
        """Test creating observation with nearby_stations."""
        data = {
            "agent_id": "agent_craft",
            "tick": 42,
            "position": [5.0, 1.0, 3.0],
            "nearby_resources": [],
            "nearby_hazards": [],
            "nearby_stations": [
                {
                    "name": "Workbench",
                    "type": "workbench",
                    "position": [12.0, 0.0, 10.0],
                    "distance": 8.5,
                },
                {
                    "name": "Anvil",
                    "type": "anvil",
                    "position": [-10.0, 0.0, -8.0],
                    "distance": 16.2,
                },
            ],
            "inventory": [],
            "health": 100.0,
        }
        obs = Observation.from_dict(data)
        assert len(obs.nearby_stations) == 2
        assert obs.nearby_stations[0].name == "Workbench"
        assert obs.nearby_stations[0].type == "workbench"
        assert obs.nearby_stations[0].position == (12.0, 0.0, 10.0)
        assert obs.nearby_stations[0].distance == 8.5
        assert obs.nearby_stations[1].type == "anvil"

    def test_observation_from_dict_without_stations(self):
        """Test observation from_dict gracefully handles missing stations."""
        data = {
            "agent_id": "agent_no_stations",
            "tick": 1,
            "position": [0.0, 0.0, 0.0],
        }
        obs = Observation.from_dict(data)
        assert obs.nearby_stations == []

    def test_observation_roundtrip_with_stations(self):
        """Test observation serialization roundtrip with stations."""
        original = Observation(
            agent_id="agent_rt",
            tick=10,
            position=(1.0, 0.0, 2.0),
            nearby_stations=[
                StationInfo(
                    name="Workbench",
                    type="workbench",
                    position=(12.0, 0.0, 10.0),
                    distance=11.0,
                )
            ],
        )
        data = original.to_dict()
        assert len(data["nearby_stations"]) == 1
        assert data["nearby_stations"][0]["name"] == "Workbench"
        assert data["nearby_stations"][0]["position"] == [12.0, 0.0, 10.0]

        reconstructed = Observation.from_dict(data)
        assert len(reconstructed.nearby_stations) == 1
        assert reconstructed.nearby_stations[0].name == "Workbench"
        assert reconstructed.nearby_stations[0].type == "workbench"

    def test_observation_roundtrip(self):
        """Test observation serialization roundtrip."""
        original = Observation(
            agent_id="agent_3",
            tick=20,
            position=(10.0, 5.0, 15.0),
            rotation=(45.0, 90.0, 0.0),
            nearby_resources=[
                ResourceInfo(
                    name="gold",
                    type="currency",
                    position=(12.0, 5.0, 16.0),
                    distance=2.2,
                )
            ],
            health=60.0,
        )
        data = original.to_dict()
        reconstructed = Observation.from_dict(data)
        assert reconstructed.agent_id == original.agent_id
        assert reconstructed.tick == original.tick
        assert reconstructed.position == original.position
        assert reconstructed.rotation == original.rotation
        assert len(reconstructed.nearby_resources) == 1
        assert reconstructed.nearby_resources[0].name == "gold"
        assert reconstructed.health == original.health


class TestAgentDecision:
    """Tests for AgentDecision dataclass."""

    def test_create_decision(self):
        """Test basic AgentDecision creation."""
        decision = AgentDecision(
            tool="move_to",
            params={"x": 10.0, "y": 5.0},
            reasoning="Moving towards the resource",
        )
        assert decision.tool == "move_to"
        assert decision.params == {"x": 10.0, "y": 5.0}
        assert decision.reasoning == "Moving towards the resource"

    def test_idle_decision(self):
        """Test creating idle decision."""
        decision = AgentDecision.idle("Waiting for target")
        assert decision.tool == "idle"
        assert decision.params == {}
        assert decision.reasoning == "Waiting for target"

    def test_idle_decision_no_reasoning(self):
        """Test creating idle decision without reasoning."""
        decision = AgentDecision.idle()
        assert decision.tool == "idle"
        assert decision.params == {}
        assert decision.reasoning is None

    def test_decision_to_dict(self):
        """Test converting decision to dictionary."""
        decision = AgentDecision(
            tool="attack",
            params={"target_id": "enemy_1"},
            reasoning="Target is in range",
        )
        data = decision.to_dict()
        assert data["tool"] == "attack"
        assert data["params"] == {"target_id": "enemy_1"}
        assert data["reasoning"] == "Target is in range"

    def test_decision_to_dict_no_reasoning(self):
        """Test converting decision without reasoning to dictionary."""
        decision = AgentDecision(tool="pickup", params={"item_id": "item_1"})
        data = decision.to_dict()
        assert data["tool"] == "pickup"
        assert data["params"] == {"item_id": "item_1"}
        assert "reasoning" not in data

    def test_from_llm_response_valid_json_string(self):
        """Test parsing valid JSON string."""
        response = '{"tool": "move_to", "params": {"x": 5.0, "y": 10.0}, "reasoning": "Going to resource"}'
        decision = AgentDecision.from_llm_response(response)
        assert decision.tool == "move_to"
        assert decision.params == {"x": 5.0, "y": 10.0}
        assert decision.reasoning == "Going to resource"

    def test_from_llm_response_dict(self):
        """Test parsing dict directly."""
        response = {"tool": "attack", "params": {"target_id": "enemy_1"}}
        decision = AgentDecision.from_llm_response(response)
        assert decision.tool == "attack"
        assert decision.params == {"target_id": "enemy_1"}

    def test_from_llm_response_alternate_field_names(self):
        """Test parsing with alternate field names."""
        # Test 'action' instead of 'tool'
        response = {"action": "flee", "parameters": {"direction": "north"}}
        decision = AgentDecision.from_llm_response(response)
        assert decision.tool == "flee"
        assert decision.params == {"direction": "north"}

        # Test 'tool_name' instead of 'tool'
        response = {"tool_name": "craft", "arguments": {"item": "sword"}}
        decision = AgentDecision.from_llm_response(response)
        assert decision.tool == "craft"
        assert decision.params == {"item": "sword"}

    def test_from_llm_response_missing_tool(self):
        """Test parsing when tool field is missing (should default to idle)."""
        response = {"params": {"x": 1.0}}
        decision = AgentDecision.from_llm_response(response)
        assert decision.tool == "idle"
        assert decision.params == {"x": 1.0}

    def test_from_llm_response_code_block(self):
        """Test parsing JSON from markdown code block."""
        response = """Here's my decision:
```json
{
    "tool": "explore",
    "params": {"direction": "east"},
    "reasoning": "Unexplored area"
}
```
"""
        decision = AgentDecision.from_llm_response(response)
        assert decision.tool == "explore"
        assert decision.params == {"direction": "east"}
        assert decision.reasoning == "Unexplored area"

    def test_from_llm_response_code_block_no_json_tag(self):
        """Test parsing JSON from markdown code block without json tag."""
        response = """
```
{"tool": "hide", "params": {"location": "bush"}}
```
"""
        decision = AgentDecision.from_llm_response(response)
        assert decision.tool == "hide"
        assert decision.params == {"location": "bush"}

    def test_from_llm_response_invalid_json(self):
        """Test handling of completely invalid JSON."""
        response = "This is not JSON at all"
        with pytest.raises(ValueError, match="Invalid JSON"):
            AgentDecision.from_llm_response(response)

    def test_from_llm_response_malformed_json(self):
        """Test handling of malformed JSON."""
        response = '{"tool": "move", "params": {'
        with pytest.raises(ValueError, match="Invalid JSON"):
            AgentDecision.from_llm_response(response)

    def test_from_llm_response_alternate_reasoning_fields(self):
        """Test parsing with alternate reasoning field names."""
        # Test 'thought' instead of 'reasoning'
        response = {"tool": "wait", "params": {}, "thought": "Observing"}
        decision = AgentDecision.from_llm_response(response)
        assert decision.reasoning == "Observing"

        # Test 'explanation' instead of 'reasoning'
        response = {"tool": "retreat", "params": {}, "explanation": "Low health"}
        decision = AgentDecision.from_llm_response(response)
        assert decision.reasoning == "Low health"


class TestSimpleContext:
    """Tests for SimpleContext dataclass."""

    def test_create_simple_context(self):
        """Test basic SimpleContext creation."""
        context = SimpleContext(
            position=(1.0, 2.0, 3.0),
            nearby_resources=[{"name": "apple", "type": "food", "distance": 5.0}],
            nearby_hazards=[],
            inventory=["sword", "shield"],
            goal="Collect resources",
            tick=10,
        )
        assert context.position == (1.0, 2.0, 3.0)
        assert len(context.nearby_resources) == 1
        assert len(context.inventory) == 2
        assert context.goal == "Collect resources"
        assert context.tick == 10

    def test_from_observation(self):
        """Test creating SimpleContext from Observation."""
        obs = Observation(
            agent_id="agent_1",
            tick=25,
            position=(10.0, 0.0, 15.0),
            nearby_resources=[
                ResourceInfo(
                    name="wood",
                    type="material",
                    position=(12.0, 0.0, 16.0),
                    distance=2.2,
                ),
                ResourceInfo(
                    name="stone",
                    type="material",
                    position=(8.0, 0.0, 14.0),
                    distance=2.2,
                ),
            ],
            nearby_hazards=[
                HazardInfo(
                    name="lava",
                    type="environmental",
                    position=(20.0, 0.0, 20.0),
                    distance=7.1,
                    damage=50.0,
                )
            ],
            inventory=[
                ItemInfo(id="item_1", name="pickaxe", quantity=1),
                ItemInfo(id="item_2", name="torch", quantity=5),
            ],
        )
        context = SimpleContext.from_observation(obs, goal="Mine resources")
        assert context.position == (10.0, 0.0, 15.0)
        assert context.tick == 25
        assert len(context.nearby_resources) == 2
        assert context.nearby_resources[0]["name"] == "wood"
        assert context.nearby_resources[0]["distance"] == 2.2
        assert len(context.nearby_hazards) == 1
        assert context.nearby_hazards[0]["damage"] == 50.0
        assert len(context.inventory) == 2
        assert "pickaxe" in context.inventory
        assert "torch" in context.inventory
        assert context.goal == "Mine resources"

    def test_from_observation_empty_fields(self):
        """Test creating SimpleContext from minimal Observation."""
        obs = Observation(
            agent_id="agent_2",
            tick=0,
            position=(0.0, 0.0, 0.0),
        )
        context = SimpleContext.from_observation(obs)
        assert context.position == (0.0, 0.0, 0.0)
        assert context.nearby_resources == []
        assert context.nearby_hazards == []
        assert context.inventory == []
        assert context.goal is None
        assert context.tick == 0
