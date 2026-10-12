import pytest

from src.core.engine import JEVEngine
from src.schemas.decision import DecisionRequest


def test_reject_dangerous_tool():
    engine = JEVEngine()

    decision = DecisionRequest(
        agent="finance",
        condition="invoice_anomaly",
        tool="delete_database",
        parameters={}
    )

    with pytest.raises(ValueError):
        engine.router.execute(decision)


def test_reject_unknown_agent():
    engine = JEVEngine()

    decision = DecisionRequest(
        agent="hacker",
        condition="invoice_anomaly",
        tool="invoice_anomaly",
        parameters={}
    )

    with pytest.raises(ValueError):
        engine.router.execute(decision)


def test_reject_condition_tool_mismatch():
    engine = JEVEngine()

    decision = DecisionRequest(
        agent="finance",
        condition="invoice_anomaly",
        tool="delete_database",
        parameters={}
    )

    with pytest.raises(ValueError):
        engine.router.execute(decision)