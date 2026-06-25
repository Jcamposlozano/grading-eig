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
