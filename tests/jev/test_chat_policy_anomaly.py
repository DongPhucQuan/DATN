
from unittest.mock import Mock

import pytest

from src.jev.chat_policy import ChatPolicy


def make_response(category="normal", risk=1):
    response = Mock()
    response.answers = {
        "category": Mock(choice=category),
        "risk_level": Mock(score=risk),
    }
    return response


def test_large_anomaly_is_flagged():
    policy = ChatPolicy(anomaly_threshold=0.15)

    action = policy.decide(
        make_response(),
        anomaly_score=1.0,
        anomaly_reason="invoice_deviation",
    )

    assert action.action == "flag_message"
    assert action.parameters["reason"] == "invoice_deviation"


def test_small_anomaly_is_not_flagged():
    policy = ChatPolicy(anomaly_threshold=0.15)

    action = policy.decide(
        make_response(),
        anomaly_score=0.05,
    )

    assert action.action == "normal_response"


def test_invalid_anomaly_score_is_rejected():
    policy = ChatPolicy()

    with pytest.raises(ValueError):
        policy.decide(make_response(), anomaly_score=1.1)


def test_existing_risk_policy_is_preserved():
    policy = ChatPolicy()

    action = policy.decide(make_response(risk=3))

    assert action.action == "flag_message"
