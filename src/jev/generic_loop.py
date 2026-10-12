"""Bounded multi-step runner around GenericJEVEngine."""
from copy import deepcopy
from typing import Any, Callable

from src.jev.generic_engine import GenericJEVEngine
from src.jev.schemas import JEVRequest
from src.jev.state import StateStore

ContinueCondition = Callable[[dict[str, Any], dict[str, Any]], bool]
NextRequestFactory = Callable[[dict[str, Any], list[dict[str, Any]]], JEVRequest]


class GenericJEVLoop:
    """Run a bounded sequence of cycles with explicit continuation semantics.

    With no ``should_continue`` callback, exactly one cycle runs. The public
    ``JEVCore.run`` API may deliberately supply an always-continue callback.
    """
    def __init__(self, engine: GenericJEVEngine):
        if not isinstance(engine, GenericJEVEngine):
            raise TypeError("engine must be a GenericJEVEngine")
        self.engine = engine

    def run(self, request: JEVRequest, max_steps: int = 5,
            should_continue: ContinueCondition | None = None,
            next_request: NextRequestFactory | None = None) -> dict[str, Any]:
        if not isinstance(request, JEVRequest):
            raise TypeError("request must be a JEVRequest")
        if not isinstance(max_steps, int) or isinstance(max_steps, bool) or max_steps <= 0:
            raise ValueError("max_steps must be a positive integer")
        if should_continue is not None and not callable(should_continue):
            raise TypeError("should_continue must be callable or None")
        if next_request is not None and not callable(next_request):
            raise TypeError("next_request must be callable or None")

        state_store = StateStore(request.state)
        history: list[dict[str, Any]] = []
        stop_reason = "max_steps_reached"

        for step in range(1, max_steps + 1):
            current_state = state_store.get()
            if step == 1 or next_request is None:
                current_request = JEVRequest(state=current_state, questions=request.questions)
            else:
                proposed = next_request(current_state, deepcopy(history))
                if not isinstance(proposed, JEVRequest):
                    raise TypeError("next_request must return a JEVRequest")
                # The loop owns state continuity; callback supplies only new questions.
                current_request = JEVRequest(state=current_state, questions=proposed.questions)

            step_result = self.engine.run(current_request)
            state_store.update(step_result["final_state"])
            new_state = state_store.update({"step": step})
            history.append({
                "step": step,
                "decisions": step_result["decisions"],
                "action": step_result["action"],
                "result": step_result["result"],
                "state": new_state,
            })

            if should_continue is None:
                stop_reason = "single_cycle_completed"
                break
            if not should_continue(deepcopy(new_state), deepcopy(step_result["result"])):
                stop_reason = "continuation_condition_met"
                break

        return {
            "steps": len(history),
            "history": history,
            "final_state": state_store.get(),
            "stop_reason": stop_reason,
        }
