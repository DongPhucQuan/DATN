from typing import Any, Literal

from pydantic import BaseModel, Field


QuestionType = Literal["choice", "score", "noul"]


class JEVQuestion(BaseModel):
    type: QuestionType
    instructions: str
    criteria: Any = None


class JEVRequest(BaseModel):
    state: dict[str, Any]
    questions: dict[str, JEVQuestion] = Field(default_factory=dict)


class JEVAnswer(BaseModel):
    type: QuestionType

    choice: str | None = None

    score: float | None = None

    noul: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    probabilities: dict[str, float] = Field(
        default_factory=dict
    )

    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )


class JEVResponse(BaseModel):
    answers: dict[str, JEVAnswer] = Field(
        default_factory=dict
    )