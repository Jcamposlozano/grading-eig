from __future__ import annotations

from dataclasses import dataclass


@dataclass
class NivelRubrica:
    nivel: str
    puntos: int
    descripcion: str


@dataclass
class CriterioRubrica:
    id: str
    nombre: str
    niveles: list[NivelRubrica]


@dataclass
class Rubrica:
    """Modelo de dominio de la rúbrica (framework-free).

    El equivalente en el borde de la API es ``RubricDTO`` (pydantic). El mapeo
    entre ambos se hará en el orquestador (Paso 7).
    """

    id: str
    max_score: int
    criterios: list[CriterioRubrica]
