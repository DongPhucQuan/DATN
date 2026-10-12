import pytest

from src.jev.action_router import ActionRouter
from src.jev.policy import PolicyAction


def test_review_invoice():
    router = ActionRouter()

    action = PolicyAction(
        action="review_invoice",
        parameters={
            "reason": "high_risk_score",
        },
    )

    result = router.execute(action)

    assert result["status"] == "review_required"


def test_accept_invoice():
    router = ActionRouter()

    action = PolicyAction(
        action="accept_invoice",
        parameters={
            "reason": "within_policy",
        },
    )

    result = router.execute(action)

    assert result["status"] == "accepted"


def test_unknown_action_is_rejected():
    router = ActionRouter()

    action = PolicyAction(
        action="delete_database",
        parameters={},
    )

    with pytest.raises(ValueError):
        router.execute(action)