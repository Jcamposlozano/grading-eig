from __future__ import annotations

from contenidos_inacap.domain.entities.material import MaterialType
from contenidos_inacap.domain.media_type import media_type_from_filename, supported_extensions


def test_detects_by_extension_case_insensitive():
    assert media_type_from_filename("Tarea.PDF") is MaterialType.DOCUMENT
    assert media_type_from_filename("audio.m4a") is MaterialType.AUDIO
    assert media_type_from_filename("video.mp4") is MaterialType.VIDEO
    assert media_type_from_filename("raro.xyz") is None


def test_supported_extensions():
    exts = supported_extensions()
    assert ".pdf" in exts
    assert ".mp4" in exts
    assert ".m4a" in exts
