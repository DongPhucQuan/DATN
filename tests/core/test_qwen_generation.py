from src.ai.qwen_client import QwenClient


def test_qwen_generates_decision():
    client = QwenClient()

    prompt = """
    Analyze this finance task.

    There may be invoices whose actual price differs
    significantly from the expected price.

    Return a decision using exactly this JSON structure:

    {
        "agent": "finance",
        "condition": "invoice_anomaly",
        "tool": "invoice_anomaly",
        "parameters": {
            "threshold": 0.15,
            "invoices": []
        }
    }

    Return JSON only.
    """

    raw_output = client.generate(prompt)

    decision = client.parse_decision(raw_output)

    assert decision.agent == "finance"
    assert decision.condition == "invoice_anomaly"
    assert decision.tool == "invoice_anomaly"
    assert decision.parameters["threshold"] == 0.15