from src.core.tool_router import ToolRouter
from src.schemas.decision import DecisionRequest


def test_router_executes_invoice_tool():

    router = ToolRouter()

    decision = DecisionRequest(
        agent="finance",
        condition="invoice_anomaly",
        tool="invoice_anomaly",
        parameters={
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
    )

    result = router.execute(decision)

    assert result["count"] == 1
    assert result["anomalies"][0]["invoice_id"] == "INV001"