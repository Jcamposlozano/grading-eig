from __future__ import annotations

from abc import ABC, abstractmethod

from contenidos_inacap.application.dto.evaluation_dto import EvaluationResponseDTO


class LLMEvaluatorPort(ABC):
    @abstractmethod
    def evaluate(self, *, prompt: str) -> EvaluationResponseDTO:
        raise NotImplementedError