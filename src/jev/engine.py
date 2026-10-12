from typing import Any

from src.jev.action_router import ActionRouter
from src.jev.policy import FinancePolicy
from src.jev.qwen_decider import JEVQwenDecider
from src.jev.state import StateStore
from src.jev.schemas import JEVRequest


class JEVEngine:
    def __init__(self):
        self.decider = JEVQwenDecider()
        self.policy = FinancePolicy()
        self.action_router = ActionRouter()

    def run(self, request: JEVRequest) -> dict[str, Any]:
        state_store = StateStore(request.state)

        initial_state = state_store.get()

        # 1. AI decision
        response = self.decider.decide(request)

        # 2. Deterministic policy
        action = self.policy.decide(response)

        # 3. Deterministic action execution
        result = self.action_router.execute(action)

        # 4. Deterministic state transition
        final_state = state_store.update(
            {
                "last_action": action.action,
                "last_result": result,
            }
        )

        return {
            "initial_state": initial_state,
            "decisions": response.model_dump(),
            "action": {
                "name": action.action,
                "parameters": action.parameters,
            },
            "result": result,
            "final_state": final_state,
        }