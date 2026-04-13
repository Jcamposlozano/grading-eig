from __future__ import annotations

import io
import os

from contenidos_inacap.adapters.canvas.canvas_client import (
    CanvasApiError,
    CanvasNotConfiguredError,
    download_file_bytes,
    fetch_assignment_submission,
    fetch_file_metadata,
    resolve_original_filename,
)
from contenidos_inacap.application.use_cases.upload_material import UploadMaterialUseCase
from contenidos_inacap.domain.entities.material import Material


def _canvas_settings() -> tuple[str, str]:
    base = (os.getenv("CANVAS_BASE_URL") or "").strip().rstrip("/")
    token = (os.getenv("CANVAS_ACCESS_TOKEN") or "").strip()
    if not base or not token:
        raise CanvasNotConfiguredError(
            "Defina CANVAS_BASE_URL y CANVAS_ACCESS_TOKEN en el entorno."
        )
    return base, token


def _attachment_from_submission(
    submission: dict,
    attachment_index: int,
) -> tuple[str, dict]:
    attachments = submission.get("attachments") or []
    if not attachments:
        raise CanvasApiError(
            "La entrega no tiene archivos adjuntos (o el token no puede verlos)."
        )
    if attachment_index < 0 or attachment_index >= len(attachments):
        raise CanvasApiError(
            f"attachment_index fuera de rango: hay {len(attachments)} adjunto(s)."
        )
    att = attachments[attachment_index]
    fid = att.get("id")
    if fid is None:
        raise CanvasApiError("El adjunto no incluye id de archivo.")
    return str(fid), att


class ImportMaterialFromCanvasUseCase:
    def __init__(self, upload_material: UploadMaterialUseCase) -> None:
        self._upload_material = upload_material

    def execute_from_assignment(
        self,
        *,
        course_id: str,
        assignment_id: str,
        user_id: str,
        attachment_index: int = 0,
    ) -> Material:
        """Resuelve el archivo desde la entrega de la tarea (sin file_id manual)."""
        base, token = _canvas_settings()
        submission = fetch_assignment_submission(
            base_url=base,
            token=token,
            course_id=course_id,
            assignment_id=assignment_id,
            user_id=user_id,
        )
        #print(submission)
        file_id, att = _attachment_from_submission(submission, attachment_index)
        hint = att.get("display_name") or att.get("filename")
        return self.execute(
            file_id=file_id,
            download_url=att.get("url"),
            filename_hint=hint if isinstance(hint, str) else None,
        )

    def execute(
        self,
        *,
        file_id: str,
        download_url: str | None = None,
        filename_hint: str | None = None,
    ) -> Material:
        base, token = _canvas_settings()
        meta = fetch_file_metadata(base_url=base, token=token, file_id=file_id)
        if filename_hint and str(filename_hint).strip():
            original_filename = str(filename_hint).strip()
        else:
            original_filename = resolve_original_filename(meta)
        raw = download_file_bytes(
            base_url=base,
            token=token,
            file_id=file_id,
            meta=meta,
            download_url=download_url,
        )
        stream = io.BytesIO(raw)
        try:
            return self._upload_material.execute(
                file_stream=stream,
                original_filename=original_filename,
            )
        finally:
            stream.close()
