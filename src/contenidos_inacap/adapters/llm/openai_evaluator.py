from __future__ import annotations

import json
import os

from openai import OpenAI

from contenidos_inacap.application.dto.evaluation_dto import EvaluationResponseDTO
from contenidos_inacap.ports.llm_evaluator_port import LLMEvaluatorPort


class OpenAIEvaluator(LLMEvaluatorPort):
    def __init__(self, model: str | None = None) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("No se encontró OPENAI_API_KEY en variables de entorno.")

        self.client = OpenAI(api_key=api_key)
        self.model = model or os.getenv("OPENAI_EVALUATION_MODEL", "gpt-4.1-mini")

    def evaluate(self, *, prompt: str) -> EvaluationResponseDTO:
        response = self.client.responses.create(
            model=self.model,
            input=prompt,
        )

        raw_text = response.output_text.strip()

        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"El modelo no devolvió un JSON válido. Respuesta: {raw_text}"
            ) from exc

        return EvaluationResponseDTO(
            criteria_results=payload["criteria_results"],
            total_score=None,
            general_feedback=payload["general_feedback"],
            prompt_used="",
        )