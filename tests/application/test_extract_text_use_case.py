from __future__ import annotations

import pytest

from grading.application.strategies.extraction import ExtractionStrategy
from grading.application.use_cases.extract_text import (
    ExtractTextUseCase,
    UnsupportedExtractionTypeError,
)
from grading.domain.entities.material import Material, MaterialStatus, MaterialType
from grading.domain.enums import ClasificacionActividad


def _material(media_type: MaterialType = MaterialType.DOCUMENT) -> Material:
    return Material(
        id="m1",
        filename="f",
        original_filename="f",
        media_type=media_type,
        mime_type="text/plain",
        file_path="/x",
        file_size=1,
    )


class FakeRepo:
    def __init__(self, material: Material) -> None:
        self.material = material

    def get_by_id(self, material_id: str):
        return self.material if material_id == self.material.id else None

    def update(self, material: Material) -> None:
        pass


class StubStrategy(ExtractionStrategy):
    def __init__(self, text: str) -> None:
        self._text = text

    def extract(self, *, file_path: str) -> str:
        return self._text


def _registry(strategy: ExtractionStrategy):
    return {ClasificacionActividad.TEXTO: strategy}


def test_extracts_and_completes():
    material = _material()
    use_case = ExtractTextUseCase(FakeRepo(material), _registry(StubStrategy("hola mundo")))

    result = use_case.execute(material_id="m1")

    assert result.extracted_text == "hola mundo"
    assert result.status is MaterialStatus.COMPLETED


def test_empty_text_marks_failed():
    material = _material()
    use_case = ExtractTextUseCase(FakeRepo(material), _registry(StubStrategy("   ")))

    with pytest.raises(ValueError):
        use_case.execute(material_id="m1")
    assert material.status is MaterialStatus.FAILED


def test_missing_strategy_is_unsupported():
    material = _material(MaterialType.AUDIO)  # el registry solo trae TEXTO
    use_case = ExtractTextUseCase(FakeRepo(material), _registry(StubStrategy("x")))

    with pytest.raises(UnsupportedExtractionTypeError):
        use_case.execute(material_id="m1")
    assert material.status is MaterialStatus.FAILED
