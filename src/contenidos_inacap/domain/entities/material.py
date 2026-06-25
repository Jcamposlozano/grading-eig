from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


# Se conserva `(str, Enum)` (no `StrEnum`): bajo py311 `StrEnum` cambia el formato
# de `f"{miembro}"` (de "MaterialType.VIDEO" a "video"), lo que alteraría mensajes
# existentes (p. ej. en extract_text.py).
class MaterialType(str, Enum):  # noqa: UP042
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"


class MaterialStatus(str, Enum):  # noqa: UP042
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
    extracted_text: str | None = None
    status: MaterialStatus = MaterialStatus.UPLOADED
    error_message: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
