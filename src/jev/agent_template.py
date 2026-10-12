"""Copy this file as the starting point for a new domain-specific JEV agent.

Keep business logic in the policy and registered handlers. Avoid editing the
shared generic core for agent-specific behavior.
"""
from __future__ import annotations

import json
from typing import Any

from src.jev import (
    GenericActionRouter,
    GenericPolicy,
    JEVConfig,
    JEVCore,
    JEVQuestion,
    JEVRequest,
)


def continue_task(parameters: dict[str, Any]) -> dict[str, Any]:
    """Example handler; replace with one bounded, explicit business operation."""
    return {"status": "continued", "received_parameters": parameters}


def request_review(parameters: dict[str, Any]) -> dict[str, Any]:
    """Example handler; replace with a review queue or human approval step."""
    return {"status": "review_requested", "received_parameters": parameters}


def build_agent(decider: Any | None = None) -> JEVCore:
    """Build an agent; inject a test/offline decider when no model is desired."""
    policy = GenericPolicy(
        rules={
            "priority": (
                "choice",
                "high",
                {
                    "action": "request_review",
                    "parameters": {"reason": "high_priority"},
                },
            ),
        },
        default_action="continue_task",
        default_parameters={},
    )

    router = GenericActionRouter(
        {
            "continue_task": continue_task,
            "request_review": request_review,
        }
    )

    return JEVCore(
        policy=policy,
        action_router=router,
        decider=decider,
        config=JEVConfig(
            agent_id="replace-with-agent-id",
            max_steps=3,
            metadata={"template_version": "1.0"},
        ),
    )


def build_request() -> JEVRequest:
    """Replace state and questions with this agent's domain contract."""
    return JEVRequest(
        state={"task": "replace-with-task", "context": {}},
        questions={
            "priority": JEVQuestion(
                type="choice",
                instructions="Classify priority using only the supplied state.",
                criteria=["low", "medium", "high"],
            ),
        },
    )


def main() -> None:
    # The default decider uses the local Qwen/llama.cpp server.
    core = build_agent()
    result = core.run_once(build_request())
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
