from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Curso:
    id: str
    universidad_id: str
    nombre: str
