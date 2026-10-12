from src.jev.policy import FinancePolicy
from src.jev.schemas import JEVAnswer, JEVResponse


def test_high_anomaly_requires_review():
    response = JEVResponse(
        answers={
            "is_anomaly": JEVAnswer(
                type="noul",
                noul=0.9,
            ),
            "risk_level": JEVAnswer(
                type="score",
                score=2,
            ),
        }
    )

    policy = FinancePolicy()

    action = policy.decide(response)

    assert action.action == "review_invoice"
    assert action.parameters["reason"] == "high_anomaly_probability"


def test_high_risk_requires_review():
    response = JEVResponse(
        answers={
            "is_anomaly": JEVAnswer(
                type="noul",
                noul=0.3,
            ),
            "risk_level": JEVAnswer(
                type="score",
                score=3,
            ),
        }
    )

    policy = FinancePolicy()

    action = policy.decide(response)

    assert action.action == "review_invoice"
    assert action.parameters["reason"] == "high_risk_score"


def test_normal_invoice_is_accepted():
    response = JEVResponse(
        answers={
            "is_anomaly": JEVAnswer(
                type="noul",
                noul=0.1,
            ),
            "risk_level": JEVAnswer(
                type="score",
                score=1,
            ),
        }
    )

    policy = FinancePolicy()

    action = policy.decide(response)

    assert action.action == "accept_invoice"
    assert action.parameters["reason"] == "within_policy"