
from dataclasses import dataclass
from typing import Any

from src.jev.schemas import JEVResponse


@dataclass
class ChatAction:
    action: str
    parameters: dict[str, Any]


class ChatPolicy:
    def __init__(self, anomaly_threshold: float = 0.15):
        if not 0 < anomaly_threshold <= 1:
            raise ValueError("anomaly_threshold phải nằm trong (0, 1].")

        self.anomaly_threshold = anomaly_threshold

    def decide(
        self,
        response: JEVResponse,
        *,
        anomaly_score: float | None = None,
        anomaly_reason: str | None = None,
    ) -> ChatAction:
        answers = response.answers

        category_answer = answers.get("category")
        risk_answer = answers.get("risk_level")

        category = (
            category_answer.choice
            if category_answer is not None
            else "normal"
        )
        risk = (
            risk_answer.score or 0
            if risk_answer is not None
            else 0
        )

        # Chỉ sử dụng anomaly_score khi được cung cấp
        # từ nguồn đáng tin cậy, chẳng hạn phép tính Python.
        if anomaly_score is not None:
            if not 0 <= anomaly_score <= 1:
                raise ValueError("anomaly_score phải nằm trong [0, 1].")

            if anomaly_score > self.anomaly_threshold:
                return ChatAction(
                    action="flag_message",
                    parameters={
                        "reason": anomaly_reason or "anomaly_threshold_exceeded",
                        "category": category,
                        "risk_level": risk,
                        "anomaly_score": anomaly_score,
                        "threshold": self.anomaly_threshold,
                    },
                )

        if category == "suspicious" or risk >= 3:
            return ChatAction(
                action="flag_message",
                parameters={
                    "reason": "suspicious_or_high_risk",
                    "category": category,
                    "risk_level": risk,
                },
            )

        if category == "important" or risk >= 2:
            return ChatAction(
                action="acknowledge_message",
                parameters={
                    "reason": "important_or_medium_risk",
                    "category": category,
                    "risk_level": risk,
                },
            )

        return ChatAction(
            action="normal_response",
            parameters={
                "reason": "normal_message",
                "category": category,
                "risk_level": risk,
            },
        )
