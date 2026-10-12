from typing import Any

from src.jev.policy import PolicyAction


class ActionRouter:
    """
    Deterministic action execution layer.

    AI never calls tools directly.
    """

    ALLOWED_ACTIONS = {
        "review_invoice",
        "accept_invoice",
    }

    def __init__(self):
        self.tools = {
            "review_invoice": self._review_invoice,
            "accept_invoice": self._accept_invoice,
        }

    def execute(self, action: PolicyAction) -> dict[str, Any]:
        if action.action not in self.ALLOWED_ACTIONS:
            raise ValueError(
                f"Action not allowed: {action.action}"
            )

        handler = self.tools.get(action.action)

        if handler is None:
            raise ValueError(
                f"Action handler not registered: {action.action}"
            )

        return handler(action.parameters)

    def _review_invoice(
        self,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "status": "review_required",
            "parameters": parameters,
        }

    def _accept_invoice(
        self,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "status": "accepted",
            "parameters": parameters,
        }