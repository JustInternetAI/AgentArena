"""
Tests for crafting system tools and schemas.
"""

from agent_runtime.schemas import Observation, StationInfo
from tools.inventory import craft_item, get_recipes


class TestCraftItemTool:
    """Tests for the craft_item Python tool."""

    def test_craft_item_returns_success(self):
        """Test craft_item tool returns expected format."""
        result = craft_item("torch")
        assert result["success"] is True
        assert result["item"] == "torch"

    def test_craft_item_with_different_recipes(self):
        """Test craft_item with various recipe names."""
        for recipe in ["torch", "shelter", "meal"]:
            result = craft_item(recipe)
            assert result["success"] is True
            assert result["item"] == recipe


class TestGetRecipesTool:
    """Tests for the get_recipes Python tool."""

    def test_get_recipes_returns_success(self):
        """Test get_recipes returns expected format."""
        result = get_recipes()
        assert result["success"] is True
        assert "recipes" in result


class TestStationInfoInObservation:
    """Tests for StationInfo integration with Observation."""

    def test_observation_with_stations_roundtrip(self):
        """Test full roundtrip of observation with station data."""
        obs = Observation(
            agent_id="test_agent",
            tick=5,
            position=(0.0, 1.0, 0.0),
            nearby_stations=[
                StationInfo(
                    name="Workbench",
                    type="workbench",
                    position=(12.0, 0.0, 10.0),
                    distance=15.6,
                ),
                StationInfo(
                    name="Anvil",
                    type="anvil",
                    position=(-10.0, 0.0, -8.0),
                    distance=12.8,
                ),
            ],
        )

        data = obs.to_dict()
        restored = Observation.from_dict(data)

        assert len(restored.nearby_stations) == 2
        assert restored.nearby_stations[0].name == "Workbench"
        assert restored.nearby_stations[0].type == "workbench"
        assert restored.nearby_stations[0].distance == 15.6
        assert restored.nearby_stations[1].name == "Anvil"
        assert restored.nearby_stations[1].type == "anvil"

    def test_empty_stations_default(self):
        """Test that nearby_stations defaults to empty list."""
        obs = Observation(
            agent_id="test",
            tick=0,
            position=(0.0, 0.0, 0.0),
        )
        assert obs.nearby_stations == []
