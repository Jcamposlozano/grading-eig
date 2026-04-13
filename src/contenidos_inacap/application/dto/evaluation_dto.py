from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


class RubricLevelDTO(BaseModel):
    level: str = Field(..., min_length=1)
    points: int = Field(..., ge=0)
    description: str = Field(..., min_length=1)


class RubricCriterionDTO(BaseModel):
    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    levels: List[RubricLevelDTO]

    @model_validator(mode="after")
    def validate_levels(self):
        if not self.levels:
            raise ValueError("Cada criterio debe tener al menos un nivel.")
        return self


class RubricDTO(BaseModel):
    rubric_name: str = Field(..., min_length=1)
    max_score: int = Field(..., ge=0)
    criteria: List[RubricCriterionDTO]

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
    prompt_template: Optional[str] = None
    canvas_course_id: Optional[str] = None
    canvas_assignment_id: Optional[str] = None
    canvas_user_id: Optional[str] = None


class CriterionEvaluationResultDTO(BaseModel):
    criterion_id: str
    criterion_name: str
    selected_level: str
    score: int
    justification: str


class EvaluationResponseDTO(BaseModel):
    criteria_results: List[CriterionEvaluationResultDTO]
    total_score: int
    general_feedback: str
    prompt_used: str