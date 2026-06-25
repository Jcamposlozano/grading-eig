from __future__ import annotations

import pytest

from contenidos_inacap.adapters.storage.local_object_storage import LocalObjectStorage
from contenidos_inacap.application.dto.evaluation_dto import (
    CriterionEvaluationResult,
    EvaluationResponseDTO,
    RubricCriterionDTO,
    RubricDTO,
    RubricLevelDTO,
)
from contenidos_inacap.application.services.rubric_grader import RubricGrader
from contenidos_inacap.application.strategies.extraction import build_extraction_registry
from contenidos_inacap.application.use_cases.calificar_entregable import (
    CalificarEntregable,
    CalificarEntregableCommand,
    TipoEntregableNoSoportadoError,
)
from contenidos_inacap.ports.canvas_port import AttachmentRef
from contenidos_inacap.shared import s3_keys

RUBRIC = RubricDTO(
    rubric_name="R",
    max_score=10,
    criteria=[
        RubricCriterionDTO(
            id="c1",
            name="Crit",
            levels=[RubricLevelDTO(level="Alto", points=10, description="ok")],
        )
    ],
)


class FakeCanvas:
    def __init__(self, *, filename="tarea.txt", data=b"respuesta del alumno") -> None:
        self.filename = filename
        self.data = data
        self.published: list[dict] = []

    def fetch_submission_attachment(self, *, course_id, assignment_id, user_id, attachment_index=0):
        return AttachmentRef(file_id="f1", filename=self.filename)

    def download_file(self, *, attachment):
        return self.data, self.filename

    def publish_grade(self, *, course_id, assignment_id, user_id, score, comment):
        self.published.append({"course_id": course_id, "user_id": user_id, "score": score})


class FakeCanvasFactory:
    def __init__(self, canvas: FakeCanvas) -> None:
        self.canvas = canvas
        self.requested = None

    def for_university(self, *, universidad_id, env):
        self.requested = (universidad_id, env)
        return self.canvas


class FakeDoc:
    """Lee el archivo temporal volcado por el orquestador y devuelve su texto."""

    def extract(self, *, file_path):
        with open(file_path, "rb") as handle:
            return handle.read().decode("utf-8")


class FakeLLM:
    def __init__(self, *, publish: bool) -> None:
        self.publish = publish

    def evaluate(self, *, prompt):
        return EvaluationResponseDTO(
            criteria_results=[
                CriterionEvaluationResult(
                    criterion_id="c1",
                    criterion_name="Crit",
                    selected_level="Alto",
                    justification="ok",
                )
            ],
            general_feedback="bien",
            publish=self.publish,
            confidence=0.9,
        )


class FakeRubricStore:
    def load(self, *, env, universidad_id, curso_id, actividad_id, rubrica_id):
        return RUBRIC


def _orchestrator(tmp_path, canvas, *, publish):
    storage = LocalObjectStorage(base_dir=str(tmp_path))
    registry = build_extraction_registry(
        document_extractor=FakeDoc(), transcriber=None, audio_extractor=None
    )
    return (
        CalificarEntregable(
            canvas_factory=FakeCanvasFactory(canvas),
            storage=storage,
            rubric_store=FakeRubricStore(),
            extraction_registry=registry,
            grader=RubricGrader(FakeLLM(publish=publish)),
        ),
        storage,
    )


def _command() -> CalificarEntregableCommand:
    return CalificarEntregableCommand(
        id_universidad="eig",
        id_curso="100",
        id_actividad="200",
        id_entregable="789",
        id_estudiante="300",
        id_rubrica="r1",
        env="dev",
    )


def _hierarchy() -> dict:
    return {
        "env": "dev",
        "universidad_id": "eig",
        "curso_id": "100",
        "estudiante_id": "300",
        "entregable_id": "789",
    }


def test_full_flow_writes_artifacts_and_publishes(tmp_path):
    canvas = FakeCanvas(filename="tarea.txt", data=b"respuesta del alumno")
    orchestrator, storage = _orchestrator(tmp_path, canvas, publish=True)

    result = orchestrator.execute(_command())

    assert result.total_score == 10
    assert storage.exists(key=s3_keys.raw_key(filename="tarea.txt", **_hierarchy()))
    assert (
        storage.get_text(key=s3_keys.extracted_text_key(**_hierarchy())) == "respuesta del alumno"
    )
    assert storage.exists(key=s3_keys.grading_key(**_hierarchy()))
    metadata = storage.get_json(key=s3_keys.metadata_key(**_hierarchy()))
    assert metadata["published"] is True
    assert canvas.published and canvas.published[0]["score"] == 10
    assert canvas.published[0]["course_id"] == "100"


def test_does_not_publish_when_flag_false(tmp_path):
    canvas = FakeCanvas()
    orchestrator, storage = _orchestrator(tmp_path, canvas, publish=False)

    orchestrator.execute(_command())

    assert canvas.published == []
    assert storage.get_json(key=s3_keys.metadata_key(**_hierarchy()))["published"] is False
    assert storage.exists(key=s3_keys.grading_key(**_hierarchy()))


def test_idempotent_skip_when_already_graded(tmp_path):
    canvas = FakeCanvas()
    orchestrator, storage = _orchestrator(tmp_path, canvas, publish=True)
    storage.put_json(key=s3_keys.grading_key(**_hierarchy()), obj={"already": True})

    result = orchestrator.execute(_command())

    assert result is None
    assert canvas.published == []


def test_unsupported_extension_raises(tmp_path):
    canvas = FakeCanvas(filename="tarea.xyz", data=b"x")
    orchestrator, _ = _orchestrator(tmp_path, canvas, publish=True)

    with pytest.raises(TipoEntregableNoSoportadoError):
        orchestrator.execute(_command())
