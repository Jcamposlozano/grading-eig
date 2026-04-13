from __future__ import annotations

from contenidos_inacap.adapters.extractors.document_text_extractor import DocumentTextExtractor
from contenidos_inacap.adapters.media.ffmpeg_audio_extractor import FFmpegAudioExtractor
from contenidos_inacap.adapters.repositories.in_memory_material_repository import (
    InMemoryMaterialRepository,
)
from contenidos_inacap.adapters.storage.local_file_storage import LocalFileStorage
from contenidos_inacap.adapters.transcription.openai_transcriber import OpenAITranscriber
from contenidos_inacap.application.use_cases.extract_text import ExtractTextUseCase
from contenidos_inacap.application.use_cases.import_material_from_canvas import (
    ImportMaterialFromCanvasUseCase,
)
from contenidos_inacap.application.use_cases.upload_material import UploadMaterialUseCase
from contenidos_inacap.shared.config import load_config

from contenidos_inacap.adapters.llm.openai_evaluator import OpenAIEvaluator
from contenidos_inacap.application.use_cases.evaluate_student_response import (
    EvaluateStudentResponseUseCase,
)

load_config()

_material_repository = InMemoryMaterialRepository()
_file_storage = LocalFileStorage(base_dir="data/uploads")
_audio_extractor = FFmpegAudioExtractor(temp_dir="data/temp")
_document_extractor = DocumentTextExtractor()


def get_upload_material_use_case() -> UploadMaterialUseCase:
    return UploadMaterialUseCase(
        material_repository=_material_repository,
        file_storage=_file_storage,
    )


def get_import_material_from_canvas_use_case() -> ImportMaterialFromCanvasUseCase:
    return ImportMaterialFromCanvasUseCase(
        upload_material=get_upload_material_use_case(),
    )


def get_extract_text_use_case() -> ExtractTextUseCase:
    transcriber = OpenAITranscriber()
    return ExtractTextUseCase(
        material_repository=_material_repository,
        transcription_service=transcriber,
        audio_extractor=_audio_extractor,
        document_extractor=_document_extractor,
    )

def get_evaluate_student_response_use_case() -> EvaluateStudentResponseUseCase:
    evaluator = OpenAIEvaluator()
    return EvaluateStudentResponseUseCase(
        llm_evaluator=evaluator,
        material_repository=_material_repository,
    )