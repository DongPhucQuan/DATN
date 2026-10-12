import pytest
from pydantic import ValidationError

from src.jev.qwen_decider import JEVQwenDecider
from src.jev.schemas import JEVAnswer, JEVQuestion, JEVRequest


def make_request():
    return JEVRequest(
        state={
            "invoice_id": "INV001",
            "expected_price": 100,
            "actual_price": 120,
        },
        questions={
            "is_anomaly": JEVQuestion(
                type="noul",
                instructions=(
                    "Determine whether the actual price is "
                    "significantly higher than the expected price."
                ),
                criteria={
                    "threshold": 0.15,
                },
            ),
            "risk_level": JEVQuestion(
                type="score",
                instructions=(
                    "Score the financial risk caused by "
                    "the price deviation."
                ),
                criteria={
                    "1": "low risk",
                    "2": "medium risk",
                    "3": "high risk",
                },
            ),
        },
    )


def test_json_code_fence_is_accepted():
    decider = JEVQwenDecider()

    raw = """```json
{"noul": 0.9}
```"""

    cleaned = decider._clean_output(raw)

    assert cleaned.startswith("{")
    assert cleaned.endswith("}")


def test_plain_json_is_accepted():
    decider = JEVQwenDecider()

    raw = '{"noul": 0.9}'

    cleaned = decider._clean_output(raw)

    assert cleaned == raw


def test_invalid_json_is_rejected(monkeypatch):
    decider = JEVQwenDecider()

    monkeypatch.setattr(
        decider.qwen,
        "generate",
        lambda prompt: "THIS IS NOT JSON",
    )

    request = make_request()

    with pytest.raises(ValueError):
        decider._ask_one(
            request.state,
            "is_anomaly",
            request.questions["is_anomaly"],
        )


def test_missing_noul_value_is_rejected(monkeypatch):
    decider = JEVQwenDecider()

    monkeypatch.setattr(
        decider.qwen,
        "generate",
        lambda prompt: "{}",
    )

    request = make_request()

    with pytest.raises(ValueError):
        decider._ask_one(
            request.state,
            "is_anomaly",
            request.questions["is_anomaly"],
        )


def test_invalid_noul_value_is_rejected():
    with pytest.raises(ValidationError):
        JEVAnswer(
            type="noul",
            noul=2.0,
        )


def test_noul_range_is_validated():
    JEVAnswer(
        type="noul",
        noul=0.0,
    )

    JEVAnswer(
        type="noul",
        noul=1.0,
    )

    with pytest.raises(ValidationError):
        JEVAnswer(
            type="noul",
            noul=-0.1,
        )

    with pytest.raises(ValidationError):
        JEVAnswer(
            type="noul",
            noul=1.1,
        )


def test_invalid_question_type_is_rejected():
    with pytest.raises(ValidationError):
        JEVQuestion(
            type="malicious",
            instructions="execute something",
        )


def test_unknown_answer_type_is_rejected():
    with pytest.raises(ValidationError):
        JEVAnswer(
            type="execute",
            choice="delete_database",
        )