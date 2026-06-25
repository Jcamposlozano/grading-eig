from __future__ import annotations

# Prefijos de rutas v1 deprecadas (siguen funcionando; sucesor: el orquestador).
_DEPRECATED_PREFIXES = ("/v1/materials", "/v1/evaluations")
_SUCCESSOR_LINK = '</v1/calificaciones>; rel="successor-version"'


def is_deprecated_path(path: str) -> bool:
    return path.startswith(_DEPRECATED_PREFIXES)


def mark_response_deprecated(response) -> None:
    """Adjunta los headers de deprecación (RFC 8594) a la respuesta."""
    response.headers["Deprecation"] = "true"
    response.headers["Link"] = _SUCCESSOR_LINK
