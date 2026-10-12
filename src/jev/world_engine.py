
from typing import Any

from src.jev.generic_policy import GenericAction
from src.jev.world_state import WorldState


class WorldEngine:
    """Validates actions and applies deterministic world rules."""

    def __init__(self, world: WorldState):
        self.world = world

    def execute(self, action: GenericAction) -> dict[str, Any]:
        if not isinstance(action, GenericAction):
            raise TypeError("action must be a GenericAction")

        state = self.world.snapshot()
        action_name = action.action
        params = action.parameters

        if action_name == "wait":
            return {
                "success": True,
                "action": action_name,
                "message": "Agent waited.",
                "world_version": self.world.version,
                "state": state,
            }

        if action_name == "move":
            direction = params.get("direction")
            allowed_directions = {"north", "south", "east", "west"}

            if direction not in allowed_directions:
                return self._rejected(
                    action_name,
                    "Invalid direction.",
                )

            energy = state.get("energy", 0)
            if not isinstance(energy, (int, float)) or isinstance(energy, bool):
                return self._rejected(
                    action_name,
                    "World energy must be numeric.",
                )

            if energy < 1:
                return self._rejected(
                    action_name,
                    "Not enough energy to move.",
                )

            position = state.get("position")
            if (
                not isinstance(position, dict)
                or not isinstance(position.get("x"), int)
                or not isinstance(position.get("y"), int)
            ):
                return self._rejected(
                    action_name,
                    "World position is invalid.",
                )

            dx, dy = {
                "north": (0, 1),
                "south": (0, -1),
                "east": (1, 0),
                "west": (-1, 0),
            }[direction]

            new_position = {
                "x": position["x"] + dx,
                "y": position["y"] + dy,
            }

            updated = self.world.apply_patch({
                "position": new_position,
                "energy": energy - 1,
            })

            return {
                "success": True,
                "action": action_name,
                "message": "Agent moved.",
                "world_version": self.world.version,
                "state": updated,
            }

        return self._rejected(
            action_name,
            "Action is not supported by this world.",
        )

    def _rejected(
        self,
        action_name: str,
        reason: str,
    ) -> dict[str, Any]:
        return {
            "success": False,
            "action": action_name,
            "message": reason,
            "world_version": self.world.version,
            "state": self.world.snapshot(),
        }
