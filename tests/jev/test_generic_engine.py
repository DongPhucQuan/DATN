
from src.jev.generic_action_router import GenericActionRouter
from src.jev.generic_engine import GenericJEVEngine
from src.jev.generic_policy import GenericPolicy
from src.jev.schemas import JEVAnswer, JEVQuestion, JEVRequest, JEVResponse


class FakeDecider:
    def decide(self, request):
        return JEVResponse(
            answers={
                "priority": JEVAnswer(
                    type="choice",
                    choice="high",
                )
            }
        )


def test_generic_engine_runs_complete_pipeline():
    policy = GenericPolicy(
        rules={
            "priority": (
                "choice",
                "high",
                {
                    "action": "request_review",
                    "parameters": {"reason": "high_priority"},
                },
            )
        },
        default_action="continue",
    )

    router = GenericActionRouter({
        "request_review": lambda params: {
            "status": "review_requested",
            "details": params,
        },
        "continue": lambda params: {
            "status": "continued",
            "details": params,
        },
    })

    engine = GenericJEVEngine(
        policy=policy,
        action_router=router,
        decider=FakeDecider(),
    )

    request = JEVRequest(
        state={"task": "check_report"},
        questions={
            "priority": JEVQuestion(
                type="choice",
                instructions="Classify the task priority.",
                criteria=["low", "medium", "high"],
            )
        },
    )

    result = engine.run(request)

    assert result["initial_state"]["task"] == "check_report"
    assert result["decisions"]["answers"]["priority"]["choice"] == "high"
    assert result["action"]["name"] == "request_review"
    assert result["result"]["status"] == "review_requested"
    assert result["final_state"]["last_action"] == "request_review"
    assert result["final_state"]["last_result"]["status"] == "review_requested"
