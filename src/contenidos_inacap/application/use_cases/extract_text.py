from __future__ import annotations

from contenidos_inacap.application.strategies.extraction import (
    ExtractionStrategy,
    clasificacion_from_media_type,
)
from contenidos_inacap.domain.entities.material import MaterialStatus
from contenidos_inacap.domain.enums import ClasificacionActividad
from contenidos_inacap.ports.material_repository_port import MaterialRepositoryPort


class MaterialNotFoundError(Exception):
    pass


class UnsupportedExtractionTypeError(Exception):
    pass


class ExtractTextUseCase:
    def __init__(
        self,
        material_repository: MaterialRepositoryPort,
        extraction_registry: dict[ClasificacionActividad, ExtractionStrategy],
    ) -> None:
        self.material_repository = material_repository
        self.extraction_registry = extraction_registry

    def execute(self, *, material_id: str):
        material = self.material_repository.get_by_id(material_id)
        if not material:
            raise MaterialNotFoundError(f"No existe material con id={material_id}")

        material.status = MaterialStatus.PROCESSING
        material.error_message = None
        self.material_repository.update(material)

        try:
            clasificacion = clasificacion_from_media_type(material.media_type)
            strategy = self.extraction_registry.get(clasificacion)
            if strategy is None:
                raise UnsupportedExtractionTypeError(
                    f"El tipo '{material.media_type}' aún no está soportado en este endpoint."
                )

            extracted_text = strategy.extract(file_path=material.file_path)
            if not extracted_text.strip():
                raise ValueError("No fue posible extraer texto del archivo.")

            material.extracted_text = extracted_text
            material.status = MaterialStatus.COMPLETED
            material.error_message = None
            self.material_repository.update(material)
            return material

        except Exception as exc:
            material.status = MaterialStatus.FAILED
            material.error_message = str(exc)
            self.material_repository.update(material)
            raise
