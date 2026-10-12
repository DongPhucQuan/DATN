from typing import Any

from src.jev.chat_policy import ChatAction


class ChatActionRouter:
    ALLOWED_ACTIONS = {
        "normal_response",
        "acknowledge_message",
        "flag_message",
    }

    def __init__(self):
        self.tools = {
            "normal_response": self._normal_response,
            "acknowledge_message": self._acknowledge_message,
            "flag_message": self._flag_message,
        }

    def execute(self, action: ChatAction) -> dict[str, Any]:
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

    def _normal_response(
        self,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "status": "normal",
            "parameters": parameters,
        }

    def _acknowledge_message(
        self,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "status": "important",
            "parameters": parameters,
        }

    def _flag_message(
        self,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "status": "flagged",
            "parameters": parameters,
        }