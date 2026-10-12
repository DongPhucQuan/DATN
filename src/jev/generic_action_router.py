"""Allow-listed action dispatcher for the generic JEV core."""
from copy import deepcopy
from typing import Any, Callable

from src.jev.generic_policy import GenericAction


ActionHandler = Callable[[dict[str, Any]], dict[str, Any]]


class GenericActionRouter:
    """Execute only handlers explicitly registered by the application."""

    def __init__(self, handlers: dict[str, ActionHandler]):
        if not isinstance(handlers, dict):
            raise TypeError("handlers must be a dictionary")
        for name, handler in handlers.items():
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Action names must be non-empty strings")
            if not callable(handler):
                raise TypeError(f"Handler for '{name}' must be callable")
        self.tools = dict(handlers)
        self.allowed_actions = frozenset(self.tools)

    def execute(self, action: GenericAction) -> dict[str, Any]:
        if not isinstance(action, GenericAction):
            raise TypeError("action must be a GenericAction")
        if action.action not in self.allowed_actions:
            raise ValueError(f"Action not allowed: {action.action}")
        handler = self.tools[action.action]
        result = handler(deepcopy(action.parameters))
        if not isinstance(result, dict):
            raise TypeError("Action handler must return a dictionary")
        return deepcopy(result)
