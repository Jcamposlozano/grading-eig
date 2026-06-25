from __future__ import annotations

import pytest

from grading.application.dto.evaluation_dto import (
    CriterionEvaluationResult,
    EvaluationResponseDTO,
    RubricCriterionDTO,
    RubricDTO,
    RubricLevelDTO,
)
from grading.application.services.rubric_grader import RubricGrader


class FakeLLM:
    def __init__(self, dto: EvaluationResponseDTO) -> None:
        self.dto = dto
        self.prompt = None

    def evaluate(self, *, prompt: str) -> EvaluationResponseDTO:
        self.prompt = prompt
        return self.dto


def _rubric() -> dict:
    return RubricDTO(
        rubric_name="R",
        max_score=10,
        criteria=[
            RubricCriterionDTO(
                id="c1",
                name="Crit",
                levels=[
                    RubricLevelDTO(level="Alto", points=7, description="ok"),
                    RubricLevelDTO(level="Bajo", points=2, description="meh"),
                ],
            )
        ],
    ).model_dump()


def _llm_result(level: str = "Alto", criteria_ids=("c1",)) -> EvaluationResponseDTO:
    return EvaluationResponseDTO(
        criteria_results=[
            CriterionEvaluationResult(
                criterion_id=cid,
                criterion_name="Crit",
                selected_level=level,
                justification="j",
            )
            for cid in criteria_ids
        ],
        general_feedback="ok",
        publish=True,
        confidence=0.8,
    )


def test_grades_and_resolves_score_from_rubric():
    llm = FakeLLM(_llm_result(level="Alto"))
    grader = RubricGrader(llm)

    result = grader.grade(rubric=_rubric(), student_response="texto del alumno")

    assert result.total_score == 7
    assert result.criteria_results[0].score == 7
    assert result.publish is True
    assert "texto del alumno" in llm.prompt  # se inyectó la respuesta


def test_rejects_invalid_level():
    grader = RubricGrader(FakeLLM(_llm_result(level="Inexistente")))
    with pytest.raises(ValueError):
        grader.grade(rubric=_rubric(), student_response="t")


def test_rejects_missing_criteria():
    grader = RubricGrader(FakeLLM(_llm_result(criteria_ids=())))
    with pytest.raises(ValueError):
        grader.grade(rubric=_rubric(), student_response="t")
