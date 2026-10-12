from src.schemas.decision import DecisionRequest
from src.core.validator import DecisionValidator
from src.tools.invoice_anomaly import InvoiceAnomalyTool


class ToolRouter:

    def __init__(self):
        self.validator = DecisionValidator()

        self.tools = {
            InvoiceAnomalyTool.name: InvoiceAnomalyTool()
        }

    def execute(self, decision: DecisionRequest) -> dict:

        self.validator.validate(decision)

        tool = self.tools.get(decision.tool)

        if tool is None:
            raise ValueError(
                f"Tool not registered: {decision.tool}"
            )

        return tool.execute(decision.parameters)