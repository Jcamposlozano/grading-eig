from __future__ import annotations

import pytest
from pydantic import ValidationError

from contenidos_inacap.application.dto.calificacion_dto import CalificacionRequestDTO


def _valid() -> dict:
    return {
        "id_universidad": "EIG",
        "id_curso": "100",
        "id_actividad": "200",
        "id_entregable": "789",
        "id_estudiante": "300",
        "id_rubrica": "r1",
        "env": "PROD",
    }


def test_normalizes_universidad_and_env():
    dto = CalificacionRequestDTO(**_valid())
    assert dto.id_universidad == "eig"
    assert dto.env == "prod"


def test_rejects_unknown_env():
    payload = _valid()
    payload["env"] = "banana"
    with pytest.raises(ValidationError):
        CalificacionRequestDTO(**payload)


def test_requires_all_ids():
    payload = _valid()
    del payload["id_entregable"]
    with pytest.raises(ValidationError):
        CalificacionRequestDTO(**payload)
