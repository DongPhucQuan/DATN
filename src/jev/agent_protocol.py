
from typing import Any

from src.jev.generic_policy import GenericAction


class AgentProtocol:
    """
    Validates agent-proposed actions against an explicit action schema.

    The protocol validates decisions only. WorldEngine remains responsible
    for deciding whether an action is valid in the current world state.
    """

    def __init__(self, action_schemas: dict[str, dict[str, Any]]):
        if not isinstance(action_schemas, dict) or not action_schemas:
            raise ValueError("action_schemas must be a non-empty dictionary")

        self.action_schemas = {}

        for action_name, schema in action_schemas.items():
            if not isinstance(action_name, str) or not action_name.strip():
                raise ValueError("Action names must be non-empty strings")

            if not isinstance(schema, dict):
                raise TypeError(f"Schema for {action_name} must be a dictionary")

            required = schema.get("required", {})
            optional = schema.get("optional", {})

            if not isinstance(required, dict) or not isinstance(optional, dict):
                raise TypeError("required and optional must be dictionaries")

            overlap = set(required) & set(optional)
            if overlap:
                raise ValueError(
                    f"Parameters cannot be both required and optional: {overlap}"
                )

            for parameter_name, rule in {**required, **optional}.items():
                if not isinstance(parameter_name, str) or not parameter_name:
                    raise ValueError("Parameter names must be non-empty strings")

                if not isinstance(rule, dict) or "type" not in rule:
                    raise ValueError(
                        f"Parameter {parameter_name} needs a type declaration"
                    )

                expected_type = rule["type"]
                if not isinstance(expected_type, type):
                    raise TypeError(
                        f"Type declaration for {parameter_name} must be a type"
                    )

                choices = rule.get("choices")
                if choices is not None and not isinstance(choices, (list, tuple, set)):
                    raise TypeError(
                        f"Choices for {parameter_name} must be a collection"
                    )

            self.action_schemas[action_name] = {
                "required": dict(required),
                "optional": dict(optional),
            }

    def validate(self, decision: dict[str, Any]) -> GenericAction:
        """Validate a structured decision and return a safe GenericAction."""
        if not isinstance(decision, dict):
            raise TypeError("Decision must be a dictionary")

        if set(decision) != {"action", "parameters"}:
            raise ValueError(
                "Decision must contain exactly 'action' and 'parameters'"
            )

        action_name = decision["action"]
        parameters = decision["parameters"]

        if not isinstance(action_name, str):
            raise TypeError("Action name must be a string")

        if action_name not in self.action_schemas:
            raise ValueError(f"Action is not allowed: {action_name}")

        if not isinstance(parameters, dict):
            raise TypeError("Action parameters must be a dictionary")

        schema = self.action_schemas[action_name]
        required = schema["required"]
        optional = schema["optional"]

        missing = set(required) - set(parameters)
        if missing:
            raise ValueError(f"Missing required parameters: {sorted(missing)}")

        unexpected = set(parameters) - set(required) - set(optional)
        if unexpected:
            raise ValueError(f"Unexpected parameters: {sorted(unexpected)}")

        for name, value in parameters.items():
            rule = required.get(name, optional.get(name))
            expected_type = rule["type"]

            # bool is a subclass of int in Python, but should not silently
            # pass as an integer parameter.
            if expected_type is int and isinstance(value, bool):
                raise TypeError(f"Parameter '{name}' must be an integer")

            if not isinstance(value, expected_type):
                raise TypeError(
                    f"Parameter '{name}' must have type "
                    f"{expected_type.__name__}"
                )

            choices = rule.get("choices")
            if choices is not None and value not in choices:
                raise ValueError(
                    f"Invalid value for '{name}': {value!r}. "
                    f"Allowed values: {list(choices)}"
                )

        return GenericAction(
            action=action_name,
            parameters=dict(parameters),
        )
