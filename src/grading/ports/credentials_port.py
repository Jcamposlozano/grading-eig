from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class CredentialsResolutionError(Exception):
    """No se pudieron resolver las credenciales de Canvas para una universidad."""


@dataclass(frozen=True)
class CanvasCredentials:
    """Credenciales de un Canvas concreto (una universidad)."""

    base_url: str
    token: str


class CredentialsPort(ABC):
    """Resuelve las credenciales de Canvas por universidad y entorno.

    Permite multi-tenant: cada universidad tiene su propio Canvas (dominio + token).
    Agregar una universidad nueva debe ser solo configuración/secreto, no código.
    """

    @abstractmethod
    def get_canvas_credentials(self, *, universidad_id: str, env: str) -> CanvasCredentials:
        """Retorna las credenciales de Canvas para ``universidad_id`` en ``env``.

        Lanza ``CredentialsResolutionError`` si no existen o están incompletas.
        """
        raise NotImplementedError
