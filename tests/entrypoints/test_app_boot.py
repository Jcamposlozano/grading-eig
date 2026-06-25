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

from contenidos_inacap.entrypoints.api import app


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
