from src.tools.invoice_anomaly import InvoiceAnomalyTool


def test_invoice_anomaly():

    tool = InvoiceAnomalyTool()

    result = tool.execute({
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
    })

    assert result["count"] == 1
    assert result["anomalies"][0]["invoice_id"] == "INV001"