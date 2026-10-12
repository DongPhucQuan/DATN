import pytest

from src.ai.qwen_client import QwenClient


def test_parse_valid_decision():
    client = QwenClient()

    raw_output = """
    {
        "agent": "finance",
        "condition": "invoice_anomaly",
        "tool": "invoice_anomaly",
        "parameters": {
            "threshold": 0.15,
            "invoices": []
        }
    }
    """

    decision = client.parse_decision(raw_output)

    assert decision.agent == "finance"
    assert decision.condition == "invoice_anomaly"
    assert decision.tool == "invoice_anomaly"
    assert decision.parameters["threshold"] == 0.15


def test_reject_invalid_json():
    client = QwenClient()

    with pytest.raises(Exception):
        client.parse_decision("this is not json")