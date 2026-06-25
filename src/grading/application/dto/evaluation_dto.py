from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class RubricLevelDTO(BaseModel):
    level: str = Field(..., min_length=1)
    points: int = Field(..., ge=0)
    description: str = Field(..., min_length=1)


class RubricCriterionDTO(BaseModel):
    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    levels: list[RubricLevelDTO]

    @model_validator(mode="after")
    def validate_levels(self):
        if not self.levels:
            raise ValueError("Cada criterio debe tener al menos un nivel.")
        return self


class RubricDTO(BaseModel):
    rubric_name: str = Field(..., min_length=1)
    max_score: int = Field(..., ge=0)
    criteria: list[RubricCriterionDTO]

    @model_validator(mode="after")
    def validate_criteria(self):
        if not self.criteria:
            raise ValueError("La rúbrica debe tener al menos un criterio.")

        ids = [c.id for c in self.criteria]
        if len(ids) != len(set(ids)):
            raise ValueError("Los ids de criterios deben ser únicos.")

        return self


class EvaluationRequestDTO(BaseModel):
    material_id: str
    rubric: RubricDTO
    prompt_template: str | None = None
    canvas_course_id: str | None = None
    canvas_assignment_id: str | None = None
    canvas_user_id: str | None = None


class CriterionEvaluationResult(BaseModel):
    criterion_id: str
    criterion_name: str
    selected_level: str
    score: int | None = None
    justification: str


class EvaluationResponseDTO(BaseModel):
    criteria_results: list[CriterionEvaluationResult]
    total_score: int | None = None
    general_feedback: str
    # Gate de publicación (Paso 3): el LLM decide si la nota es fiable para
    # publicarse en Canvas. Por defecto False (no publicar ante la duda).
    publish: bool = False
    confidence: float = 0.0
    prompt_used: str | None = None
