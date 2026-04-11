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

        prompt = self._build_prompt(
            prompt_template=prompt_template,
            rubric=request.rubric.model_dump(),
            student_response=material.extracted_text,
        )

        result = self.llm_evaluator.evaluate(prompt=prompt)
        result.prompt_used = prompt_template
        
        # Upload to Canvas if Canvas parameters are provided
        if (
            request.canvas_course_id
            and request.canvas_assignment_id
            and request.canvas_user_id
        ):
            self._upload_to_canvas(request, result)
        
        return result

    def _upload_to_canvas(self, request: EvaluationRequestDTO, result: EvaluationResponseDTO) -> None:
        """Upload evaluation results to Canvas."""
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
                comment=result.general_feedback,
            )
        except CanvasApiError as exc:
            # Log the error but don't fail the evaluation
            print(f"Error subiendo a Canvas: {exc}")

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