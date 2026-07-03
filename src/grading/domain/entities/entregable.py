from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from grading.domain.entities.material import MaterialType
from grading.domain.enums import ClasificacionActividad, EstadoEntregable


@dataclass
class Entregable:
    """Lo que entrega un estudiante para una actividad (generaliza ``Material``).

    Es la entidad que recorre el pipeline del orquestador (Paso 7): se descarga
    de Canvas (``raw_key``), se extrae su contenido (``extracted_text``) y se
    califica, avanzando por ``estado``.
    """

    id: str
    universidad_id: str
    curso_id: str
    estudiante_id: str
    actividad_id: str
    clasificacion: ClasificacionActividad
    estado: EstadoEntregable = EstadoEntregable.RECIBIDO
    media_type: MaterialType | None = None
    raw_key: str | None = None
    extracted_text: str | None = None
    error_message: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
