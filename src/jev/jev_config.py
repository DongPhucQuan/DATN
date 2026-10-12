"""Configuration for a standard JEV core instance."""
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any


@dataclass
class JEVConfig:
    agent_id: str = "jev-agent"
    max_steps: int = 5
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.agent_id, str) or not self.agent_id.strip():
            raise ValueError("agent_id must be a non-empty string")
        if not isinstance(self.max_steps, int) or isinstance(self.max_steps, bool) or self.max_steps <= 0:
            raise ValueError("max_steps must be a positive integer")
        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be a dictionary")
        self.metadata = deepcopy(self.metadata)

    def to_dict(self) -> dict[str, Any]:
        return {"agent_id": self.agent_id, "max_steps": self.max_steps,
                "metadata": deepcopy(self.metadata)}
