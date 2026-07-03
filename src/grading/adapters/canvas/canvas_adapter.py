from __future__ import annotations

from grading.adapters.canvas import canvas_client
from grading.ports.canvas_port import AttachmentRef, CanvasPort
from grading.ports.credentials_port import CredentialsPort


class CanvasAdapter(CanvasPort):
    """Implementación de ``CanvasPort`` para un Canvas concreto (``base_url`` + ``token``).

    Delega en las funciones ya probadas de ``canvas_client`` (paginación,
    ``download_frd``, detección de HTML, etc.), pasándoles las credenciales de la
    instancia en lugar de leerlas de variables de entorno globales.
    """

    def __init__(self, *, base_url: str, token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token

    def fetch_submission_attachment(
        self,
        *,
        course_id: str,
        assignment_id: str,
        user_id: str,
        attachment_index: int = 0,
    ) -> AttachmentRef:
        submission = canvas_client.fetch_assignment_submission(
            base_url=self.base_url,
            token=self.token,
            course_id=course_id,
            assignment_id=assignment_id,
            user_id=user_id,
        )
        attachments = submission.get("attachments") or []
        if not attachments:
            raise canvas_client.CanvasApiError("La entrega no tiene archivos adjuntos en Canvas.")
        if attachment_index < 0 or attachment_index >= len(attachments):
            raise canvas_client.CanvasApiError(
                f"attachment_index={attachment_index} fuera de rango "
                f"(la entrega tiene {len(attachments)} adjunto(s))."
            )

        attachment = attachments[attachment_index]
        file_id = attachment.get("id")
        if file_id is None:
            raise canvas_client.CanvasApiError("El adjunto de Canvas no tiene id.")

        return AttachmentRef(
            file_id=str(file_id),
            filename=attachment.get("display_name") or attachment.get("filename"),
            download_url=attachment.get("url") or attachment.get("download_url"),
        )

    def download_file(self, *, attachment: AttachmentRef) -> tuple[bytes, str]:
        meta = canvas_client.fetch_file_metadata(
            base_url=self.base_url,
            token=self.token,
            file_id=attachment.file_id,
        )
        filename = attachment.filename or canvas_client.resolve_original_filename(meta)
        data = canvas_client.download_file_bytes(
            base_url=self.base_url,
            token=self.token,
            file_id=attachment.file_id,
            meta=meta,
            download_url=attachment.download_url,
        )
        return data, filename

    def publish_grade(
        self,
        *,
        course_id: str,
        assignment_id: str,
        user_id: str,
        score: int | float,
        comment: str,
    ) -> None:
        canvas_client.update_submission_grade(
            base_url=self.base_url,
            token=self.token,
            course_id=course_id,
            assignment_id=assignment_id,
            user_id=user_id,
            score=score,
            comment=comment,
        )


class CanvasAdapterFactory:
    """Construye un ``CanvasPort`` por universidad, resolviendo credenciales."""

    def __init__(self, credentials: CredentialsPort) -> None:
        self._credentials = credentials

    def for_university(self, *, universidad_id: str, env: str) -> CanvasPort:
        creds = self._credentials.get_canvas_credentials(universidad_id=universidad_id, env=env)
        return CanvasAdapter(base_url=creds.base_url, token=creds.token)
