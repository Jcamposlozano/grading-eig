from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi import FastAPI
from fastapi.testclient import TestClient

from contenidos_inacap.adapters.queue.in_memory_queue import InMemoryQueue
from contenidos_inacap.adapters.storage.local_object_storage import LocalObjectStorage
from contenidos_inacap.entrypoints.routers import calificaciones_router as mod
from contenidos_inacap.shared import s3_keys

_ALL_UNIS = ["westfield", "eig", "esic", "uide"]


def _valid_payload() -> dict:
    return {
        "id_universidad": "eig",
        "id_curso": "100",
        "id_actividad": "200",
        "id_entregable": "789",
        "id_estudiante": "300",
        "id_rubrica": "r1",
        "env": "prod",
    }


def _client(*, allowed=_ALL_UNIS):
    app = FastAPI()
    app.include_router(mod.router)
    queue = InMemoryQueue()
    app.dependency_overrides[mod.get_queue_dep] = lambda: queue
    app.dependency_overrides[mod.get_allowed_universidades_dep] = lambda: list(allowed)
    return TestClient(app), queue


def test_build_idempotency_key_deterministic_and_sensitive():
    payload = _valid_payload()
    assert mod.build_idempotency_key(payload) == mod.build_idempotency_key(dict(payload))

    other = dict(payload, id_entregable="999")
    assert mod.build_idempotency_key(payload) != mod.build_idempotency_key(other)


def test_post_enqueues_and_returns_202():
    client, queue = _client()

    response = client.post("/v1/calificaciones", json=_valid_payload())

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "accepted"
    assert body["idempotency_key"]

    messages = queue.consume(max_messages=1)
    assert messages[0].body["id_universidad"] == "eig"
    assert messages[0].body["idempotency_key"] == body["idempotency_key"]


def test_post_rejects_bad_env():
    client, _ = _client()

    response = client.post("/v1/calificaciones", json={**_valid_payload(), "env": "banana"})

    assert response.status_code == 422


def test_post_rejects_universidad_not_allowed():
    client, queue = _client(allowed=["esic", "uide"])  # eig NO está habilitada

    response = client.post("/v1/calificaciones", json=_valid_payload())

    assert response.status_code == 400
    assert "no habilitada" in response.json()["detail"]
    assert queue.consume(max_messages=1) == []  # no se encoló


def test_post_accepts_allowed_universidad_after_normalizacion():
    client, queue = _client(allowed=["eig"])

    response = client.post("/v1/calificaciones", json={**_valid_payload(), "id_universidad": "EIG"})

    assert response.status_code == 202
    assert queue.consume(max_messages=1)[0].body["id_universidad"] == "eig"


def test_get_calificacion_404_then_200(tmp_path):
    storage = LocalObjectStorage(base_dir=str(tmp_path))
    app = FastAPI()
    app.include_router(mod.router)
    app.dependency_overrides[mod.get_storage_dep] = lambda: storage
    client = TestClient(app)

    url = "/v1/universidades/eig/cursos/100/estudiantes/300/entregables/789/calificacion?env=prod"
    assert client.get(url).status_code == 404

    storage.put_json(
        key=s3_keys.grading_key(
            env="prod",
            universidad_id="eig",
            curso_id="100",
            estudiante_id="300",
            entregable_id="789",
        ),
        obj={"total_score": 7},
    )

    response = client.get(url)
    assert response.status_code == 200
    assert response.json()["total_score"] == 7
