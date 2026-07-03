from __future__ import annotations

from grading.adapters.canvas.canvas_adapter import CanvasAdapterFactory
from grading.adapters.extractors.document_text_extractor import DocumentTextExtractor
from grading.adapters.llm.openai_evaluator import OpenAIEvaluator
from grading.adapters.media.ffmpeg_audio_extractor import FFmpegAudioExtractor
from grading.adapters.repositories.in_memory_material_repository import (
    InMemoryMaterialRepository,
)
from grading.adapters.rubric.s3_rubric_store import S3RubricStore
from grading.adapters.storage.local_file_storage import LocalFileStorage
from grading.adapters.storage.local_object_storage import LocalObjectStorage
from grading.adapters.transcription.openai_transcriber import OpenAITranscriber
from grading.application.services.rubric_grader import RubricGrader
from grading.application.strategies.extraction import build_extraction_registry
from grading.application.use_cases.calificar_entregable import (
    CalificarEntregable,
    CalificarEntregableCommand,
)
from grading.application.use_cases.evaluate_student_response import (
    EvaluateStudentResponseUseCase,
)
from grading.application.use_cases.extract_text import ExtractTextUseCase
from grading.application.use_cases.import_material_from_canvas import (
    ImportMaterialFromCanvasUseCase,
)
from grading.application.use_cases.upload_material import UploadMaterialUseCase
from grading.ports.credentials_port import CredentialsPort
from grading.ports.queue_port import QueuePort
from grading.ports.rubric_port import RubricPort
from grading.ports.storage_port import StoragePort
from grading.shared.config import load_config

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
        from grading.adapters.storage.s3_storage import S3Storage

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
        from grading.adapters.secrets.secrets_manager_credentials import (
            SecretsManagerCredentials,
        )

        return SecretsManagerCredentials(
            secret_prefix=cred_cfg.get("secret_prefix", "prisma/grading"),
            region=_config.get("storage", {}).get("region"),
        )

    from grading.adapters.secrets.env_credentials import EnvCredentials

    return EnvCredentials()


_credentials = _build_credentials()
_canvas_adapter_factory = CanvasAdapterFactory(_credentials)


def _build_queue() -> QueuePort:
    queue_cfg = _config.get("queue", {})
    backend = queue_cfg.get("backend", "memory")
    if backend == "sqs":
        # Import diferido: boto3 solo es necesario con SQS.
        from grading.adapters.queue.sqs_queue import SqsQueue

        return SqsQueue(
            queue_url=queue_cfg["url"],
            region=_config.get("storage", {}).get("region"),
        )

    from grading.adapters.queue.in_memory_queue import InMemoryQueue

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


def get_allowed_universidades() -> list[str]:
    return list(_config.get("universidades", {}).get("permitidas", []))


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


def get_calificar_entregable_use_case() -> CalificarEntregable:
    transcriber = OpenAITranscriber()
    registry = build_extraction_registry(
        document_extractor=_document_extractor,
        transcriber=transcriber,
        audio_extractor=_audio_extractor,
    )
    return CalificarEntregable(
        canvas_factory=_canvas_adapter_factory,
        storage=_object_storage,
        rubric_store=_rubric_store,
        extraction_registry=registry,
        grader=RubricGrader(OpenAIEvaluator()),
    )


def get_message_handler():
    """Handler que el worker invoca por cada mensaje de la cola."""
    use_case = get_calificar_entregable_use_case()

    def handle(body: dict) -> None:
        command = CalificarEntregableCommand(
            id_universidad=body["id_universidad"],
            id_curso=body["id_curso"],
            id_actividad=body["id_actividad"],
            id_entregable=body["id_entregable"],
            id_estudiante=body["id_estudiante"],
            id_rubrica=body["id_rubrica"],
            env=body["env"],
        )
        use_case.execute(command)

    return handle
