from __future__ import annotations

import pytest

from grading.application.strategies.extraction import (
    AudioExtractionStrategy,
    DocumentExtractionStrategy,
    VideoExtractionStrategy,
    build_extraction_registry,
    clasificacion_from_media_type,
)
from grading.domain.entities.material import MaterialType
from grading.domain.enums import ClasificacionActividad


class FakeDoc:
    def extract(self, *, file_path):
        return f"texto:{file_path}"


class FakeTranscriber:
    def transcribe(self, *, audio_path):
        return f"trans:{audio_path}"


class FakeAudioExtractor:
    def __init__(self, out_path):
        self.out_path = out_path
        self.called_with = None

    def extract_audio(self, *, input_path):
        self.called_with = input_path
        return self.out_path


def test_document_strategy():
    strategy = DocumentExtractionStrategy(document_extractor=FakeDoc())
    assert strategy.extract(file_path="/x.docx") == "texto:/x.docx"


def test_audio_strategy():
    strategy = AudioExtractionStrategy(transcriber=FakeTranscriber())
    assert strategy.extract(file_path="/a.m4a") == "trans:/a.m4a"


def test_video_strategy_transcribes_and_cleans_temp(tmp_path):
    temp_audio = tmp_path / "out.wav"
    temp_audio.write_bytes(b"x")
    strategy = VideoExtractionStrategy(
        audio_extractor=FakeAudioExtractor(str(temp_audio)),
        transcriber=FakeTranscriber(),
    )

    result = strategy.extract(file_path="/v.mp4")

    assert result == f"trans:{temp_audio}"
    assert not temp_audio.exists()  # el audio temporal se limpia


def test_video_strategy_cleans_temp_on_failure(tmp_path):
    temp_audio = tmp_path / "out.wav"
    temp_audio.write_bytes(b"x")

    class Boom:
        def transcribe(self, *, audio_path):
            raise RuntimeError("fallo de transcripción")

    strategy = VideoExtractionStrategy(
        audio_extractor=FakeAudioExtractor(str(temp_audio)),
        transcriber=Boom(),
    )

    with pytest.raises(RuntimeError):
        strategy.extract(file_path="/v.mp4")
    assert not temp_audio.exists()


def test_registry_and_mapping():
    registry = build_extraction_registry(
        document_extractor=FakeDoc(),
        transcriber=FakeTranscriber(),
        audio_extractor=FakeAudioExtractor("x"),
    )

    assert set(registry) == {
        ClasificacionActividad.TEXTO,
        ClasificacionActividad.AUDIO,
        ClasificacionActividad.VIDEO,
    }
    assert isinstance(registry[ClasificacionActividad.TEXTO], DocumentExtractionStrategy)
    assert clasificacion_from_media_type(MaterialType.DOCUMENT) is ClasificacionActividad.TEXTO
    assert clasificacion_from_media_type(MaterialType.VIDEO) is ClasificacionActividad.VIDEO
