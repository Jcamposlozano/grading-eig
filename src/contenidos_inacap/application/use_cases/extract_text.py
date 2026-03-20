from __future__ import annotations

import os

from contenidos_inacap.domain.entities.material import MaterialStatus, MaterialType
from contenidos_inacap.ports.audio_extractor_port import AudioExtractorPort
from contenidos_inacap.ports.document_extractor_port import DocumentExtractorPort
from contenidos_inacap.ports.material_repository_port import MaterialRepositoryPort
from contenidos_inacap.ports.transcription_port import TranscriptionPort


class MaterialNotFoundError(Exception):
    pass


class UnsupportedExtractionTypeError(Exception):
    pass


class ExtractTextUseCase:
    def __init__(
        self,
        material_repository: MaterialRepositoryPort,
        transcription_service: TranscriptionPort,
        audio_extractor: AudioExtractorPort,
        document_extractor: DocumentExtractorPort,
    ) -> None:
        self.material_repository = material_repository
        self.transcription_service = transcription_service
        self.audio_extractor = audio_extractor
        self.document_extractor = document_extractor

    def execute(self, *, material_id: str):
        material = self.material_repository.get_by_id(material_id)
        if not material:
            raise MaterialNotFoundError(f"No existe material con id={material_id}")

        material.status = MaterialStatus.PROCESSING
        material.error_message = None
        self.material_repository.update(material)

        temp_audio_to_delete: str | None = None

        try:
            if material.media_type == MaterialType.DOCUMENT:
                extracted_text = self.document_extractor.extract(
                    file_path=material.file_path
                )

            elif material.media_type == MaterialType.AUDIO:
                extracted_text = self.transcription_service.transcribe(
                    audio_path=material.file_path
                )

            elif material.media_type == MaterialType.VIDEO:
                temp_audio_to_delete = self.audio_extractor.extract_audio(
                    input_path=material.file_path
                )
                extracted_text = self.transcription_service.transcribe(
                    audio_path=temp_audio_to_delete
                )

            else:
                raise UnsupportedExtractionTypeError(
                    f"El tipo '{material.media_type}' aún no está soportado en este endpoint."
                )

            if not extracted_text.strip():
                raise ValueError("No fue posible extraer texto del archivo.")

            material.extracted_text = extracted_text
            material.status = MaterialStatus.COMPLETED
            material.error_message = None
            self.material_repository.update(material)
            return material

        except Exception as exc:
            material.status = MaterialStatus.FAILED
            material.error_message = str(exc)
            self.material_repository.update(material)
            raise

        finally:
            if temp_audio_to_delete and os.path.exists(temp_audio_to_delete):
                try:
                    os.remove(temp_audio_to_delete)
                except OSError:
                    pass