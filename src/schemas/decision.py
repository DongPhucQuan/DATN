from typing import Any

from pydantic import BaseModel, Field


class DecisionRequest(BaseModel):
    agent: str
    condition: str
    tool: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class DecisionResult(BaseModel):
    success: bool
    tool: str
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None