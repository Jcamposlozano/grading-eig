from __future__ import annotations

import hashlib
import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from grading.application.dto.calificacion_dto import (
    CalificacionAcceptedDTO,
    CalificacionRequestDTO,
)
from grading.ports.queue_port import QueuePort
from grading.ports.rubric_port import RubricNotFoundError, RubricPort
from grading.ports.storage_port import StoragePort
from grading.shared import s3_keys

router = APIRouter(tags=["calificaciones"])

_IDEMPOTENCY_FIELDS = (
    "env",
    "id_universidad",
    "id_curso",
    "id_actividad",
    "id_entregable",
    "id_estudiante",
    "id_rubrica",
)


def get_queue_dep() -> QueuePort:
    from grading.shared.container import get_queue

    return get_queue()


def get_storage_dep() -> StoragePort:
    from grading.shared.container import get_object_storage

    return get_object_storage()


def get_rubric_dep() -> RubricPort:
    from grading.shared.container import get_rubric_store

    return get_rubric_store()


def get_allowed_universidades_dep() -> list[str]:
    from grading.shared.container import get_allowed_universidades

    return get_allowed_universidades()


def build_idempotency_key(payload: dict) -> str:
    raw = "|".join(str(payload[field]) for field in _IDEMPOTENCY_FIELDS)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@router.post(
    "/v1/calificaciones",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=CalificacionAcceptedDTO,
)
def crear_calificacion(
    body: CalificacionRequestDTO,
    queue: QueuePort = Depends(get_queue_dep),
    universidades: list[str] = Depends(get_allowed_universidades_dep),
) -> CalificacionAcceptedDTO:
    if body.id_universidad not in universidades:
        raise HTTPException(
            status_code=400,
            detail=f"Universidad '{body.id_universidad}' no habilitada. Permitidas: {universidades}",
        )

    payload = body.model_dump()
    idempotency_key = build_idempotency_key(payload)
    payload["idempotency_key"] = idempotency_key
    queue.enqueue(message=payload)
    return CalificacionAcceptedDTO(
        correlation_id=uuid.uuid4().hex,
        idempotency_key=idempotency_key,
    )


@router.get(
    "/v1/universidades/{universidad_id}/cursos/{curso_id}"
    "/estudiantes/{estudiante_id}/entregables/{entregable_id}/calificacion"
)
def leer_calificacion(
    universidad_id: str,
    curso_id: str,
    estudiante_id: str,
    entregable_id: str,
    env: str = "prod",
    storage: StoragePort = Depends(get_storage_dep),
) -> dict:
    key = s3_keys.grading_key(
        env=env,
        universidad_id=universidad_id,
        curso_id=curso_id,
        estudiante_id=estudiante_id,
        entregable_id=entregable_id,
    )
    if not storage.exists(key=key):
        raise HTTPException(status_code=404, detail="Calificación no encontrada.")
    return storage.get_json(key=key)


@router.get(
    "/v1/universidades/{universidad_id}/cursos/{curso_id}/actividades/{actividad_id}/rubrica"
)
def leer_rubrica(
    universidad_id: str,
    curso_id: str,
    actividad_id: str,
    rubrica_id: str,
    env: str = "prod",
    rubric_store: RubricPort = Depends(get_rubric_dep),
) -> dict:
    try:
        rubric = rubric_store.load(
            env=env,
            universidad_id=universidad_id,
            curso_id=curso_id,
            actividad_id=actividad_id,
            rubrica_id=rubrica_id,
        )
    except RubricNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return rubric.model_dump()
