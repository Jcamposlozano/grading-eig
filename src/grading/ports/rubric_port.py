from __future__ import annotations

from abc import ABC, abstractmethod

from grading.application.dto.evaluation_dto import RubricDTO


class RubricNotFoundError(Exception):
    """No existe la rúbrica solicitada en el almacenamiento."""


class RubricPort(ABC):
    """Resuelve una rúbrica por su id dentro de la jerarquía multi-tenant."""

    @abstractmethod
    def load(
        self,
        *,
        env: str,
        universidad_id: str,
        curso_id: str,
        actividad_id: str,
        rubrica_id: str,
    ) -> RubricDTO:
        """Carga y valida la rúbrica. Lanza ``RubricNotFoundError`` si no existe."""
        raise NotImplementedError
