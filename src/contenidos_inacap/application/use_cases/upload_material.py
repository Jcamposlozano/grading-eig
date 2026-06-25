from __future__ import annotations

import mimetypes
import uuid
from pathlib import Path
from typing import BinaryIO

from contenidos_inacap.domain.entities.material import Material, MaterialStatus, MaterialType
from contenidos_inacap.domain.media_type import media_type_from_filename, supported_extensions
from contenidos_inacap.ports.file_storage_port import FileStoragePort
from contenidos_inacap.ports.material_repository_port import MaterialRepositoryPort


class UnsupportedFileTypeError(Exception):
    pass


class EmptyFileError(Exception):
    pass


class UploadMaterialUseCase:
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
        declared_media_type: str | None = None,
    ) -> Material:
        if not original_filename:
            raise UnsupportedFileTypeError("El archivo debe tener un nombre válido.")

        media_type = self._resolve_media_type(
            original_filename=original_filename,
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
        original_filename: str,
        declared_media_type: str | None,
    ) -> MaterialType:
        if declared_media_type:
            try:
                return MaterialType(declared_media_type)
            except ValueError as exc:
                raise UnsupportedFileTypeError(
                    f"Tipo declarado no soportado: {declared_media_type}"
                ) from exc

        media_type = media_type_from_filename(original_filename)
        if media_type is None:
            extension = Path(original_filename).suffix.lower()
            raise UnsupportedFileTypeError(
                f"No se soporta la extensión '{extension}'. Permitidos: {supported_extensions()}"
            )
        return media_type
