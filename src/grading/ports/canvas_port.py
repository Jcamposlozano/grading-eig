from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class AttachmentRef:
    """Referencia a un archivo adjunto de una entrega en Canvas."""

    file_id: str
    filename: str | None = None
    download_url: str | None = None


class CanvasPort(ABC):
    """Operaciones contra el Canvas de una universidad concreta.

    Cada instancia trabaja contra un ``base_url`` + ``token`` ya resueltos (ver
    ``CanvasAdapter`` / ``CanvasAdapterFactory``); el puerto no conoce nada de
    multi-tenant ni de cómo se obtuvieron las credenciales.
    """

    @abstractmethod
    def fetch_submission_attachment(
        self,
        *,
        course_id: str,
        assignment_id: str,
        user_id: str,
        attachment_index: int = 0,
    ) -> AttachmentRef:
        """Resuelve el adjunto ``attachment_index`` de la entrega del usuario."""
        raise NotImplementedError

    @abstractmethod
    def download_file(self, *, attachment: AttachmentRef) -> tuple[bytes, str]:
        """Descarga el binario del adjunto. Retorna ``(bytes, filename)``."""
        raise NotImplementedError

    @abstractmethod
    def publish_grade(
        self,
        *,
        course_id: str,
        assignment_id: str,
        user_id: str,
        score: int | float,
        comment: str,
    ) -> None:
        """Publica nota + comentario en la entrega del usuario."""
        raise NotImplementedError
