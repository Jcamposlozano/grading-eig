from __future__ import annotations

import json
import os

from contenidos_inacap.adapters.canvas.canvas_client import (
    CanvasApiError,
    CanvasNotConfiguredError,
    update_submission_grade,
)
from contenidos_inacap.application.dto.evaluation_dto import (
    EvaluationRequestDTO,
    EvaluationResponseDTO,
)
from contenidos_inacap.ports.llm_evaluator_port import LLMEvaluatorPort
from contenidos_inacap.ports.material_repository_port import MaterialRepositoryPort
from contenidos_inacap.shared.prompt_loader import get_default_evaluation_prompt


class MaterialForEvaluationNotFoundError(Exception):
    pass


class MaterialWithoutExtractedTextError(Exception):
    pass


class EvaluateStudentResponseUseCase:
    def __init__(
        self,
        llm_evaluator: LLMEvaluatorPort,
        material_repository: MaterialRepositoryPort,
    ) -> None:
        self.llm_evaluator = llm_evaluator
        self.material_repository = material_repository

    def execute(self, request: EvaluationRequestDTO) -> EvaluationResponseDTO:
        material = self.material_repository.get_by_id(request.material_id)
        if not material:
            raise MaterialForEvaluationNotFoundError(
                f"No existe material con id={request.material_id}"
            )

        if not material.extracted_text or not material.extracted_text.strip():
            raise MaterialWithoutExtractedTextError(
                f"El material con id={request.material_id} no tiene texto extraído."
            )

        prompt_template = request.prompt_template or get_default_evaluation_prompt()
        rubric = request.rubric.model_dump()

        prompt = self._build_prompt(
            prompt_template=prompt_template,
            rubric=rubric,
            student_response=material.extracted_text,
        )

        llm_result = self.llm_evaluator.evaluate(prompt=prompt)

        validated_result = self._normalize_and_score_result(
            rubric=rubric,
            llm_result=llm_result,
        )
        validated_result.prompt_used = prompt_template

        if (
            request.canvas_course_id
            and request.canvas_assignment_id
            and request.canvas_user_id
        ):
            self._upload_to_canvas(request, validated_result)

        return validated_result


    def _normalize_and_score_result(
        self,
        *,
        rubric: dict,
        llm_result: EvaluationResponseDTO,
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
        self,
        *,
        rubric: dict,
        criterion_id: str,
        selected_level: str,
    ) -> None:
        for criterion in rubric["criteria"]:
            if criterion["id"] == criterion_id:
                #valid_levels = {level["name"] for level in criterion["levels"]}
                valid_levels = {level["level"] for level in criterion["levels"]}
                if selected_level not in valid_levels:
                    raise ValueError(
                        f"Nivel inválido '{selected_level}' para criterio '{criterion_id}'. "
                        f"Niveles válidos: {sorted(valid_levels)}"
                    )
                return

        raise ValueError(f"Criterio no encontrado en la rúbrica: {criterion_id}")

    def _resolve_score_from_rubric(
        self,
        *,
        rubric: dict,
        criterion_id: str,
        selected_level: str,
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
        self,
        rubric: dict,
        llm_result: EvaluationResponseDTO,
    ) -> None:
        expected_ids = {c["id"] for c in rubric["criteria"]}
        returned_ids = {c.criterion_id for c in llm_result.criteria_results}

        missing = expected_ids - returned_ids
        extra = returned_ids - expected_ids

        if missing:
            raise ValueError(f"Faltan criterios en la evaluación: {sorted(missing)}")

        if extra:
            raise ValueError(f"Hay criterios no definidos en la rúbrica: {sorted(extra)}")
    
    def _upload_to_canvas(
        self,
        request: EvaluationRequestDTO,
        result: EvaluationResponseDTO,
    ) -> None:
        canvas_base_url = os.getenv("CANVAS_BASE_URL")
        canvas_token = os.getenv("CANVAS_ACCESS_TOKEN")

        if not canvas_base_url or not canvas_token:
            raise CanvasNotConfiguredError(
                "CANVAS_BASE_URL y CANVAS_ACCESS_TOKEN deben estar configurados para subir a Canvas"
            )

        try:
            comment = self._build_canvas_comment(result)

            update_submission_grade(
                base_url=canvas_base_url,
                token=canvas_token,
                course_id=request.canvas_course_id,
                assignment_id=request.canvas_assignment_id,
                user_id=request.canvas_user_id,
                score=result.total_score,
                comment=comment,
            )
        except CanvasApiError as exc:
            print(f"Error subiendo a Canvas: {exc}")

    def _build_canvas_comment(self, result: EvaluationResponseDTO) -> str:
        lines = []
        lines.append(f"Calificación total: {result.total_score}")
        lines.append("")
        lines.append("Detalle por criterio:")

        for item in result.criteria_results:
            lines.append(
                f"- {item.criterion_name}: {item.selected_level} ({item.score} pts)"
            )
            lines.append(f"  Justificación: {item.justification}")

        lines.append("")
        lines.append("Retroalimentación general:")
        lines.append(result.general_feedback)

        return "\n".join(lines)

    def _build_prompt(
        self,
        *,
        prompt_template: str,
        rubric: dict,
        student_response: str,
    ) -> str:
        return prompt_template.replace(
            "{{RUBRIC}}",
            json.dumps(rubric, ensure_ascii=False, indent=2),
        ).replace(
            "{{STUDENT_RESPONSE}}",
            student_response,
        )