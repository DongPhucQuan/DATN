"""Safe, copy-on-read/write state container for the generic JEV core."""
from copy import deepcopy
from typing import Any


class StateStore:
    """Deterministic state container; model output never mutates state directly."""

    def __init__(self, initial_state: dict[str, Any] | None = None):
        if initial_state is None:
            initial_state = {}
        if not isinstance(initial_state, dict):
            raise TypeError("initial_state must be a dictionary")
        self._state = deepcopy(initial_state)

    def get(self) -> dict[str, Any]:
        return deepcopy(self._state)

    def update(self, changes: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(changes, dict):
            raise TypeError("changes must be a dictionary")
        self._state.update(deepcopy(changes))
        return self.get()
