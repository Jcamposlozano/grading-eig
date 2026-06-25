from __future__ import annotations

from contenidos_inacap.application.dto.evaluation_dto import EvaluationResponseDTO


def build_grade_comment(result: EvaluationResponseDTO) -> str:
    """Arma el comentario en español que se publica en Canvas con la nota."""
    lines = [
        f"Calificación total: {result.total_score}",
        "",
        "Detalle por criterio:",
    ]
    for item in result.criteria_results:
        lines.append(f"- {item.criterion_name}: {item.selected_level} ({item.score} pts)")
        lines.append(f"  Justificación: {item.justification}")
    lines.append("")
    lines.append("Retroalimentación general:")
    lines.append(result.general_feedback)
    return "\n".join(lines)
