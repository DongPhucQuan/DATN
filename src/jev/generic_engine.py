"""One deterministic JEV decision/action cycle."""
from copy import deepcopy
from typing import Any

from src.jev.generic_action_router import GenericActionRouter
from src.jev.generic_policy import GenericAction, GenericPolicy
from src.jev.qwen_decider import JEVQwenDecider
from src.jev.schemas import JEVRequest, JEVResponse
from src.jev.state import StateStore


class GenericJEVEngine:
    """Coordinate decider -> deterministic policy -> allow-listed router -> state."""

    def __init__(self, policy: GenericPolicy, action_router: GenericActionRouter,
                 decider: Any | None = None):
        if not isinstance(policy, GenericPolicy):
            raise TypeError("policy must be a GenericPolicy")
        if not isinstance(action_router, GenericActionRouter):
            raise TypeError("action_router must be a GenericActionRouter")
        resolved_decider = JEVQwenDecider() if decider is None else decider
        if not callable(getattr(resolved_decider, "decide", None)):
            raise TypeError("decider must provide a callable decide(request) method")
        self.decider = resolved_decider
        self.policy = policy
        self.action_router = action_router

        configured_actions = {policy.default_action}
        configured_actions.update(
            config[2]["action"] for config in policy.rules.values()
        )
        unknown_actions = configured_actions - action_router.allowed_actions
        if unknown_actions:
            raise ValueError(
                "Policy references actions that are not registered in the router: "
                f"{sorted(unknown_actions)}"
            )

    def run(self, request: JEVRequest) -> dict[str, Any]:
        if not isinstance(request, JEVRequest):
            raise TypeError("request must be a JEVRequest")
        state_store = StateStore(request.state)
        initial_state = state_store.get()
        response = self.decider.decide(request)
        if not isinstance(response, JEVResponse):
            raise TypeError("decider.decide(request) must return a JEVResponse")
        action = self.policy.decide(response)
        if not isinstance(action, GenericAction):
            raise TypeError("policy.decide(response) must return a GenericAction")
        result = self.action_router.execute(action)
        final_state = state_store.update({
            "last_action": action.action,
            "last_result": result,
        })
        return {
            "initial_state": initial_state,
            "decisions": response.model_dump(),
            "action": {"name": action.action, "parameters": deepcopy(action.parameters)},
            "result": result,
            "final_state": final_state,
        }
