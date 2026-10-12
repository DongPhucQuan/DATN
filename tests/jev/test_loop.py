import pytest

from src.jev.loop import JEVLoop
from src.jev.schemas import JEVQuestion, JEVRequest


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


def test_loop_runs_one_step():
    loop = JEVLoop()

    result = loop.run(
        make_request(),
        max_steps=5,
    )

    assert result["steps"] == 1
    assert len(result["history"]) == 1
    assert result["final_state"]["step"] == 1


def test_loop_can_continue():
    loop = JEVLoop()

    result = loop.run(
        make_request(),
        max_steps=2,
        should_continue=lambda state, result: True,
    )

    assert result["steps"] == 2
    assert len(result["history"]) == 2
    assert result["final_state"]["step"] == 2


def test_loop_stops_when_condition_is_false():
    loop = JEVLoop()

    result = loop.run(
        make_request(),
        max_steps=5,
        should_continue=lambda state, result: False,
    )

    assert result["steps"] == 1


def test_loop_respects_max_steps():
    loop = JEVLoop()

    result = loop.run(
        make_request(),
        max_steps=2,
        should_continue=lambda state, result: True,
    )

    assert result["steps"] == 2


def test_invalid_max_steps():
    loop = JEVLoop()

    with pytest.raises(ValueError):
        loop.run(
            make_request(),
            max_steps=0,
        )