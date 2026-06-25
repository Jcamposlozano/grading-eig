from __future__ import annotations

import json

from grading.application.dto.evaluation_dto import EvaluationResponseDTO
from grading.ports.llm_evaluator_port import LLMEvaluatorPort
from grading.shared.prompt_loader import get_default_evaluation_prompt


class RubricGrader:
    """Califica una respuesta contra una rúbrica usando el LLM.

    Encapsula: armado del prompt, llamada al LLM, validación de criterios y
    resolución de puntajes desde la rúbrica (el LLM elige nivel; el puntaje lo
    pone el servidor). Reutilizado por el endpoint v1
    (``EvaluateStudentResponseUseCase``) y por el orquestador
    (``CalificarEntregable``).
    """

    def __init__(self, llm_evaluator: LLMEvaluatorPort) -> None:
        self._llm = llm_evaluator

    def grade(
        self,
        *,
        rubric: dict,
        student_response: str,
        prompt_template: str | None = None,
    ) -> EvaluationResponseDTO:
        template = prompt_template or get_default_evaluation_prompt()
        prompt = self._build_prompt(template, rubric, student_response)
        llm_result = self._llm.evaluate(prompt=prompt)
        result = self._normalize_and_score(rubric, llm_result)
        result.prompt_used = template
        return result

    def _build_prompt(self, template: str, rubric: dict, student_response: str) -> str:
        return template.replace(
            "{{RUBRIC}}", json.dumps(rubric, ensure_ascii=False, indent=2)
        ).replace("{{STUDENT_RESPONSE}}", student_response)

    def _normalize_and_score(
        self, rubric: dict, llm_result: EvaluationResponseDTO
    ) -> EvaluationResponseDTO:
        self._validate_all_criteria_present(rubric, llm_result)

        normalized_results = []
        total_score = 0
        for item in llm_result.criteria_results:
            self._validate_selected_level(
                rubric=rubric,
                criterion_id=item.criterion_id,
                selected_level=item.selected_level,
            )
            score = self._resolve_score_from_rubric(
                rubric=rubric,
                criterion_id=item.criterion_id,
                selected_level=item.selected_level,
            )
            item.score = score
            normalized_results.append(item)
            total_score += score

        llm_result.criteria_results = normalized_results
        llm_result.total_score = total_score
        return llm_result

    def _validate_selected_level(
        self, *, rubric: dict, criterion_id: str, selected_level: str
    ) -> None:
        for criterion in rubric["criteria"]:
            if criterion["id"] == criterion_id:
                valid_levels = {level["level"] for level in criterion["levels"]}
                if selected_level not in valid_levels:
                    raise ValueError(
                        f"Nivel inválido '{selected_level}' para criterio '{criterion_id}'. "
                        f"Niveles válidos: {sorted(valid_levels)}"
                    )
                return
        raise ValueError(f"Criterio no encontrado en la rúbrica: {criterion_id}")

    def _resolve_score_from_rubric(
        self, *, rubric: dict, criterion_id: str, selected_level: str
    ) -> int:
        for criterion in rubric["criteria"]:
            if criterion["id"] == criterion_id:
                for level in criterion["levels"]:
                    if level["level"] == selected_level:
                        return int(level["points"])
        raise ValueError(
            f"No se encontró score para criterion_id={criterion_id}, level={selected_level}"
        )

    def _validate_all_criteria_present(
        self, rubric: dict, llm_result: EvaluationResponseDTO
    ) -> None:
        expected_ids = {c["id"] for c in rubric["criteria"]}
        returned_ids = {c.criterion_id for c in llm_result.criteria_results}

        missing = expected_ids - returned_ids
        extra = returned_ids - expected_ids
        if missing:
            raise ValueError(f"Faltan criterios en la evaluación: {sorted(missing)}")
        if extra:
            raise ValueError(f"Hay criterios no definidos en la rúbrica: {sorted(extra)}")
