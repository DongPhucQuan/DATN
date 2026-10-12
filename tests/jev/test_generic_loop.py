
import pytest

from src.jev.generic_action_router import GenericActionRouter
from src.jev.generic_engine import GenericJEVEngine
from src.jev.generic_loop import GenericJEVLoop
from src.jev.generic_policy import GenericPolicy
from src.jev.schemas import (
    JEVAnswer,
    JEVQuestion,
    JEVRequest,
    JEVResponse,
)


class FakeDecider:
    def decide(self, request):
        priority_question = request.questions.get("priority")

        choice = "high"
        if priority_question and "low" in priority_question.instructions:
            choice = "low"

        return JEVResponse(
            answers={
                "priority": JEVAnswer(
                    type="choice",
                    choice=choice,
                )
            }
        )


def build_loop():
    policy = GenericPolicy(
        rules={
            "priority": (
                "choice",
                "high",
                {"action": "review"},
            )
        },
        default_action="continue",
    )

    router = GenericActionRouter({
        "review": lambda params: {"status": "review"},
        "continue": lambda params: {"status": "continued"},
    })

    engine = GenericJEVEngine(
        policy=policy,
        action_router=router,
        decider=FakeDecider(),
    )

    return GenericJEVLoop(engine)


def make_request():
    return JEVRequest(
        state={"task": "check_report"},
        questions={
            "priority": JEVQuestion(
                type="choice",
                instructions="Classify the priority.",
                criteria=["low", "medium", "high"],
            )
        },
    )


def test_generic_loop_runs_one_step_by_default():
    result = build_loop().run(make_request())

    assert result["steps"] == 1
    assert len(result["history"]) == 1
    assert result["final_state"]["step"] == 1


def test_generic_loop_respects_max_steps():
    result = build_loop().run(
        make_request(),
        max_steps=3,
        should_continue=lambda state, action_result: True,
    )

    assert result["steps"] == 3
    assert result["final_state"]["step"] == 3


def test_generic_loop_stops_when_condition_is_false():
    result = build_loop().run(
        make_request(),
        max_steps=5,
        should_continue=lambda state, action_result: False,
    )

    assert result["steps"] == 1


def test_generic_loop_can_build_next_request():
    loop = build_loop()

    def next_request(state, history):
        assert len(history) == 1
        return JEVRequest(
            state=state,
            questions={
                "priority": JEVQuestion(
                    type="choice",
                    instructions="Classify low priority.",
                    criteria=["low", "medium", "high"],
                )
            },
        )

    result = loop.run(
        make_request(),
        max_steps=2,
        should_continue=lambda state, action_result: state["step"] < 2,
        next_request=next_request,
    )

    assert result["steps"] == 2
    assert result["history"][0]["action"]["name"] == "review"
    assert result["history"][1]["action"]["name"] == "continue"


def test_generic_loop_rejects_invalid_max_steps():
    with pytest.raises(ValueError):
        build_loop().run(make_request(), max_steps=0)
