"""Deterministic mapping from typed model answers to approved actions."""
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, ClassVar

from src.jev.schemas import JEVResponse


@dataclass
class GenericAction:
    action: str
    parameters: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.action, str) or not self.action.strip():
            raise ValueError("action must be a non-empty string")
        if not isinstance(self.parameters, dict):
            raise TypeError("parameters must be a dictionary")
        self.parameters = deepcopy(self.parameters)


@dataclass
class GenericPolicy:
    """Map answer values to actions; never execute actions or trust model tool calls.

    Each rule is ``question_name: (answer_field, expected_value, action_config)``.
    ``action_config`` contains ``action`` and optional ``parameters``.
    """
    rules: dict[str, tuple[str, Any, dict[str, Any]]] = field(default_factory=dict)
    default_action: str = "continue"
    default_parameters: dict[str, Any] = field(default_factory=dict)

    _ALLOWED_FIELDS: ClassVar[frozenset[str]] = frozenset({"choice", "score", "noul"})

    def __post_init__(self) -> None:
        if not isinstance(self.rules, dict):
            raise TypeError("rules must be a dictionary")
        if not isinstance(self.default_action, str) or not self.default_action.strip():
            raise ValueError("default_action must be a non-empty string")
        if not isinstance(self.default_parameters, dict):
            raise TypeError("default_parameters must be a dictionary")
        normalized = {}
        for question_name, rule in self.rules.items():
            if not isinstance(question_name, str) or not question_name.strip():
                raise ValueError("Rule question names must be non-empty strings")
            if not isinstance(rule, (tuple, list)) or len(rule) != 3:
                raise ValueError(f"Rule for '{question_name}' must contain 3 items")
            field_name, expected_value, action_config = rule
            if field_name not in self._ALLOWED_FIELDS:
                raise ValueError(
                    f"Unsupported answer field '{field_name}' for '{question_name}'"
                )
            if not isinstance(action_config, dict):
                raise TypeError(f"Action config for '{question_name}' must be a dictionary")
            if set(action_config) - {"action", "parameters"}:
                raise ValueError(
                    f"Unexpected action config keys for '{question_name}': "
                    f"{sorted(set(action_config) - {'action', 'parameters'})}"
                )
            action_name = action_config.get("action")
            params = action_config.get("parameters", {})
            if not isinstance(action_name, str) or not action_name.strip():
                raise ValueError(f"Action config for '{question_name}' needs a non-empty action")
            if not isinstance(params, dict):
                raise TypeError(f"Action parameters for '{question_name}' must be a dictionary")
            normalized[question_name] = (
                field_name,
                deepcopy(expected_value),
                {"action": action_name, "parameters": deepcopy(params)},
            )
        self.rules = normalized
        self.default_parameters = deepcopy(self.default_parameters)

    def decide(self, response: JEVResponse) -> GenericAction:
        if not isinstance(response, JEVResponse):
            raise TypeError("response must be a JEVResponse")
        for question_name, (field_name, expected_value, action_config) in self.rules.items():
            answer = response.answers.get(question_name)
            if answer is None:
                continue
            actual_value = getattr(answer, field_name, None)
            if actual_value is not None and actual_value == expected_value:
                return GenericAction(
                    action=action_config["action"],
                    parameters=deepcopy(action_config.get("parameters", {})),
                )
        return GenericAction(
            action=self.default_action,
            parameters=deepcopy(self.default_parameters),
        )
