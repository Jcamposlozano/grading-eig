from __future__ import annotations

from dataclasses import dataclass

from grading.domain.enums import ClasificacionActividad


@dataclass
class Actividad:
    """Tarea evaluable de un curso. Porta la clasificación y la rúbrica."""

    id: str
    curso_id: str
    clasificacion: ClasificacionActividad
    rubrica_id: str
