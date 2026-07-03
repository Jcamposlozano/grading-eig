"""Detección de tipo de material por extensión (fuente única de la verdad).

La usan tanto el flujo v1 de subida (``UploadMaterialUseCase``) como el
orquestador (``CalificarEntregable``), para no duplicar las listas de extensiones.
"""

from __future__ import annotations

from pathlib import Path

from grading.domain.entities.material import MaterialType

DOCUMENT_EXTENSIONS = frozenset({".txt", ".pdf", ".docx"})
AUDIO_EXTENSIONS = frozenset({".mp3", ".wav", ".m4a", ".ogg", ".webm"})
VIDEO_EXTENSIONS = frozenset({".mp4", ".mov", ".mkv", ".avi", ".webm"})


def media_type_from_filename(filename: str) -> MaterialType | None:
    """Retorna el ``MaterialType`` según la extensión, o None si no se soporta."""
    extension = Path(filename).suffix.lower()
    if extension in DOCUMENT_EXTENSIONS:
        return MaterialType.DOCUMENT
    if extension in AUDIO_EXTENSIONS:
        return MaterialType.AUDIO
    if extension in VIDEO_EXTENSIONS:
        return MaterialType.VIDEO
    return None


def supported_extensions() -> list[str]:
    return sorted(DOCUMENT_EXTENSIONS | AUDIO_EXTENSIONS | VIDEO_EXTENSIONS)
