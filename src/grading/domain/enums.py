from __future__ import annotations

from enum import Enum


# Se usa `(str, Enum)` (no `StrEnum`) por consistencia con MaterialType: bajo
# py311 `StrEnum` cambia el formato de `f"{miembro}"`. Ver material.py.
class ClasificacionActividad(str, Enum):  # noqa: UP042
    """Clasificación de una actividad; decide la estrategia de extracción."""

    TEXTO = "texto"
    AUDIO = "audio"
    VIDEO = "video"


class EstadoEntregable(str, Enum):  # noqa: UP042
    """Estados por los que pasa un entregable en el pipeline de calificación."""

    RECIBIDO = "recibido"
    DESCARGADO = "descargado"
    EXTRAIDO = "extraido"
    CALIFICADO = "calificado"
    PUBLICADO = "publicado"
    FALLIDO = "fallido"
