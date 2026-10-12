from src.jev.qwen_decider import JEVQwenDecider
from src.jev.schemas import JEVQuestion, JEVRequest


def test_qwen_decides_multiple_questions():
    decider = JEVQwenDecider()

    request = JEVRequest(
        state={
            "invoice_id": "INV001",
            "expected_price": 100,
            "actual_price": 120,
        },
        questions={
            "is_anomaly": JEVQuestion(
                type="noul",
                instructions=(
                    "Determine whether the actual price is significantly "
                    "higher than the expected price."
                ),
                criteria={
                    "threshold": 0.15,
                },
            ),
            "risk_level": JEVQuestion(
                type="score",
                instructions=(
                    "Score the financial risk caused by the price deviation."
                ),
                criteria={
                    "1": "low risk",
                    "2": "medium risk",
                    "3": "high risk",
                },
            ),
            "invoice_category": JEVQuestion(
                type="choice",
                instructions="Classify the invoice.",
                criteria=[
                    "normal",
                    "suspicious",
                ],
            ),
        },
    )

    response = decider.decide(request)

    assert "is_anomaly" in response.answers
    assert "risk_level" in response.answers
    assert "invoice_category" in response.answers

    assert response.answers["is_anomaly"].type == "noul"
    assert response.answers["risk_level"].type == "score"
    assert response.answers["invoice_category"].type == "choice"