from __future__ import annotations

import pytest

from contenidos_inacap.application.dto.evaluation_dto import (
    CriterionEvaluationResult,
    EvaluationRequestDTO,
    EvaluationResponseDTO,
    RubricCriterionDTO,
    RubricDTO,
    RubricLevelDTO,
)
from contenidos_inacap.application.use_cases import evaluate_student_response as mod
from contenidos_inacap.application.use_cases.evaluate_student_response import (
    EvaluateStudentResponseUseCase,
)
from contenidos_inacap.domain.entities.material import Material, MaterialStatus, MaterialType
from contenidos_inacap.ports.llm_evaluator_port import LLMEvaluatorPort


def _material() -> Material:
    return Material(
        id="m1",
        filename="f.txt",
        original_filename="f.txt",
        media_type=MaterialType.DOCUMENT,
        mime_type="text/plain",
        file_path="/tmp/f.txt",
        file_size=10,
        extracted_text="respuesta del estudiante",
        status=MaterialStatus.COMPLETED,
    )


class FakeRepo:
    def __init__(self, material: Material) -> None:
        self._m = material

    def get_by_id(self, material_id: str):
        return self._m if material_id == self._m.id else None


class FakeEvaluator(LLMEvaluatorPort):
    def __init__(self, *, publish: bool) -> None:
        self._publish = publish

    def evaluate(self, *, prompt: str) -> EvaluationResponseDTO:
        return EvaluationResponseDTO(
            criteria_results=[
                CriterionEvaluationResult(
                    criterion_id="c1",
                    criterion_name="Claridad",
                    selected_level="Alto",
                    justification="ok",
                )
            ],
            general_feedback="bien",
            publish=self._publish,
            confidence=0.9,
        )


def _request() -> EvaluationRequestDTO:
    rubric = RubricDTO(
        rubric_name="R",
        max_score=10,
        criteria=[
            RubricCriterionDTO(
                id="c1",
                name="Claridad",
                levels=[RubricLevelDTO(level="Alto", points=10, description="muy bien")],
            )
        ],
    )
    return EvaluationRequestDTO(
        material_id="m1",
        rubric=rubric,
        canvas_course_id="100",
        canvas_assignment_id="200",
        canvas_user_id="300",
    )


@pytest.fixture
def canvas_env(monkeypatch):
    monkeypatch.setenv("CANVAS_BASE_URL", "https://eig.x")
    monkeypatch.setenv("CANVAS_ACCESS_TOKEN", "tok")


def test_publishes_when_flag_true(monkeypatch, canvas_env):
    calls: list[dict] = []
    monkeypatch.setattr(mod, "update_submission_grade", lambda **k: calls.append(k))
    use_case = EvaluateStudentResponseUseCase(FakeEvaluator(publish=True), FakeRepo(_material()))

    result = use_case.execute(_request())

    assert result.publish is True
    assert result.total_score == 10
    assert len(calls) == 1
    assert calls[0]["course_id"] == "100"
    assert calls[0]["score"] == 10


def test_does_not_publish_when_flag_false(monkeypatch, canvas_env):
    calls: list[dict] = []
    monkeypatch.setattr(mod, "update_submission_grade", lambda **k: calls.append(k))
    use_case = EvaluateStudentResponseUseCase(FakeEvaluator(publish=False), FakeRepo(_material()))

    result = use_case.execute(_request())

    assert result.publish is False
    assert result.total_score == 10  # se calcula igual, solo no se publica
    assert calls == []
