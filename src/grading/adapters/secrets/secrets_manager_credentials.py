from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any

from grading.ports.credentials_port import (
    CanvasCredentials,
    CredentialsPort,
    CredentialsResolutionError,
)

_BASE_URL_KEYS = ("base_url", "domain", "url")
_TOKEN_KEYS = ("token", "access_token", "key", "key-canvas")


class SecretsManagerCredentials(CredentialsPort):
    """Resuelve credenciales de Canvas por universidad desde AWS Secrets Manager.

    Convención de nombre del secreto: ``{secret_prefix}/{env}/canvas/{universidad}``
    (p. ej. ``prisma/grading/prod/canvas/eig``). El secreto es un JSON con
    ``base_url`` y ``token`` (se aceptan alias). Se cachea en memoria con TTL para
    no llamar a Secrets Manager en cada petición.
    """

    def __init__(
        self,
        *,
        secret_prefix: str = "prisma/grading",
        region: str | None = None,
        cache_ttl_seconds: float = 300.0,
        client: Any = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.secret_prefix = secret_prefix.strip("/")
        self.cache_ttl_seconds = cache_ttl_seconds
        self._clock = clock
        self._cache: dict[str, tuple[CanvasCredentials, float]] = {}
        if client is None:
            import boto3

            client = boto3.client("secretsmanager", region_name=region)
        self._client = client

    def secret_name(self, *, universidad_id: str, env: str) -> str:
        return f"{self.secret_prefix}/{env}/canvas/{universidad_id}"

    def get_canvas_credentials(self, *, universidad_id: str, env: str) -> CanvasCredentials:
        name = self.secret_name(universidad_id=universidad_id, env=env)

        cached = self._cache.get(name)
        if cached is not None and self._clock() < cached[1]:
            return cached[0]

        credentials = self._fetch(name)
        self._cache[name] = (credentials, self._clock() + self.cache_ttl_seconds)
        return credentials

    def _fetch(self, name: str) -> CanvasCredentials:
        try:
            response = self._client.get_secret_value(SecretId=name)
        except Exception as exc:  # ClientError (ResourceNotFound, AccessDenied, ...)
            raise CredentialsResolutionError(
                f"No se pudo leer el secreto de Canvas '{name}': {exc}"
            ) from exc

        raw = response.get("SecretString")
        if not raw:
            raise CredentialsResolutionError(f"El secreto '{name}' no tiene SecretString.")

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise CredentialsResolutionError(f"El secreto '{name}' no es un JSON válido.") from exc

        base_url = _first(payload, _BASE_URL_KEYS)
        token = _first(payload, _TOKEN_KEYS)
        if not base_url or not token:
            raise CredentialsResolutionError(
                f"El secreto '{name}' debe incluir base_url/domain y token."
            )

        return CanvasCredentials(base_url=base_url.strip().rstrip("/"), token=token.strip())


def _first(payload: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None
