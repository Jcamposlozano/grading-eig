from __future__ import annotations

from abc import ABC, abstractmethod

from grading.application.dto.evaluation_dto import EvaluationResponseDTO


class LLMEvaluatorPort(ABC):
    @abstractmethod
    def evaluate(self, *, prompt: str) -> EvaluationResponseDTO:
        raise NotImplementedError
