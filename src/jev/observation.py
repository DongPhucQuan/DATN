
from copy import deepcopy
from typing import Any

from src.jev.world_state import WorldState


class Observation:
    """Creates a restricted view of the world for an agent."""

    @staticmethod
    def observe(
        world: WorldState,
        visible_keys: list[str] | None = None,
    ) -> dict[str, Any]:
        state = world.snapshot()

        if visible_keys is None:
            visible_state = state
        else:
            visible_state = {
                key: state[key]
                for key in visible_keys
                if key in state
            }

        return {
            "world_version": world.version,
            "state": deepcopy(visible_state),
        }
