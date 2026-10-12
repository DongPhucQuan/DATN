import pytest

from src.jev.generic_policy import GenericAction, GenericPolicy
from src.jev.generic_action_router import GenericActionRouter
from src.jev.schemas import JEVAnswer, JEVResponse


def test_generic_policy_maps_choice_to_action():
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

    response = JEVResponse(
        answers={
            "priority": JEVAnswer(
                type="choice",
                choice="high",
            )
        }
    )

    action = policy.decide(response)

    assert action.action == "request_review"
    assert action.parameters["reason"] == "high_priority"


def test_generic_policy_uses_default_when_rule_does_not_match():
    policy = GenericPolicy(
        rules={
            "priority": (
                "choice",
                "high",
                {"action": "request_review"},
            )
        },
        default_action="continue",
    )

    response = JEVResponse(
        answers={
            "priority": JEVAnswer(
                type="choice",
                choice="low",
            )
        }
    )

    assert policy.decide(response).action == "continue"


def test_generic_router_executes_registered_action():
    router = GenericActionRouter(
        {
            "continue": lambda params: {
                "status": "continued",
                "parameters": params,
            }
        }
    )

    result = router.execute(
        GenericAction(
            action="continue",
            parameters={"step": 1},
        )
    )

    assert result["status"] == "continued"
    assert result["parameters"]["step"] == 1


def test_generic_router_rejects_unknown_action():
    router = GenericActionRouter({})

    with pytest.raises(ValueError):
        router.execute(
            GenericAction(
                action="delete_database",
                parameters={},
            )
        )


def test_generic_router_requires_dictionary_result():
    router = GenericActionRouter(
        {"bad_handler": lambda params: "not a dictionary"}
    )

    with pytest.raises(TypeError):
        router.execute(
            GenericAction(
                action="bad_handler",
                parameters={},
            )
        )
