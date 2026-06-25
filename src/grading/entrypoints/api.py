from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from grading.entrypoints.deprecation import is_deprecated_path, mark_response_deprecated
from grading.entrypoints.routers.calificaciones_router import (
    router as calificaciones_router,
)
from grading.entrypoints.routers.evaluations_router import (
    router as evaluations_router,
)
from grading.entrypoints.routers.materials_router import (
    router as materials_router,
)
from grading.shared.config import load_config

cfg = load_config()
SERVICE_NAME = cfg.get("project", {}).get("name", "content-grading-service")

app = FastAPI(title=SERVICE_NAME, version="0.1.0")

# CORS
origins = [
    "http://localhost:4200",
    "http://127.0.0.1:4200",
    "https://d1l01nx5bjijft.cloudfront.net",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_deprecation_headers(request: Request, call_next):
    """Header Deprecation/Link en TODAS las respuestas de rutas v1 (incl. errores)."""
    response = await call_next(request)
    if is_deprecated_path(request.url.path):
        mark_response_deprecated(response)
    return response


# routers
# v1 (materials, evaluations): DEPRECADAS — siguen funcionando, pero el flujo nuevo
# es POST /v1/calificaciones (orquestador). Se marcan en OpenAPI (deprecated=True) y
# con header Deprecation/Link en runtime. No se eliminan por ahora.
app.include_router(materials_router, deprecated=True)
app.include_router(evaluations_router, deprecated=True)
app.include_router(calificaciones_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME}


@app.get("/health/ready")
def ready():
    return {"status": "ready", "service": SERVICE_NAME}
