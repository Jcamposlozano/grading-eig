from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class CanvasApiError(Exception):
    """Error al llamar a la API de Canvas."""


class CanvasNotConfiguredError(CanvasApiError):
    """Faltan CANVAS_BASE_URL o CANVAS_ACCESS_TOKEN."""


def _user_ids_equal(canvas_value: Any, target: int) -> bool:
    if canvas_value is None:
        return False
    try:
        return int(canvas_value) == int(target)
    except (TypeError, ValueError):
        return False


def _normalize_submissions_batch(raw: Any) -> list[Any]:
    """Canvas suele devolver lista; en algunos casos objeto con clave conocida."""
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        for key in ("submissions", "data", "results"):
            inner = raw.get(key)
            if isinstance(inner, list):
                return inner
    return []


def _get(url: str, token: str, *, timeout: float = 120.0) -> tuple[bytes, int]:
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read(), resp.getcode() or 200
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        if e.code == 404 and "/submissions/" in url:
            raise CanvasApiError(
                "Canvas devolvió 404 para la entrega. Suele pasar si: (1) ese usuario no "
                "ha entregado la tarea; (2) course_id o assignment_id no coinciden; "
                "(3) el token es de profesor: usa user_id con el id numérico del alumno "
                "(no 'self'). Detalle Canvas: "
                f"{body[:400]}"
            ) from e
        raise CanvasApiError(
            f"Canvas respondió {e.code} para {url}: {body[:500]}"
        ) from e
    except urllib.error.URLError as e:
        raise CanvasApiError(f"No se pudo conectar a Canvas: {e}") from e


def fetch_self_user_id(*, base_url: str, token: str) -> str:
    """GET /api/v1/users/self/profile → id numérico del usuario del token."""
    url = f"{base_url.rstrip('/')}/api/v1/users/self/profile"
    raw, _ = _get(url, token, timeout=60.0)
    data = json.loads(raw.decode("utf-8"))
    uid = data.get("id")
    if uid is None:
        raise CanvasApiError("Canvas no devolvió id en /users/self/profile.")
    return str(uid)


def fetch_assignment_submission(
    *,
    base_url: str,
    token: str,
    course_id: str,
    assignment_id: str,
    user_id: str,
) -> dict[str, Any]:
    """Obtiene la entrega de un usuario vía listado (misma API que en Canvas UI).

    Usa ``GET .../submissions?student_ids[]=...&include[]=attachments`` para pedir
    explícitamente la entrega de ese usuario (recomendado si el token es de profesor).

    `user_id` puede ser el id numérico del alumno o ``self`` (usuario del token).
    """
    resolved_uid = (
        fetch_self_user_id(base_url=base_url, token=token)
        if user_id.strip().lower() == "self"
        else user_id.strip()
    )
    try:
        target_uid = int(resolved_uid)
    except ValueError as exc:
        raise CanvasApiError(
            "user_id debe ser numérico o la cadena 'self'."
        ) from exc

    base = base_url.rstrip("/")
    cid = urllib.parse.quote(course_id, safe="")
    aid = urllib.parse.quote(assignment_id, safe="")

    page = 1
    max_pages = 50
    while page <= max_pages:
        params = [
            ("student_ids[]", str(target_uid)),
            ("include[]", "attachments"),
            ("per_page", "100"),
            ("page", str(page)),
        ]
        query = urllib.parse.urlencode(params)
        url = f"{base}/api/v1/courses/{cid}/assignments/{aid}/submissions?{query}"
        raw, _ = _get(url, token, timeout=120.0)
        parsed: Any = json.loads(raw.decode("utf-8"))
        batch = _normalize_submissions_batch(parsed)
        if not batch and not isinstance(parsed, (list, dict)):
            raise CanvasApiError(
                "Canvas devolvió un formato inesperado al listar entregas."
            )
        for sub in batch:
            if _user_ids_equal(sub.get("user_id"), target_uid):
                return sub
        if len(batch) < 100:
            break
        page += 1

    raise CanvasApiError(
        f"No hay entrega para user_id={resolved_uid} en esta tarea, o el token no puede "
        f"verla. Si usaste 'self', ese número es el usuario del token: si eres profesor, "
        f"pon en user_id el id de Canvas del alumno (no 'self'). Si eres el alumno, confirma "
        f"que entregaste la tarea y que lleva archivo adjunto."
    )


def fetch_file_metadata(*, base_url: str, token: str, file_id: str) -> dict[str, Any]:
    """GET /api/v1/files/:id"""
    url = f"{base_url.rstrip('/')}/api/v1/files/{urllib.parse.quote(file_id, safe='')}"
    raw, _ = _get(url, token, timeout=60.0)
    return json.loads(raw.decode("utf-8"))


def _absolute_canvas_url(base_url: str, path_or_url: str) -> str:
    p = path_or_url.strip()
    if p.startswith("http://") or p.startswith("https://"):
        return p
    if p.startswith("/"):
        return base_url.rstrip("/") + p
    return f"{base_url.rstrip('/')}/{p}"


