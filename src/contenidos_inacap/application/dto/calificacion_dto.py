from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

_ALLOWED_ENVS = {"dev", "staging", "prod"}


class CalificacionRequestDTO(BaseModel):
    """Payload del trigger externo (ver docs/PLAN_ESCALABILIDAD.md §4)."""

    id_universidad: str = Field(..., min_length=1)
    id_curso: str = Field(..., min_length=1)
    id_actividad: str = Field(..., min_length=1)
    id_entregable: str = Field(..., min_length=1)
    id_estudiante: str = Field(..., min_length=1)
    id_rubrica: str = Field(..., min_length=1)
    env: str = Field(..., min_length=1)

    @field_validator("id_universidad")
    @classmethod
    def _normalize_universidad(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("env")
    @classmethod
    def _check_env(cls, value: str) -> str:
        env = value.strip().lower()
        if env not in _ALLOWED_ENVS:
            raise ValueError(f"env debe ser uno de {sorted(_ALLOWED_ENVS)}")
        return env


class CalificacionAcceptedDTO(BaseModel):
    status: str = "accepted"
    correlation_id: str
    idempotency_key: str
