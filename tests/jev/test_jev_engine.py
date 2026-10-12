from unittest import result

from src.jev.engine import JEVEngine
from src.jev.schemas import JEVQuestion, JEVRequest


def test_jev_engine_end_to_end():
    engine = JEVEngine()

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

    result = engine.run(request)

    assert "decisions" in result
    assert "action" in result
    assert "result" in result

    assert result["action"]["name"] in {
        "review_invoice",
        "accept_invoice",
    }
    assert "initial_state" in result
    assert "final_state" in result

    assert result["initial_state"]["invoice_id"] == "INV001"

    assert (
      result["final_state"]["last_action"]
      == result["action"]["name"]
)

    assert (
    result["final_state"]["last_result"]
    == result["result"]
)         