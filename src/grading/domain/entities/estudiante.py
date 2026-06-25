from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Estudiante:
    id: str
    universidad_id: str
    canvas_user_id: str
