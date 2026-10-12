
from copy import deepcopy
from typing import Any


class WorldState:
    """Holds the authoritative state of a simulated world."""

    def __init__(self, initial_state: dict[str, Any]):
        if not isinstance(initial_state, dict):
            raise TypeError("initial_state must be a dictionary")

        self._data = deepcopy(initial_state)
        self._version = 0

    @property
    def version(self) -> int:
        return self._version

    def snapshot(self) -> dict[str, Any]:
        """Return a copy so callers cannot mutate the real state."""
        return deepcopy(self._data)

    def get(self, key: str, default: Any = None) -> Any:
        return deepcopy(self._data.get(key, default))

    def apply_patch(self, patch: dict[str, Any]) -> dict[str, Any]:
        """Apply explicit top-level state changes."""
        if not isinstance(patch, dict):
            raise TypeError("patch must be a dictionary")

        self._data.update(deepcopy(patch))
        self._version += 1
        return self.snapshot()
