"""
Testing utilities for Agent Arena SDK.

Provides mock observations, shorthand factories, and a lightweight MockArena
so developers can test their ``decide()`` logic with pure ``pytest`` — no
Godot, no GPU, no model files required.

Quick start::

    from agent_arena_sdk.testing import mock_observation, MockArena

    obs = mock_observation(
        nearby_resources=[{"name": "berry_001", "type": "berry",
                           "position": (5, 0, 3), "distance": 4.2}],
        health=80.0,
    )
    decision = my_agent.decide(obs)
    assert decision.tool == "move_to"
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

from .schemas import (
    Decision,
    EntityInfo,
    ExplorationInfo,
    ExploreTarget,
    HazardInfo,
    ItemInfo,
    Observation,
    ResourceInfo,
    StationInfo,
)

# ---------------------------------------------------------------------------
#  Module-level counters for auto-generated IDs
# ---------------------------------------------------------------------------

_resource_counter: int = 0
_hazard_counter: int = 0
_item_counter: int = 0
_station_counter: int = 0
_obs_counter: int = 0


def _next_id(prefix: str, counter_name: str) -> tuple[str, int]:
    """Increment a module-level counter and return ``prefix_NNN``."""
    g = globals()
    g[counter_name] += 1
    return f"{prefix}_{g[counter_name]:03d}", g[counter_name]


# ---------------------------------------------------------------------------
#  Shorthand factories
# ---------------------------------------------------------------------------


def mock_resource(
    name_or_type: str = "berry",
    *,
    name: str | None = None,
    type: str | None = None,
    position: tuple[float, float, float] = (5.0, 0.0, 3.0),
    distance: float = 4.2,
) -> ResourceInfo:
    """Create a :class:`ResourceInfo` with sensible defaults.

    The first positional argument is interpreted as the *type* (e.g.
    ``"berry"``).  A unique *name* is auto-generated from the type unless
    explicitly provided.

    Both typed objects and keyword overrides are supported::

        r = mock_resource("berry", position=(5, 0, 3), distance=4.2)
        r = mock_resource(name="berry_001", type="berry")
    """
    rtype = type or name_or_type
    if name is None:
        auto_name, _ = _next_id(rtype, "_resource_counter")
        name = auto_name
    return ResourceInfo(name=name, type=rtype, position=position, distance=distance)


def mock_hazard(
    name_or_type: str = "fire",
    *,
    name: str | None = None,
    type: str | None = None,
    position: tuple[float, float, float] = (2.0, 0.0, 1.0),
    distance: float = 1.5,
    damage: float = 5.0,
) -> HazardInfo:
    """Create a :class:`HazardInfo` with sensible defaults."""
    htype = type or name_or_type
    if name is None:
        auto_name, _ = _next_id(htype, "_hazard_counter")
        name = auto_name
    return HazardInfo(name=name, type=htype, position=position, distance=distance, damage=damage)


def mock_item(
    name: str = "wood",
    *,
    id: str | None = None,
    quantity: int = 1,
) -> ItemInfo:
    """Create an :class:`ItemInfo` with sensible defaults."""
    if id is None:
        auto_id, _ = _next_id(name, "_item_counter")
        id = auto_id
    return ItemInfo(id=id, name=name, quantity=quantity)


def mock_station(
    name_or_type: str = "workbench",
    *,
    name: str | None = None,
    type: str | None = None,
    position: tuple[float, float, float] = (0.0, 0.0, 0.0),
    distance: float = 3.0,
) -> StationInfo:
    """Create a :class:`StationInfo` with sensible defaults."""
    stype = type or name_or_type
    if name is None:
        auto_name, _ = _next_id(stype, "_station_counter")
        name = auto_name
    return StationInfo(name=name, type=stype, position=position, distance=distance)


# ---------------------------------------------------------------------------
#  Auto-conversion helpers (dict → typed dataclass)
# ---------------------------------------------------------------------------


def _coerce_resource(item: Any) -> ResourceInfo:
    if isinstance(item, ResourceInfo):
        return item
    if isinstance(item, dict):
        pos = item.get("position", (0.0, 0.0, 0.0))
        if isinstance(pos, list):
            pos = tuple(pos)
        return ResourceInfo(
            name=item.get("name", "resource"),
            type=item.get("type", "unknown"),
            position=pos,
            distance=item.get("distance", 0.0),
        )
    raise TypeError(f"Expected ResourceInfo or dict, got {type(item)}")


def _coerce_hazard(item: Any) -> HazardInfo:
    if isinstance(item, HazardInfo):
        return item
    if isinstance(item, dict):
        pos = item.get("position", (0.0, 0.0, 0.0))
        if isinstance(pos, list):
            pos = tuple(pos)
        return HazardInfo(
            name=item.get("name", "hazard"),
            type=item.get("type", "unknown"),
            position=pos,
            distance=item.get("distance", 0.0),
            damage=item.get("damage", 0.0),
        )
    raise TypeError(f"Expected HazardInfo or dict, got {type(item)}")


def _coerce_item(item: Any) -> ItemInfo:
    if isinstance(item, ItemInfo):
        return item
    if isinstance(item, dict):
        return ItemInfo(
            id=item.get("id", item.get("name", "item")),
            name=item.get("name", "item"),
            quantity=item.get("quantity", 1),
        )
    raise TypeError(f"Expected ItemInfo or dict, got {type(item)}")


def _coerce_station(item: Any) -> StationInfo:
    if isinstance(item, StationInfo):
        return item
    if isinstance(item, dict):
        pos = item.get("position", (0.0, 0.0, 0.0))
        if isinstance(pos, list):
            pos = tuple(pos)
        return StationInfo(
            name=item.get("name", "station"),
            type=item.get("type", "unknown"),
            position=pos,
            distance=item.get("distance", 0.0),
        )
    raise TypeError(f"Expected StationInfo or dict, got {type(item)}")


def _coerce_inventory(
    inventory: Sequence[ItemInfo | dict] | dict[str, int] | None,
) -> list[ItemInfo]:
    """Convert inventory from various formats to ``list[ItemInfo]``.

    Accepts:
    - ``None`` → ``[]``
    - ``list[ItemInfo]`` → pass-through
    - ``list[dict]`` → auto-convert each dict
    - ``dict[str, int]`` (shorthand) → expand ``{"wood": 2}`` to
      ``[ItemInfo(id="wood_0", name="wood", quantity=2)]``
    """
    if inventory is None:
        return []
    if isinstance(inventory, dict):
        items: list[ItemInfo] = []
        for name, qty in inventory.items():
            items.append(ItemInfo(id=f"{name}_0", name=name, quantity=qty))
        return items
    return [_coerce_item(i) for i in inventory]


# ---------------------------------------------------------------------------
#  mock_observation()
# ---------------------------------------------------------------------------


def mock_observation(
    *,
    agent_id: str | None = None,
    tick: int | None = None,
    position: tuple[float, float, float] = (0.0, 0.0, 0.0),
    health: float = 100.0,
    energy: float = 100.0,
    nearby_resources: Sequence[ResourceInfo | dict] | None = None,
    nearby_hazards: Sequence[HazardInfo | dict] | None = None,
    inventory: Sequence[ItemInfo | dict] | dict[str, int] | None = None,
    nearby_stations: Sequence[StationInfo | dict] | None = None,
    exploration: ExplorationInfo | None = None,
    scenario_name: str = "",
    objective: Any | None = None,
    current_progress: dict[str, float] | None = None,
    **kwargs: Any,
) -> Observation:
    """Create a mock :class:`Observation` for testing.

    Accepts **both** typed SDK dataclasses (passed through as-is) and plain
    dicts (auto-converted).  Fields not provided receive sensible defaults.

    ``agent_id`` and ``tick`` are auto-generated sequentially when omitted.

    Extra keyword arguments are forwarded to :class:`Observation` (e.g.
    ``rotation``, ``velocity``, ``custom``, ``last_tool_result``).
    """
    global _obs_counter
    _obs_counter += 1

    if agent_id is None:
        agent_id = f"test_agent_{_obs_counter:03d}"
    if tick is None:
        tick = _obs_counter

    return Observation(
        agent_id=agent_id,
        tick=tick,
        position=position,
        health=health,
        energy=energy,
        nearby_resources=[_coerce_resource(r) for r in (nearby_resources or [])],
        nearby_hazards=[_coerce_hazard(h) for h in (nearby_hazards or [])],
        inventory=_coerce_inventory(inventory),
        nearby_stations=[_coerce_station(s) for s in (nearby_stations or [])],
        exploration=exploration,
        scenario_name=scenario_name,
        objective=objective,
        current_progress=current_progress or {},
        **kwargs,
    )


# ---------------------------------------------------------------------------
#  Utility functions
# ---------------------------------------------------------------------------


def distance_between(
    pos1: tuple[float, float, float] | Sequence[float],
    pos2: tuple[float, float, float] | Sequence[float],
) -> float:
    """Euclidean distance between two 3-D positions."""
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(pos1, pos2)))


def assert_valid_decision(
    decision: Decision,
    valid_tools: Sequence[str] = ("move_to", "collect", "idle", "craft_item"),
) -> None:
    """Assert that *decision* is a well-formed :class:`Decision`."""
    assert isinstance(decision, Decision), f"Expected Decision, got {type(decision)}"
    assert decision.tool in valid_tools, (
        f"Invalid tool '{decision.tool}', expected one of {valid_tools}"
    )
    assert isinstance(decision.params, dict), "Decision.params must be a dict"


# ---------------------------------------------------------------------------
#  MockArena — lightweight multi-tick simulation
# ---------------------------------------------------------------------------


@dataclass
class MockArenaResults:
    """Results returned by :meth:`MockArena.run`."""

    resources_collected: int = 0
    damage_taken: float = 0.0
    final_health: float = 100.0
    decisions: list[Decision] = field(default_factory=list)
    ticks_survived: int = 0
    final_position: tuple[float, float, float] = (0.0, 0.0, 0.0)


@dataclass
class _Resource:
    name: str
    type: str
    position: tuple[float, float, float]


@dataclass
class _Hazard:
    name: str
    type: str
    position: tuple[float, float, float]
    damage: float


class MockArena:
    """Lightweight arena for testing agent logic without Godot.

    Simulates straight-line movement, auto-collection within a pickup radius,
    and hazard damage within a damage radius.  No collision or pathfinding.

    Example::

        arena = MockArena()
        arena.add_resource("berry", position=(5, 0, 3))
        arena.add_hazard("fire", position=(3, 0, 2), damage=5.0)
        results = arena.run(my_agent.decide, ticks=100)
        print(results.resources_collected)
    """

    def __init__(
        self,
        *,
        speed: float = 1.0,
        pickup_radius: float = 1.5,
        hazard_radius: float = 3.0,
        starting_health: float = 100.0,
        starting_energy: float = 100.0,
        starting_position: tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> None:
        self.speed = speed
        self.pickup_radius = pickup_radius
        self.hazard_radius = hazard_radius
        self.starting_health = starting_health
        self.starting_energy = starting_energy
        self.starting_position = starting_position

        self._resources: list[_Resource] = []
        self._hazards: list[_Hazard] = []

        # Runtime state (set on reset)
        self._position: tuple[float, float, float] = starting_position
        self._health: float = starting_health
        self._energy: float = starting_energy
        self._tick: int = 0
        self._collected: int = 0
        self._damage_taken: float = 0.0
        self._live_resources: list[_Resource] = []
        self._decisions: list[Decision] = []

    # -- World setup --------------------------------------------------------

    def add_resource(
        self,
        type: str = "berry",
        *,
        name: str | None = None,
        position: tuple[float, float, float] = (5.0, 0.0, 3.0),
    ) -> None:
        """Add a collectible resource to the arena."""
        if name is None:
            name = f"{type}_{len(self._resources) + 1:03d}"
        self._resources.append(_Resource(name=name, type=type, position=position))

    def add_hazard(
        self,
        type: str = "fire",
        *,
        name: str | None = None,
        position: tuple[float, float, float] = (3.0, 0.0, 2.0),
        damage: float = 5.0,
    ) -> None:
        """Add a hazard to the arena."""
        if name is None:
            name = f"{type}_{len(self._hazards) + 1:03d}"
        self._hazards.append(_Hazard(name=name, type=type, position=position, damage=damage))

    # -- Simulation ---------------------------------------------------------

    def reset(self) -> Observation:
        """Reset the arena to its initial state and return the first observation."""
        self._position = self.starting_position
        self._health = self.starting_health
        self._energy = self.starting_energy
        self._tick = 0
        self._collected = 0
        self._damage_taken = 0.0
        self._live_resources = list(self._resources)  # shallow copy
        self._decisions = []
        return self._build_observation()

    def step(self, decision: Decision) -> Observation:
        """Apply *decision*, advance one tick, and return the new observation."""
        self._decisions.append(decision)
        self._tick += 1

        # 1. Movement
        if decision.tool == "move_to":
            target = decision.params.get("target_position")
            if target and len(target) >= 3:
                self._move_toward(tuple(target[:3]))

        # 2. Hazard damage
        for hazard in self._hazards:
            dist = distance_between(self._position, hazard.position)
            if dist <= self.hazard_radius:
                self._health -= hazard.damage
                self._damage_taken += hazard.damage

        # 3. Auto-collection
        remaining: list[_Resource] = []
        for res in self._live_resources:
            dist = distance_between(self._position, res.position)
            if dist <= self.pickup_radius:
                self._collected += 1
            else:
                remaining.append(res)
        self._live_resources = remaining

        # 4. Clamp health
        self._health = max(0.0, self._health)

        return self._build_observation()

    def run(
        self,
        decide_fn: Callable[[Observation], Decision],
        *,
        ticks: int = 100,
    ) -> MockArenaResults:
        """Run *decide_fn* for up to *ticks* ticks, returning aggregated results."""
        obs = self.reset()
        for _ in range(ticks):
            decision = decide_fn(obs)
            obs = self.step(decision)
            if self._health <= 0:
                break

        return MockArenaResults(
            resources_collected=self._collected,
            damage_taken=self._damage_taken,
            final_health=self._health,
            decisions=list(self._decisions),
            ticks_survived=self._tick,
            final_position=self._position,
        )

    # -- Internal helpers ---------------------------------------------------

    def _move_toward(self, target: tuple[float, float, float]) -> None:
        dx = target[0] - self._position[0]
        dy = target[1] - self._position[1]
        dz = target[2] - self._position[2]
        dist = math.sqrt(dx * dx + dy * dy + dz * dz)
        if dist <= self.speed:
            self._position = target
        elif dist > 0:
            ratio = self.speed / dist
            self._position = (
                self._position[0] + dx * ratio,
                self._position[1] + dy * ratio,
                self._position[2] + dz * ratio,
            )

    def _build_observation(self) -> Observation:
        nearby_resources = [
            ResourceInfo(
                name=r.name,
                type=r.type,
                position=r.position,
                distance=distance_between(self._position, r.position),
            )
            for r in self._live_resources
        ]
        nearby_hazards = [
            HazardInfo(
                name=h.name,
                type=h.type,
                position=h.position,
                distance=distance_between(self._position, h.position),
                damage=h.damage,
            )
            for h in self._hazards
        ]
        return Observation(
            agent_id="mock_agent",
            tick=self._tick,
            position=self._position,
            health=self._health,
            energy=self._energy,
            nearby_resources=nearby_resources,
            nearby_hazards=nearby_hazards,
            inventory=[],
        )


# ---------------------------------------------------------------------------
#  Public API
# ---------------------------------------------------------------------------

__all__ = [
    "mock_observation",
    "mock_resource",
    "mock_hazard",
    "mock_item",
    "mock_station",
    "MockArena",
    "MockArenaResults",
    "assert_valid_decision",
    "distance_between",
]
