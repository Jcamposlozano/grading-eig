from __future__ import annotations

from contenidos_inacap.shared.s3_keys import (
    extracted_text_key,
    grading_key,
    metadata_key,
    raw_key,
    rubrica_key,
)


def test_rubrica_key_layout():
    key = rubrica_key(
        env="prod",
        universidad_id="eig",
        curso_id="123",
        actividad_id="456",
        rubrica_id="rA",
    )
    assert key == "prod/eig/123/actividades/456/rubrica/rA.json"


def _hierarchy() -> dict:
    return {
        "env": "prod",
        "universidad_id": "eig",
        "curso_id": "123",
        "estudiante_id": "555",
        "entregable_id": "789",
    }


def test_entregable_artifact_keys():
    base = "prod/eig/123/555/789"
    assert raw_key(filename="t.pdf", **_hierarchy()) == f"{base}/raw/t.pdf"
    assert extracted_text_key(**_hierarchy()) == f"{base}/extracted/extracted.txt"
    assert grading_key(**_hierarchy()) == f"{base}/grading/calificacion.json"
    assert metadata_key(**_hierarchy()) == f"{base}/grading/metadata.json"
