from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class MaterialType(str, Enum):
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"


class MaterialStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Material:
    id: str
    filename: str
    original_filename: str
    media_type: MaterialType
    mime_type: str
    file_path: str
    file_size: int
    extracted_text: Optional[str] = None
    status: MaterialStatus = MaterialStatus.UPLOADED
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))