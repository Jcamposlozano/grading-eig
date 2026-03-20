from __future__ import annotations

import mimetypes
import uuid
from pathlib import Path
from typing import BinaryIO, Optional

from contenidos_inacap.domain.entities.material import Material, MaterialStatus, MaterialType
from contenidos_inacap.ports.file_storage_port import FileStoragePort
from contenidos_inacap.ports.material_repository_port import MaterialRepositoryPort


class UnsupportedFileTypeError(Exception):
    pass


class EmptyFileError(Exception):
    pass


class UploadMaterialUseCase:
    DOCUMENT_EXTENSIONS = {".txt", ".pdf", ".docx"}
    AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".webm"}
    VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm"}

    def __init__(
        self,
        material_repository: MaterialRepositoryPort,
        file_storage: FileStoragePort,
    ) -> None:
        self.material_repository = material_repository
        self.file_storage = file_storage

    def execute(
        self,
        *,
        file_stream: BinaryIO,
        original_filename: str,
        declared_media_type: Optional[str] = None,
    ) -> Material:
        if not original_filename:
            raise UnsupportedFileTypeError("El archivo debe tener un nombre válido.")

        extension = Path(original_filename).suffix.lower()

        media_type = self._resolve_media_type(
            extension=extension,
            declared_media_type=declared_media_type,
        )

        stored_filename, absolute_path, file_size = self.file_storage.save_file(
            file_stream=file_stream,
            original_filename=original_filename,
            target_subdir=media_type.value,
        )

        if file_size == 0:
            raise EmptyFileError("El archivo está vacío.")

        mime_type, _ = mimetypes.guess_type(original_filename)
        mime_type = mime_type or "application/octet-stream"

        material = Material(
            id=uuid.uuid4().hex,
            filename=stored_filename,
            original_filename=original_filename,
            media_type=media_type,
            mime_type=mime_type,
            file_path=absolute_path,
            file_size=file_size,
            status=MaterialStatus.UPLOADED,
        )

        return self.material_repository.save(material)

    def _resolve_media_type(
        self,
        *,
        extension: str,
        declared_media_type: Optional[str],
    ) -> MaterialType:
        if declared_media_type:
            try:
                return MaterialType(declared_media_type)
            except ValueError as exc:
                raise UnsupportedFileTypeError(
                    f"Tipo declarado no soportado: {declared_media_type}"
                ) from exc

        if extension in self.DOCUMENT_EXTENSIONS:
            return MaterialType.DOCUMENT
        if extension in self.AUDIO_EXTENSIONS:
            return MaterialType.AUDIO
        if extension in self.VIDEO_EXTENSIONS:
            return MaterialType.VIDEO

        raise UnsupportedFileTypeError(
            f"No se soporta la extensión '{extension}'. "
            f"Permitidos: {sorted(self.DOCUMENT_EXTENSIONS | self.AUDIO_EXTENSIONS | self.VIDEO_EXTENSIONS)}"
        )