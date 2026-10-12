
import json

from src.jev.generic_action_router import GenericActionRouter
from src.jev.generic_policy import GenericPolicy
from src.jev.jev_config import JEVConfig
from src.jev.jev_core import JEVCore
from src.jev.schemas import JEVQuestion, JEVRequest


def request_review(parameters):
    return {
        "status": "review_requested",
        "reason": "The configured policy matched.",
        "parameters": parameters,
    }


def continue_task(parameters):
    return {
        "status": "continue",
        "parameters": parameters,
    }


def main():
    policy = GenericPolicy(
        rules={
            "priority": (
                "choice",
                "high",
                {
                    "action": "request_review",
                    "parameters": {},
                },
            ),
        },
        default_action="continue_task",
        default_parameters={},
    )

    action_router = GenericActionRouter({
        "request_review": request_review,
        "continue_task": continue_task,
    })

    config = JEVConfig(
        agent_id="jev-prototype",
        max_steps=3,
        metadata={
            "prototype": True,
            "domain": "generic",
        },
    )

    jev = JEVCore(
        policy=policy,
        action_router=action_router,
        config=config,
    )

    request = JEVRequest(
        state={
            "task": "Evaluate the importance of a pending task.",
            "context": "A generic demonstration, not a business workflow.",
        },
        questions={
            "priority": JEVQuestion(
                type="choice",
                instructions=(
                    "Classify the task priority based on the supplied "
                    "state. Choose high, medium, or low."
                ),
                criteria=["low", "medium", "high"],
            ),
        },
    )

    result = jev.run_once(request)

    print("=== JEV CORE PROTOTYPE ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
