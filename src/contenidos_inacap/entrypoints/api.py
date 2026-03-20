from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from contenidos_inacap.entrypoints.routers.evaluations_router import (
    router as evaluations_router,
)
from contenidos_inacap.entrypoints.routers.materials_router import (
    router as materials_router,
)
from contenidos_inacap.shared.config import load_config

cfg = load_config()
SERVICE_NAME = cfg.get("project", {}).get("name", "content-grading-service")

app = FastAPI(title=SERVICE_NAME, version="0.1.0")


# CORS
origins = [
    "http://localhost:4200",
    "http://127.0.0.1:4200",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# routers
app.include_router(materials_router)
app.include_router(evaluations_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": SERVICE_NAME}