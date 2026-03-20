from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from contenidos_inacap.domain.entities.material import MaterialStatus, MaterialType


class ExtractTextResponse(BaseModel):
    material_id: str
    original_filename: str
    media_type: MaterialType
    status: MaterialStatus
    extracted_text: Optional[str]
    error_message: Optional[str]
    created_at: datetime