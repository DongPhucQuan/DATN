
import pytest

from src.jev.generic_policy import GenericAction
from src.jev.world_state import WorldState
from src.jev.world_engine import WorldEngine


@pytest.fixture
def world():
    return WorldState({
        "position": {"x": 0, "y": 0},
        "energy": 3,
    })


def test_move_changes_position_and_energy(world):
    engine = WorldEngine(world)

    result = engine.execute(
        GenericAction("move", {"direction": "east"})
    )

    assert result["success"] is True
    assert world.get("position") == {"x": 1, "y": 0}
    assert world.get("energy") == 2
    assert world.version == 1


def test_invalid_direction_does_not_change_world(world):
    engine = WorldEngine(world)
    before = world.snapshot()

    result = engine.execute(
        GenericAction("move", {"direction": "up"})
    )

    assert result["success"] is False
    assert world.snapshot() == before
    assert world.version == 0


def test_move_without_energy_is_rejected():
    world = WorldState({
        "position": {"x": 0, "y": 0},
        "energy": 0,
    })
    engine = WorldEngine(world)

    result = engine.execute(
        GenericAction("move", {"direction": "north"})
    )

    assert result["success"] is False
    assert world.get("position") == {"x": 0, "y": 0}
    assert world.version == 0


def test_wait_does_not_change_world(world):
    engine = WorldEngine(world)
    before = world.snapshot()

    result = engine.execute(GenericAction("wait"))

    assert result["success"] is True
    assert world.snapshot() == before
    assert world.version == 0


def test_unknown_action_is_rejected(world):
    engine = WorldEngine(world)

    result = engine.execute(GenericAction("fly"))

    assert result["success"] is False
    assert world.version == 0


def test_invalid_position_is_rejected():
    world = WorldState({
        "position": "unknown",
        "energy": 3,
    })
    engine = WorldEngine(world)

    result = engine.execute(
        GenericAction("move", {"direction": "north"})
    )

    assert result["success"] is False
    assert world.version == 0


def test_wrong_action_type_is_rejected(world):
    engine = WorldEngine(world)

    with pytest.raises(TypeError):
        engine.execute({"action": "wait"})
