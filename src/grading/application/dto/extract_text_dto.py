from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from grading.domain.entities.material import MaterialStatus, MaterialType


class ExtractTextResponse(BaseModel):
    material_id: str
    original_filename: str
    media_type: MaterialType
    status: MaterialStatus
    extracted_text: str | None
    error_message: str | None
    created_at: datetime
