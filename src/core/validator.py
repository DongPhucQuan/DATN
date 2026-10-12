from src.schemas.decision import DecisionRequest


class DecisionValidator:

    ALLOWED_AGENTS = {
        "finance"
    }

    ALLOWED_CONDITIONS = {
        "invoice_anomaly"
    }

    ALLOWED_TOOLS = {
        "invoice_anomaly"
    }

    def validate(self, decision: DecisionRequest) -> None:

        if decision.agent not in self.ALLOWED_AGENTS:
            raise ValueError(
                f"Agent not allowed: {decision.agent}"
            )

        if decision.condition not in self.ALLOWED_CONDITIONS:
            raise ValueError(
                f"Condition not allowed: {decision.condition}"
            )

        if decision.tool not in self.ALLOWED_TOOLS:
            raise ValueError(
                f"Tool not allowed: {decision.tool}"
            )

        if decision.condition != decision.tool:
            raise ValueError(
                "Condition and tool are inconsistent"
            )