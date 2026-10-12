from typing import Any, Callable

from src.jev.action_router import ActionRouter
from src.jev.policy import FinancePolicy
from src.jev.qwen_decider import JEVQwenDecider
from src.jev.schemas import JEVRequest
from src.jev.state import StateStore


class JEVLoop:
    def __init__(
        self,
        decider: JEVQwenDecider | None = None,
        policy: FinancePolicy | None = None,
        action_router: ActionRouter | None = None,
    ):
        self.decider = decider or JEVQwenDecider()
        self.policy = policy or FinancePolicy()
        self.action_router = action_router or ActionRouter()

    def run(
        self,
        request: JEVRequest,
        max_steps: int = 5,
        should_continue: Callable[
            [dict[str, Any], dict[str, Any]],
            bool,
        ]
        | None = None,
    ) -> dict[str, Any]:

        if max_steps <= 0:
            raise ValueError("max_steps must be greater than 0")

        state_store = StateStore(request.state)

        history: list[dict[str, Any]] = []

        for step in range(max_steps):
            state = state_store.get()

            # 1. Decision
            response = self.decider.decide(
                JEVRequest(
                    state=state,
                    questions=request.questions,
                )
            )

            # 2. Policy
            action = self.policy.decide(response)

            # 3. Action
            result = self.action_router.execute(action)

            # 4. State transition
            new_state = state_store.update(
                {
                    "last_action": action.action,
                    "last_result": result,
                    "step": step + 1,
                }
            )

            history.append(
                {
                    "step": step + 1,
                    "state": state,
                    "decisions": response.model_dump(),
                    "action": {
                        "name": action.action,
                        "parameters": action.parameters,
                    },
                    "result": result,
                    "new_state": new_state,
                }
            )

            # Default: stop after one completed action.
            if should_continue is None:
                break

            if not should_continue(new_state, result):
                break

        return {
            "steps": len(history),
            "history": history,
            "final_state": state_store.get(),
        }