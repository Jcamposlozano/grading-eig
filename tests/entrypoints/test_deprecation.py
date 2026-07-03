from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from fastapi import Response

from grading.entrypoints.deprecation import is_deprecated_path, mark_response_deprecated


def test_is_deprecated_path():
    assert is_deprecated_path("/v1/materials")
    assert is_deprecated_path("/v1/materials/from-canvas")
    assert is_deprecated_path("/v1/evaluations")
    # el flujo nuevo y health NO están deprecados
    assert not is_deprecated_path("/v1/calificaciones")
    assert not is_deprecated_path("/v1/universidades/eig/cursos/1/actividades/2/rubrica")
    assert not is_deprecated_path("/health")


def test_mark_response_deprecated_sets_headers():
    response = Response()

    mark_response_deprecated(response)

    assert response.headers["Deprecation"] == "true"
    assert "successor-version" in response.headers["Link"]
    assert "/v1/calificaciones" in response.headers["Link"]
