from __future__ import annotations

import os

from contenidos_inacap.ports.credentials_port import (
    CanvasCredentials,
    CredentialsPort,
    CredentialsResolutionError,
)


class EnvCredentials(CredentialsPort):
    """Fallback single-tenant: lee un único Canvas desde variables de entorno.

    Útil en desarrollo y durante la migración (antes de tener un secreto por
    universidad en Secrets Manager). Ignora ``universidad_id``/``env`` y devuelve
    siempre las credenciales globales ``CANVAS_BASE_URL`` / ``CANVAS_ACCESS_TOKEN``.
    """

    def get_canvas_credentials(self, *, universidad_id: str, env: str) -> CanvasCredentials:
        base_url = (os.getenv("CANVAS_BASE_URL") or "").strip().rstrip("/")
        token = (os.getenv("CANVAS_ACCESS_TOKEN") or "").strip()
        if not base_url or not token:
            raise CredentialsResolutionError(
                "Defina CANVAS_BASE_URL y CANVAS_ACCESS_TOKEN en el entorno "
                "(backend de credenciales 'env')."
            )
        return CanvasCredentials(base_url=base_url, token=token)
