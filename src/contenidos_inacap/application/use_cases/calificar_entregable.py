from __future__ import annotations

import contextlib
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from contenidos_inacap.adapters.canvas.canvas_adapter import CanvasAdapterFactory
from contenidos_inacap.application.dto.evaluation_dto import EvaluationResponseDTO
from contenidos_inacap.application.services.feedback import build_grade_comment
from contenidos_inacap.application.services.rubric_grader import RubricGrader
from contenidos_inacap.application.strategies.extraction import (
    ExtractionStrategy,
    clasificacion_from_media_type,
)
from contenidos_inacap.domain.enums import ClasificacionActividad
from contenidos_inacap.domain.media_type import media_type_from_filename, supported_extensions
from contenidos_inacap.ports.rubric_port import RubricPort
from contenidos_inacap.ports.storage_port import StoragePort
from contenidos_inacap.shared import s3_keys
from contenidos_inacap.shared.logger import get_logger

log = get_logger("contenidos_inacap.calificar")


class TipoEntregableNoSoportadoError(Exception):
    pass


@dataclass(frozen=True)
class CalificarEntregableCommand:
    id_universidad: str
    id_curso: str
    id_actividad: str
    id_entregable: str
    id_estudiante: str
    id_rubrica: str
    env: str


class CalificarEntregable:
    """Orquestador (Paso 7): del trigger a la nota publicada en Canvas.

    idempotencia -> resolver Canvas -> descargar a raw/ -> extraer a extracted/
    -> cargar rúbrica -> calificar -> escribir grading/ -> publicar si publish=True.

    Supuesto (a confirmar): ``id_curso``/``id_actividad``/``id_estudiante`` son los
    ids de Canvas (course/assignment/user). Si en algún tenant difieren, el mapeo
    se haría aquí (p. ej. vía la entidad Estudiante).
    """

    def __init__(
        self,
        *,
        canvas_factory: CanvasAdapterFactory,
        storage: StoragePort,
        rubric_store: RubricPort,
        extraction_registry: dict[ClasificacionActividad, ExtractionStrategy],
        grader: RubricGrader,
    ) -> None:
        self._canvas_factory = canvas_factory
        self._storage = storage
        self._rubric_store = rubric_store
        self._registry = extraction_registry
        self._grader = grader

    def execute(self, command: CalificarEntregableCommand) -> EvaluationResponseDTO | None:
        hierarchy = {
            "env": command.env,
            "universidad_id": command.id_universidad,
            "curso_id": command.id_curso,
            "estudiante_id": command.id_estudiante,
            "entregable_id": command.id_entregable,
        }
        grading = s3_keys.grading_key(**hierarchy)

        # Idempotencia: si ya hay calificación, no reprocesar.
        if self._storage.exists(key=grading):
            log.info("Entregable %s ya calificado; se omite.", command.id_entregable)
            return None

        # 1. Resolver el Canvas de la universidad (credenciales por tenant).
        canvas = self._canvas_factory.for_university(
            universidad_id=command.id_universidad, env=command.env
        )

        # 2. Descargar el entregable y guardarlo crudo.
        attachment = canvas.fetch_submission_attachment(
            course_id=command.id_curso,
            assignment_id=command.id_actividad,
            user_id=command.id_estudiante,
        )
        data, filename = canvas.download_file(attachment=attachment)
        self._storage.put_bytes(key=s3_keys.raw_key(filename=filename, **hierarchy), data=data)

        # 3. Extraer contenido (estrategia por clasificación).
        extracted_text = self._extract(filename=filename, data=data)
        self._storage.put_text(key=s3_keys.extracted_text_key(**hierarchy), text=extracted_text)

        # 4. Cargar la rúbrica.
        rubric = self._rubric_store.load(
            env=command.env,
            universidad_id=command.id_universidad,
            curso_id=command.id_curso,
            actividad_id=command.id_actividad,
            rubrica_id=command.id_rubrica,
        )

        # 5. Calificar.
        result = self._grader.grade(rubric=rubric.model_dump(), student_response=extracted_text)

        # 6. Escribir el resultado.
        self._storage.put_json(key=grading, obj=result.model_dump())

        # 7. Publicar en Canvas si el gate lo permite.
        published = False
        if result.publish:
            canvas.publish_grade(
                course_id=command.id_curso,
                assignment_id=command.id_actividad,
                user_id=command.id_estudiante,
                score=result.total_score,
                comment=build_grade_comment(result),
            )
            published = True

        self._storage.put_json(
            key=s3_keys.metadata_key(**hierarchy),
            obj=self._metadata(command, filename, result, published),
        )
        return result

    def _extract(self, *, filename: str, data: bytes) -> str:
        media_type = media_type_from_filename(filename)
        if media_type is None:
            raise TipoEntregableNoSoportadoError(
                f"Extensión no soportada para '{filename}'. Permitidos: {supported_extensions()}"
            )
        strategy = self._registry.get(clasificacion_from_media_type(media_type))
        if strategy is None:
            raise TipoEntregableNoSoportadoError(
                f"No hay estrategia de extracción para '{filename}'."
            )

        # Los extractores trabajan sobre un archivo local; volcamos los bytes.
        fd, tmp_path = tempfile.mkstemp(suffix=Path(filename).suffix)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
            return strategy.extract(file_path=tmp_path)
        finally:
            with contextlib.suppress(OSError):
                os.remove(tmp_path)

    def _metadata(
        self,
        command: CalificarEntregableCommand,
        filename: str,
        result: EvaluationResponseDTO,
        published: bool,
    ) -> dict:
        return {
            "id_universidad": command.id_universidad,
            "id_curso": command.id_curso,
            "id_actividad": command.id_actividad,
            "id_entregable": command.id_entregable,
            "id_estudiante": command.id_estudiante,
            "id_rubrica": command.id_rubrica,
            "env": command.env,
            "filename": filename,
            "total_score": result.total_score,
            "publish": result.publish,
            "confidence": result.confidence,
            "published": published,
            "created_at": datetime.now(UTC).isoformat(),
        }
