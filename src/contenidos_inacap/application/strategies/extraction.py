"""Estrategias de extracción de contenido, seleccionadas por clasificación.

Reemplaza el ``if/elif`` por ``media_type`` que vivía en ``extract_text.py``:
la clasificación de la actividad decide la estrategia (texto → leer directo;
audio → transcribir; video → extraer audio → transcribir).
"""

from __future__ import annotations

import contextlib
import os
from abc import ABC, abstractmethod

from contenidos_inacap.domain.entities.material import MaterialType
from contenidos_inacap.domain.enums import ClasificacionActividad
from contenidos_inacap.ports.audio_extractor_port import AudioExtractorPort
from contenidos_inacap.ports.document_extractor_port import DocumentExtractorPort
from contenidos_inacap.ports.transcription_port import TranscriptionPort


class ExtractionStrategy(ABC):
    @abstractmethod
    def extract(self, *, file_path: str) -> str:
        """Extrae el texto del archivo en ``file_path``."""
        raise NotImplementedError


class DocumentExtractionStrategy(ExtractionStrategy):
    def __init__(self, *, document_extractor: DocumentExtractorPort) -> None:
        self._document_extractor = document_extractor

    def extract(self, *, file_path: str) -> str:
        return self._document_extractor.extract(file_path=file_path)


class AudioExtractionStrategy(ExtractionStrategy):
    def __init__(self, *, transcriber: TranscriptionPort) -> None:
        self._transcriber = transcriber

    def extract(self, *, file_path: str) -> str:
        return self._transcriber.transcribe(audio_path=file_path)


class VideoExtractionStrategy(ExtractionStrategy):
    def __init__(
        self,
        *,
        audio_extractor: AudioExtractorPort,
        transcriber: TranscriptionPort,
    ) -> None:
        self._audio_extractor = audio_extractor
        self._transcriber = transcriber

    def extract(self, *, file_path: str) -> str:
        audio_path = self._audio_extractor.extract_audio(input_path=file_path)
        try:
            return self._transcriber.transcribe(audio_path=audio_path)
        finally:
            if audio_path and os.path.exists(audio_path):
                with contextlib.suppress(OSError):
                    os.remove(audio_path)


_MEDIA_TYPE_TO_CLASIFICACION: dict[MaterialType, ClasificacionActividad] = {
    MaterialType.DOCUMENT: ClasificacionActividad.TEXTO,
    MaterialType.AUDIO: ClasificacionActividad.AUDIO,
    MaterialType.VIDEO: ClasificacionActividad.VIDEO,
}


def clasificacion_from_media_type(media_type: MaterialType) -> ClasificacionActividad:
    """Mapea el ``MaterialType`` de un Material a la clasificación de actividad."""
    return _MEDIA_TYPE_TO_CLASIFICACION[media_type]


def build_extraction_registry(
    *,
    document_extractor: DocumentExtractorPort,
    transcriber: TranscriptionPort,
    audio_extractor: AudioExtractorPort,
) -> dict[ClasificacionActividad, ExtractionStrategy]:
    return {
        ClasificacionActividad.TEXTO: DocumentExtractionStrategy(
            document_extractor=document_extractor
        ),
        ClasificacionActividad.AUDIO: AudioExtractionStrategy(transcriber=transcriber),
        ClasificacionActividad.VIDEO: VideoExtractionStrategy(
            audio_extractor=audio_extractor, transcriber=transcriber
        ),
    }