def download_file_bytes(
    *,
    base_url: str,
    token: str,
    file_id: str,
    meta: dict[str, Any] | None = None,
    download_url: str | None = None,
) -> bytes:
    """Descarga el binario usando la URL que Canvas expone (con ``verifier``), no solo ``/download``.

    Orden: ``download_url`` del adjunto de la entrega → ``meta['url']`` del GET /files/:id →
    último recurso ``/api/v1/files/:id/download?download_frd=1``.
    """
    base = base_url.rstrip("/")
    if meta is None:
        meta = fetch_file_metadata(base_url=base_url, token=token, file_id=file_id)

    candidates: list[str] = []
    if download_url and str(download_url).strip():
        candidates.append(_absolute_canvas_url(base_url, str(download_url).strip()))
    api_url = meta.get("url")
    if isinstance(api_url, str) and api_url.strip():
        candidates.append(_absolute_canvas_url(base_url, api_url.strip()))

    def _looks_like_html(data: bytes) -> bool:
        head = data[: min(500, len(data))].lower()
        return b"<!doctype" in head or head.lstrip().startswith(b"<html")

    for url in candidates:
        if not url.startswith("http"):
            continue
        try:
            data, _ = _get(url, token, timeout=120.0)
        except CanvasApiError:
            continue
        if data and not _looks_like_html(data):
            return data

    url = (
        f"{base}/api/v1/files/"
        f"{urllib.parse.quote(file_id, safe='')}/download?download_frd=1"
    )
    try:
        data, _ = _get(url, token, timeout=120.0)
    except CanvasApiError as exc:
        raise CanvasApiError(
            "No se pudo descargar el archivo desde Canvas. Prueba un token con acceso al curso "
            "y al fichero, o descarga manual desde la URL del adjunto en la entrega."
        ) from exc
    if not data or _looks_like_html(data):
        raise CanvasApiError(
            "Canvas devolvió HTML en lugar del archivo (404 o sin permiso). Comprueba el token "
            "y que el fichero siga disponible."
        )
    return data


def _put(url: str, token: str, data: dict[str, Any], *, timeout: float = 120.0) -> tuple[bytes, int]:
    """Send PUT request to Canvas API."""
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="PUT",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read(), resp.getcode() or 200
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise CanvasApiError(
            f"Canvas respondió {e.code} para {url}: {body[:500]}"
        ) from e
    except urllib.error.URLError as e:
        raise CanvasApiError(f"No se pudo conectar a Canvas: {e}") from e


def _post(url: str, token: str, data: dict[str, Any], *, timeout: float = 120.0) -> tuple[bytes, int]:
    """Send POST request to Canvas API."""
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read(), resp.getcode() or 200
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise CanvasApiError(
            f"Canvas respondió {e.code} para {url}: {body[:500]}"
        ) from e
    except urllib.error.URLError as e:
        raise CanvasApiError(f"No se pudo conectar a Canvas: {e}") from e


def update_submission_grade(
    *,
    base_url: str,
    token: str,
    course_id: str,
    assignment_id: str,
    user_id: str,
    score: int | float,
    comment: str,
) -> dict[str, Any]:
    """Update submission with grade and feedback comment."""
    url = (
        f"{base_url.rstrip('/')}/api/v1/courses/"
        f"{urllib.parse.quote(course_id, safe='')}/assignments/"
        f"{urllib.parse.quote(assignment_id, safe='')}/submissions/"
        f"{urllib.parse.quote(user_id, safe='')}"
    )
    
    # First update the grade
    grade_data = {
        "submission": {
            "posted_grade": str(score)
        }
    }
    
    print(f"Enviando calificación a Canvas URL: {url}")
    print(f"Datos de calificación: {json.dumps(grade_data, indent=2)}")
    
    try:
        raw, status_code = _put(url, token, grade_data, timeout=120.0)
        response_data = json.loads(raw.decode("utf-8"))
        print(f"Respuesta calificación Canvas (status {status_code}): {json.dumps(response_data, indent=2)}")
    except Exception as e:
        print(f"Error en calificación a Canvas: {e}")
        raise
    
    # Then add the comment separately
    comment_url = (
        f"{base_url.rstrip('/')}/api/v1/courses/"
        f"{urllib.parse.quote(course_id, safe='')}/assignments/"
        f"{urllib.parse.quote(assignment_id, safe='')}/submissions/"
        f"{urllib.parse.quote(user_id, safe='')}"
    )
    
    comment_data = {
        "comment": {
            "text_comment": comment
        }
    }
    
    print(f"Enviando comentario a Canvas URL: {comment_url}")
    print(f"Datos de comentario: {json.dumps(comment_data, indent=2)}")
    
    try:
        raw, status_code = _put(comment_url, token, comment_data, timeout=120.0)
        comment_response = json.loads(raw.decode("utf-8"))
        print(f"Respuesta comentario Canvas (status {status_code}): {json.dumps(comment_response, indent=2)}")
    except Exception as e:
        print(f"Error en comentario a Canvas: {e}")
        # Don't raise here, grade was already updated
    
    return response_data


def resolve_original_filename(meta: dict[str, Any]) -> str:
    name = (meta.get("display_name") or meta.get("filename") or "download").strip()
    return name if name else "download"
