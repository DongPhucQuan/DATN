from src.jev.schemas import (
    JEVAnswer,
    JEVQuestion,
    JEVRequest,
    JEVResponse,
)


def test_jev_request_supports_three_question_types():
    request = JEVRequest(
        state={
            "invoice_amount": 120,
            "expected_amount": 100,
        },
        questions={
            "is_anomaly": JEVQuestion(
                type="noul",
                instructions="Determine whether the invoice is anomalous.",
                criteria={
                    "threshold": 0.15,
                },
            ),
            "risk": JEVQuestion(
                type="score",
                instructions="Score the financial risk.",
                criteria={
                    "1": "low",
                    "2": "medium",
                    "3": "high",
                },
            ),
            "category": JEVQuestion(
                type="choice",
                instructions="Classify the invoice.",
                criteria=[
                    "normal",
                    "suspicious",
                ],
            ),
        },
    )

    assert request.questions["is_anomaly"].type == "noul"
    assert request.questions["risk"].type == "score"
    assert request.questions["category"].type == "choice"


def test_jev_response():
    response = JEVResponse(
        answers={
            "is_anomaly": JEVAnswer(
                type="noul",
                noul=0.9,
            ),
            "risk": JEVAnswer(
                type="score",
                score=3,
                probabilities={
                    "1": 0.05,
                    "2": 0.15,
                    "3": 0.80,
                },
                confidence=0.80,
            ),
            "category": JEVAnswer(
                type="choice",
                choice="suspicious",
                probabilities={
                    "normal": 0.1,
                    "suspicious": 0.9,
                },
                confidence=0.9,
            ),
        }
    )

    assert response.answers["is_anomaly"].noul == 0.9
    assert response.answers["risk"].score == 3
    assert response.answers["category"].choice == "suspicious"