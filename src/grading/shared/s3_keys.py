"""Construcción canónica de claves del bucket ``prisma-calificacion-canvas``.

Centraliza el layout por jerarquía descrito en docs/PLAN_ESCALABILIDAD.md para
que la rúbrica (Paso 3) y, más adelante, el orquestador (raw/extracted/grading)
compartan exactamente las mismas claves.
"""

from __future__ import annotations


def rubrica_key(
    *,
    env: str,
    universidad_id: str,
    curso_id: str,
    actividad_id: str,
    rubrica_id: str,
) -> str:
    """Rúbrica a nivel actividad (compartida entre estudiantes)."""
    return f"{env}/{universidad_id}/{curso_id}/actividades/{actividad_id}/rubrica/{rubrica_id}.json"


def entregable_prefix(
    *,
    env: str,
    universidad_id: str,
    curso_id: str,
    estudiante_id: str,
    entregable_id: str,
) -> str:
    return f"{env}/{universidad_id}/{curso_id}/{estudiante_id}/{entregable_id}"


def raw_key(*, filename: str, **hierarchy: str) -> str:
    """Entregable crudo descargado de Canvas."""
    return f"{entregable_prefix(**hierarchy)}/raw/{filename}"


def extracted_text_key(**hierarchy: str) -> str:
    """Texto extraído / transcripción."""
    return f"{entregable_prefix(**hierarchy)}/extracted/extracted.txt"


def grading_key(**hierarchy: str) -> str:
    """Resultado de la calificación."""
    return f"{entregable_prefix(**hierarchy)}/grading/calificacion.json"


def metadata_key(**hierarchy: str) -> str:
    """Trazabilidad del procesamiento."""
    return f"{entregable_prefix(**hierarchy)}/grading/metadata.json"
