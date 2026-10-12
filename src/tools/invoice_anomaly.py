from .base import DeterministicTool


class InvoiceAnomalyTool(DeterministicTool):
    name = "invoice_anomaly"

    def validate(self, parameters: dict) -> None:
        if "invoices" not in parameters:
            raise ValueError("Missing invoices")

        if "threshold" not in parameters:
            raise ValueError("Missing threshold")

    def execute(self, parameters: dict) -> dict:
        self.validate(parameters)

        invoices = parameters["invoices"]
        threshold = parameters["threshold"]

        anomalies = []

        for invoice in invoices:
            expected = invoice["expected_price"]
            actual = invoice["actual_price"]

            deviation = (actual - expected) / expected

            if abs(deviation) >= threshold:
                anomalies.append({
                    "invoice_id": invoice["invoice_id"],
                    "deviation": deviation
                })

        return {
            "count": len(anomalies),
            "anomalies": anomalies
        }