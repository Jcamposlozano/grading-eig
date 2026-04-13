from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from contenidos_inacap.adapters.canvas.canvas_client import (
    CanvasApiError,
    CanvasNotConfiguredError,
)
from contenidos_inacap.application.dto.canvas_import_dto import (
    ImportFromCanvasAssignmentRequest,
    ImportFromCanvasRequest,
)
from contenidos_inacap.application.dto.extract_text_dto import ExtractTextResponse
from contenidos_inacap.application.dto.material_dto import UploadMaterialResponse
from contenidos_inacap.application.use_cases.extract_text import (
    ExtractTextUseCase,
    MaterialNotFoundError,
    UnsupportedExtractionTypeError,
)
from contenidos_inacap.application.use_cases.upload_material import (
    EmptyFileError,
    UnsupportedFileTypeError,
    UploadMaterialUseCase,
)
from contenidos_inacap.shared.container import (
    get_extract_text_use_case,
    get_import_material_from_canvas_use_case,
    get_upload_material_use_case,
)

router = APIRouter(prefix="/v1/materials", tags=["materials"])


@router.post(
    "",
    response_model=UploadMaterialResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_material(
    file: UploadFile = File(...),
    material_type: str | None = Form(default=None),
):
    try:
        use_case: UploadMaterialUseCase = get_upload_material_use_case()

        material = use_case.execute(
            file_stream=file.file,
            original_filename=file.filename or "",
            declared_media_type=material_type,
        )

        return UploadMaterialResponse(
            material_id=material.id,
            original_filename=material.original_filename,
            stored_filename=material.filename,
            media_type=material.media_type,
            mime_type=material.mime_type,
            file_size=material.file_size,
            status=material.status,
            created_at=material.created_at,
        )

    except UnsupportedFileTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except EmptyFileError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    finally:
        await file.close()


@router.post(
    "/from-canvas",
    response_model=UploadMaterialResponse,
    status_code=status.HTTP_201_CREATED,
)
async def import_from_canvas(body: ImportFromCanvasRequest):
    """Descarga un archivo desde Canvas (API) y lo registra como material."""
    try:
        use_case = get_import_material_from_canvas_use_case()
        material = use_case.execute(file_id=body.file_id.strip())
        return UploadMaterialResponse(
            material_id=material.id,
            original_filename=material.original_filename,
            stored_filename=material.filename,
            media_type=material.media_type,
            mime_type=material.mime_type,
            file_size=material.file_size,
            status=material.status,
            created_at=material.created_at,
        )
    except CanvasNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except CanvasApiError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except UnsupportedFileTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except EmptyFileError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/from-canvas-assignment",
    response_model=UploadMaterialResponse,
    status_code=status.HTTP_201_CREATED,
)
async def import_from_canvas_assignment(body: ImportFromCanvasAssignmentRequest):
    """Descarga el archivo de la entrega de una tarea (curso + assignment + usuario). No hace falta file_id."""
    try:
        use_case = get_import_material_from_canvas_use_case()
        material = use_case.execute_from_assignment(
            course_id=body.course_id.strip(),
            assignment_id=body.assignment_id.strip(),
            user_id=body.user_id.strip(),
            attachment_index=body.attachment_index,
        )
        return UploadMaterialResponse(
            material_id=material.id,
            original_filename=material.original_filename,
            stored_filename=material.filename,
            media_type=material.media_type,
            mime_type=material.mime_type,
            file_size=material.file_size,
            status=material.status,
            created_at=material.created_at,
        )
    except CanvasNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except CanvasApiError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except UnsupportedFileTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except EmptyFileError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/{material_id}/extract-text",
    response_model=ExtractTextResponse,
    status_code=status.HTTP_200_OK,
)
async def extract_text(material_id: str):
    try:
        use_case: ExtractTextUseCase = get_extract_text_use_case()
        material = use_case.execute(material_id=material_id)

        return ExtractTextResponse(
            material_id=material.id,
            original_filename=material.original_filename,
            media_type=material.media_type,
            status=material.status,
            extracted_text=material.extracted_text,
            error_message=material.error_message,
            created_at=material.created_at,
        )

    except MaterialNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except UnsupportedExtractionTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc