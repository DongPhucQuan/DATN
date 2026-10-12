from abc import ABC, abstractmethod


class DeterministicTool(ABC):
    name: str

    @abstractmethod
    def validate(self, parameters: dict) -> None:
        pass

    @abstractmethod
    def execute(self, parameters: dict) -> dict:
        pass