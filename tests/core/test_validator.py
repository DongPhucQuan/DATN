import pytest

from src.core.validator import DecisionValidator
from src.schemas.decision import DecisionRequest


def test_valid_decision():
    validator = DecisionValidator()

    decision = DecisionRequest(
        agent="finance",
        condition="invoice_anomaly",
        tool="invoice_anomaly",
        parameters={
            "threshold": 0.15,
            "invoices": []
        }
    )

    validator.validate(decision)


def test_reject_unknown_tool():
    validator = DecisionValidator()

    decision = DecisionRequest(
        agent="finance",
        condition="invoice_anomaly",
        tool="delete_database",
        parameters={}
    )

    with pytest.raises(ValueError):
        validator.validate(decision)


def test_reject_unknown_agent():
    validator = DecisionValidator()

    decision = DecisionRequest(
        agent="hacker",
        condition="invoice_anomaly",
        tool="invoice_anomaly",
        parameters={}
    )

    with pytest.raises(ValueError):
        validator.validate(decision)


def test_reject_inconsistent_condition_and_tool():
    validator = DecisionValidator()

    decision = DecisionRequest(
        agent="finance",
        condition="invoice_anomaly",
        tool="invoice_anomaly_wrong",
        parameters={}
    )

    with pytest.raises(ValueError):
        validator.validate(decision)