from __future__ import annotations

from grading.application.dto.evaluation_dto import (
    CriterionEvaluationResult,
    EvaluationResponseDTO,
)
from grading.application.services.feedback import build_grade_comment


def test_build_grade_comment():
    result = EvaluationResponseDTO(
        criteria_results=[
            CriterionEvaluationResult(
                criterion_id="c1",
                criterion_name="Claridad",
                selected_level="Alto",
                score=7,
                justification="bien argumentado",
            )
        ],
        total_score=7,
        general_feedback="buen trabajo",
    )

    comment = build_grade_comment(result)

    assert "Calificación total: 7" in comment
    assert "- Claridad: Alto (7 pts)" in comment
    assert "bien argumentado" in comment
    assert "buen trabajo" in comment
