from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from contenidos_inacap.application.dto.evaluation_dto import (
    EvaluationRequestDTO,
    EvaluationResponseDTO,
)
from contenidos_inacap.application.use_cases.evaluate_student_response import (
    EvaluateStudentResponseUseCase,
    MaterialForEvaluationNotFoundError,
    MaterialWithoutExtractedTextError,
)
from contenidos_inacap.shared.container import get_evaluate_student_response_use_case

router = APIRouter(prefix="/v1/evaluations", tags=["evaluations"])


@router.post(
    "",
    response_model=EvaluationResponseDTO,
    status_code=status.HTTP_200_OK,
)
async def evaluate_student_response(request: EvaluationRequestDTO):
    try:
        use_case: EvaluateStudentResponseUseCase = (
            get_evaluate_student_response_use_case()
        )
        return use_case.execute(request)

    except MaterialForEvaluationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except MaterialWithoutExtractedTextError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc