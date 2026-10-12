
import pytest

from src.jev.world_state import WorldState
from src.jev.observation import Observation


def test_snapshot_cannot_mutate_world():
    world = WorldState({"energy": 10})

    snapshot = world.snapshot()
    snapshot["energy"] = 999

    assert world.get("energy") == 10


def test_patch_updates_state_and_version():
    world = WorldState({"energy": 10})

    result = world.apply_patch({"energy": 7})

    assert result["energy"] == 7
    assert world.version == 1


def test_observation_only_exposes_allowed_keys():
    world = WorldState({
        "energy": 10,
        "goal": "explore",
        "secret": "hidden",
    })

    observed = Observation.observe(
        world,
        visible_keys=["energy", "goal"],
    )

    assert observed["state"] == {
        "energy": 10,
        "goal": "explore",
    }
    assert "secret" not in observed["state"]


def test_observation_does_not_mutate_world():
    world = WorldState({"energy": 10})

    observed = Observation.observe(world)
    observed["state"]["energy"] = 0

    assert world.get("energy") == 10


def test_invalid_patch_is_rejected():
    world = WorldState({"energy": 10})

    with pytest.raises(TypeError):
        world.apply_patch(["invalid"])
