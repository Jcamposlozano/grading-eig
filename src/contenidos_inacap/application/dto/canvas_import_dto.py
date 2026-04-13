from __future__ import annotations

from pydantic import BaseModel, Field


class ImportFromCanvasRequest(BaseModel):
    file_id: str = Field(
        ...,
        min_length=1,
        description="Identificador del archivo en Canvas (GET /api/v1/files/:id)",
    )


class ImportFromCanvasAssignmentRequest(BaseModel):
    course_id: str = Field(..., min_length=1, description="ID del curso en Canvas")
    assignment_id: str = Field(..., min_length=1, description="ID de la tarea (assignment)")
    user_id: str = Field(
        default="self",
        min_length=1,
        description="Usuario cuya entrega se descarga: 'self' = dueño del token, o id del alumno",
    )
    attachment_index: int = Field(
        default=0,
        ge=0,
        description="Si hay varios archivos en la entrega, cuál bajar (0 = el primero)",
    )
