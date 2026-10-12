
import json

from src.jev.generic_action_router import GenericActionRouter
from src.jev.generic_engine import GenericJEVEngine
from src.jev.generic_policy import GenericPolicy
from src.jev.schemas import JEVQuestion, JEVRequest


def main():
    policy = GenericPolicy(
        rules={
            "priority": (
                "choice",
                "high",
                {
                    "action": "request_review",
                    "parameters": {
                        "reason": "high_priority",
                    },
                },
            ),
        },
        default_action="continue",
        default_parameters={"reason": "no_escalation_rule_matched"},
    )

    router = GenericActionRouter({
        "request_review": lambda params: {
            "status": "review_requested",
            "details": params,
        },
        "acknowledge": lambda params: {
            "status": "acknowledged",
            "details": params,
        },
        "continue": lambda params: {
            "status": "continue",
            "details": params,
        },
    })

    engine = GenericJEVEngine(
        policy=policy,
        action_router=router,
    )

    request = JEVRequest(
        state={
            "task": "review_work_report",
            "report": (
                "The deployment failed twice. "
                "The team has not identified the cause, "
                "and the delivery deadline is tomorrow."
            ),
        },
        questions={
            "priority": JEVQuestion(
                type="choice",
                instructions=(
                    "Classify the urgency of this work report. "
                    "Choose high for an urgent unresolved problem, "
                    "medium for an issue needing attention, "
                    "or low for routine work."
                ),
                criteria=["low", "medium", "high"],
            )
        },
    )

    result = engine.run(request)

    print("\n=== GENERIC JEV DEMO ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
