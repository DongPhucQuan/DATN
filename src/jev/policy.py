from dataclasses import dataclass
from typing import Any

from src.jev.schemas import JEVResponse


@dataclass
class PolicyAction:
    action: str
    parameters: dict[str, Any]


class FinancePolicy:
    """
    Deterministic policy layer.

    Qwen chỉ đưa ra decision.
    Policy quyết định action.
    """

    def decide(self, response: JEVResponse) -> PolicyAction:
        is_anomaly = response.answers["is_anomaly"]
        risk_level = response.answers["risk_level"]

        # NOUL
        anomaly_probability = is_anomaly.noul or 0.0

        # SCORE
        risk_score = risk_level.score or 0

        if anomaly_probability >= 0.8:
            return PolicyAction(
                action="review_invoice",
                parameters={
                    "reason": "high_anomaly_probability",
                    "anomaly_probability": anomaly_probability,
                    "risk_score": risk_score,
                },
            )

        if risk_score >= 3:
            return PolicyAction(
                action="review_invoice",
                parameters={
                    "reason": "high_risk_score",
                    "anomaly_probability": anomaly_probability,
                    "risk_score": risk_score,
                },
            )

        return PolicyAction(
            action="accept_invoice",
            parameters={
                "reason": "within_policy",
                "anomaly_probability": anomaly_probability,
                "risk_score": risk_score,
            },
        )