from __future__ import annotations

from contenidos_inacap.adapters.canvas.canvas_adapter import CanvasAdapterFactory
from contenidos_inacap.adapters.extractors.document_text_extractor import DocumentTextExtractor
from contenidos_inacap.adapters.llm.openai_evaluator import OpenAIEvaluator
from contenidos_inacap.adapters.media.ffmpeg_audio_extractor import FFmpegAudioExtractor
from contenidos_inacap.adapters.repositories.in_memory_material_repository import (
    InMemoryMaterialRepository,
)
from contenidos_inacap.adapters.rubric.s3_rubric_store import S3RubricStore
from contenidos_inacap.adapters.storage.local_file_storage import LocalFileStorage
from contenidos_inacap.adapters.storage.local_object_storage import LocalObjectStorage
from contenidos_inacap.adapters.transcription.openai_transcriber import OpenAITranscriber
from contenidos_inacap.application.strategies.extraction import build_extraction_registry
from contenidos_inacap.application.use_cases.evaluate_student_response import (
    EvaluateStudentResponseUseCase,
)
from contenidos_inacap.application.use_cases.extract_text import ExtractTextUseCase
from contenidos_inacap.application.use_cases.import_material_from_canvas import (
    ImportMaterialFromCanvasUseCase,
)
from contenidos_inacap.application.use_cases.upload_material import UploadMaterialUseCase
from contenidos_inacap.ports.credentials_port import CredentialsPort
from contenidos_inacap.ports.queue_port import QueuePort
from contenidos_inacap.ports.rubric_port import RubricPort
from contenidos_inacap.ports.storage_port import StoragePort
from contenidos_inacap.shared.config import load_config

_config = load_config()

_material_repository = InMemoryMaterialRepository()
_file_storage = LocalFileStorage(base_dir="data/uploads")
_audio_extractor = FFmpegAudioExtractor(temp_dir="data/temp")
_document_extractor = DocumentTextExtractor()


def _build_object_storage() -> StoragePort:
    storage_cfg = _config.get("storage", {})
    backend = storage_cfg.get("backend", "local")
    if backend == "s3":
        # Import diferido: boto3 solo es necesario con el backend S3.
        from contenidos_inacap.adapters.storage.s3_storage import S3Storage

        return S3Storage(
            bucket=storage_cfg["s3_bucket"],
            region=storage_cfg.get("region"),
        )
    return LocalObjectStorage(base_dir=storage_cfg.get("local_base_dir", "data/objects"))


_object_storage = _build_object_storage()
_rubric_store = S3RubricStore(storage=_object_storage)


def get_rubric_store() -> RubricPort:
    return _rubric_store


def _build_credentials() -> CredentialsPort:
    cred_cfg = _config.get("credentials", {})
    backend = cred_cfg.get("backend", "env")
    if backend == "secrets_manager":
        # Import diferido: boto3 solo es necesario con Secrets Manager.
        from contenidos_inacap.adapters.secrets.secrets_manager_credentials import (
            SecretsManagerCredentials,
        )

        return SecretsManagerCredentials(
            secret_prefix=cred_cfg.get("secret_prefix", "prisma/grading"),
            region=_config.get("storage", {}).get("region"),
        )

    from contenidos_inacap.adapters.secrets.env_credentials import EnvCredentials

    return EnvCredentials()


_credentials = _build_credentials()
_canvas_adapter_factory = CanvasAdapterFactory(_credentials)


def _build_queue() -> QueuePort:
    queue_cfg = _config.get("queue", {})
    backend = queue_cfg.get("backend", "memory")
    if backend == "sqs":
        # Import diferido: boto3 solo es necesario con SQS.
        from contenidos_inacap.adapters.queue.sqs_queue import SqsQueue

        return SqsQueue(
            queue_url=queue_cfg["url"],
            region=_config.get("storage", {}).get("region"),
        )

    from contenidos_inacap.adapters.queue.in_memory_queue import InMemoryQueue

    return InMemoryQueue()


_queue = _build_queue()


def get_queue() -> QueuePort:
    return _queue


def get_credentials() -> CredentialsPort:
    return _credentials


def get_canvas_adapter_factory() -> CanvasAdapterFactory:
    return _canvas_adapter_factory


def get_object_storage() -> StoragePort:
    return _object_storage


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
    registry = build_extraction_registry(
        document_extractor=_document_extractor,
        transcriber=transcriber,
        audio_extractor=_audio_extractor,
    )
    return ExtractTextUseCase(
        material_repository=_material_repository,
        extraction_registry=registry,
    )


def get_evaluate_student_response_use_case() -> EvaluateStudentResponseUseCase:
    evaluator = OpenAIEvaluator()
    return EvaluateStudentResponseUseCase(
        llm_evaluator=evaluator,
        material_repository=_material_repository,
    )
