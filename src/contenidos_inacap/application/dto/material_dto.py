from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from contenidos_inacap.domain.entities.material import MaterialStatus, MaterialType


class UploadMaterialResponse(BaseModel):
    material_id: str = Field(..., description="Identificador único del material")
    original_filename: str
    stored_filename: str
    media_type: MaterialType
    mime_type: str
    file_size: int
    status: MaterialStatus
    created_at: datetime


class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None