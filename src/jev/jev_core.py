"""Stable public API for the standard, domain-neutral JEV core."""
from copy import deepcopy
from typing import Any, Callable

from src.jev.generic_action_router import GenericActionRouter
from src.jev.generic_engine import GenericJEVEngine
from src.jev.generic_loop import GenericJEVLoop
from src.jev.generic_policy import GenericPolicy
from src.jev.jev_config import JEVConfig
from src.jev.qwen_decider import JEVQwenDecider
from src.jev.schemas import JEVRequest

ContinueCondition = Callable[[dict[str, Any], dict[str, Any]], bool]
NextRequestFactory = Callable[[dict[str, Any], list[dict[str, Any]]], JEVRequest]


class JEVCore:
    """Public facade. Domain behavior belongs in policy and registered handlers."""
    def __init__(self, policy: GenericPolicy, action_router: GenericActionRouter,
                 decider: Any | None = None, config: JEVConfig | None = None):
        self.config = config if config is not None else JEVConfig()
        if not isinstance(self.config, JEVConfig):
            raise TypeError("config must be a JEVConfig")
        # Instantiate the local model client only when caller did not inject a decider.
        resolved_decider = JEVQwenDecider() if decider is None else decider
        self.engine = GenericJEVEngine(policy, action_router, resolved_decider)
        self.loop = GenericJEVLoop(self.engine)

    def run_once(self, request: JEVRequest) -> dict[str, Any]:
        self._validate_request(request)
        cycle = self.engine.run(request)
        history = [{
            "step": 1,
            "decisions": cycle["decisions"],
            "action": cycle["action"],
            "result": cycle["result"],
            "state": cycle["final_state"],
        }]
        return {
            "agent_id": self.config.agent_id,
            "status": "completed",
            "mode": "single",
            "steps": 1,
            "stop_reason": "single_cycle_completed",
            "history": history,
            "last_decisions": deepcopy(cycle["decisions"]),
            "last_action": deepcopy(cycle["action"]),
            "last_result": deepcopy(cycle["result"]),
            "final_state": deepcopy(cycle["final_state"]),
            "metadata": deepcopy(self.config.metadata),
        }

    def run(self, request: JEVRequest, max_steps: int | None = None,
            should_continue: ContinueCondition | None = None,
            next_request: NextRequestFactory | None = None) -> dict[str, Any]:
        """Run up to max_steps. Without a callback, continue to the hard limit."""
        self._validate_request(request)
        limit = self.config.max_steps if max_steps is None else max_steps
        if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
            raise ValueError("max_steps must be a positive integer")
        continuation = should_continue if should_continue is not None else (lambda state, result: True)
        loop_result = self.loop.run(request, max_steps=limit,
                                    should_continue=continuation,
                                    next_request=next_request)
        history = loop_result["history"]
        last = history[-1] if history else None
        return {
            "agent_id": self.config.agent_id,
            "status": "completed",
            "mode": "multi",
            "steps": loop_result["steps"],
            "stop_reason": loop_result["stop_reason"],
            "history": history,
            "last_decisions": deepcopy(last["decisions"]) if last else None,
            "last_action": deepcopy(last["action"]) if last else None,
            "last_result": deepcopy(last["result"]) if last else None,
            "final_state": loop_result["final_state"],
            "metadata": deepcopy(self.config.metadata),
        }

    @staticmethod
    def _validate_request(request: JEVRequest) -> None:
        if not isinstance(request, JEVRequest):
            raise TypeError("request must be a JEVRequest")
