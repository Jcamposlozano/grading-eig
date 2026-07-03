from __future__ import annotations

import os

from grading.adapters.canvas.canvas_client import (
    CanvasApiError,
    CanvasNotConfiguredError,
    update_submission_grade,
)
from grading.application.dto.evaluation_dto import (
    EvaluationRequestDTO,
    EvaluationResponseDTO,
)
from grading.application.services.feedback import build_grade_comment
from grading.application.services.rubric_grader import RubricGrader
from grading.ports.llm_evaluator_port import LLMEvaluatorPort
from grading.ports.material_repository_port import MaterialRepositoryPort
from grading.shared.logger import get_logger

log = get_logger("grading.evaluate")


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
        self.material_repository = material_repository
        self._grader = RubricGrader(llm_evaluator)

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

        result = self._grader.grade(
            rubric=request.rubric.model_dump(),
            student_response=material.extracted_text,
            prompt_template=request.prompt_template,
        )

        # Gate de publicación: solo se sube la nota a Canvas si el LLM lo aprobó
        # (publish=True) y se proporcionó el contexto de Canvas.
        has_canvas_context = bool(
            request.canvas_course_id and request.canvas_assignment_id and request.canvas_user_id
        )
        if result.publish and has_canvas_context:
            self._upload_to_canvas(request, result)

        return result

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
            update_submission_grade(
                base_url=canvas_base_url,
                token=canvas_token,
                course_id=request.canvas_course_id,
                assignment_id=request.canvas_assignment_id,
                user_id=request.canvas_user_id,
                score=result.total_score,
                comment=build_grade_comment(result),
            )
        except CanvasApiError as exc:
            log.error("Error subiendo a Canvas: %s", exc)
