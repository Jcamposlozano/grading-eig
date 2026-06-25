"""Smoke de arranque de la app completa (api + todos los routers + container).

Requiere el set completo de dependencias (poetry install). En entornos sin
ellas, se omite — los tests unitarios cubren cada pieza por separado.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("multipart")  # python-multipart (Form en materials_router)
pytest.importorskip("openai")
pytest.importorskip("pypdf")
pytest.importorskip("docx")  # python-docx
pytest.importorskip("yaml")
pytest.importorskip("dotenv")

from fastapi.testclient import TestClient

from grading.entrypoints.api import app


def test_health_and_ready():
    client = TestClient(app)
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/health/ready").status_code == 200


def test_post_calificaciones_on_real_app():
    client = TestClient(app)
    payload = {
        "id_universidad": "eig",
        "id_curso": "100",
        "id_actividad": "200",
        "id_entregable": "789",
        "id_estudiante": "300",
        "id_rubrica": "r1",
        "env": "dev",
    }

    response = client.post("/v1/calificaciones", json=payload)

    assert response.status_code == 202
    assert response.json()["status"] == "accepted"


def test_v1_routes_marked_deprecated_in_openapi():
    paths = app.openapi()["paths"]

    # rutas v1 (materials, evaluations): deprecadas
    assert paths["/v1/evaluations"]["post"]["deprecated"] is True
    assert paths["/v1/materials"]["post"]["deprecated"] is True

    # el flujo nuevo NO está deprecado
    assert paths["/v1/calificaciones"]["post"].get("deprecated", False) is False


def test_deprecation_header_on_v1_even_on_error():
    client = TestClient(app)

    # body inválido -> 422, pero el header de deprecación debe estar igual
    response = client.post("/v1/evaluations", json={})
    assert response.status_code == 422
    assert response.headers.get("Deprecation") == "true"
    assert "/v1/calificaciones" in response.headers.get("Link", "")

    # las rutas no-deprecadas no llevan el header
    assert client.get("/health").headers.get("Deprecation") is None
    assert client.post("/v1/calificaciones", json={}).headers.get("Deprecation") is None
