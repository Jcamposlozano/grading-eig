from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ResultadoCriterio:
    criterio_id: str
    criterio_nombre: str
    nivel_seleccionado: str
    puntos: int
    justificacion: str


@dataclass
class Calificacion:
    """Resultado de calificar un entregable.

    ``publish`` es el gate: si es True (y hay contexto Canvas) se publica la
    nota. ``publicado`` registra si efectivamente se subió a Canvas. El
    equivalente en el borde de la API es ``EvaluationResponseDTO``.
    """

    entregable_id: str
    total_score: int
    publish: bool
    confidence: float
    feedback_general: str
    resultados: list[ResultadoCriterio] = field(default_factory=list)
    publicado: bool = False
