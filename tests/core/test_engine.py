from src.core.engine import JEVEngine


def test_engine_runs_qwen_to_tool():
    engine = JEVEngine()

    prompt = """
    Analyze this finance task.

    Return exactly this decision:

    {
        "agent": "finance",
        "condition": "invoice_anomaly",
        "tool": "invoice_anomaly",
        "parameters": {
            "threshold": 0.15,
            "invoices": [
                {
                    "invoice_id": "INV001",
                    "expected_price": 100,
                    "actual_price": 120
                },
                {
                    "invoice_id": "INV002",
                    "expected_price": 100,
                    "actual_price": 105
                }
            ]
        }
    }

    Return JSON only.
    """

    result = engine.run(prompt)

    assert result["count"] == 1
    assert result["anomalies"][0]["invoice_id"] == "INV001"