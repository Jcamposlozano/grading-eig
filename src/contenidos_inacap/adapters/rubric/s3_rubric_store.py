from __future__ import annotations

from contenidos_inacap.application.dto.evaluation_dto import RubricDTO
from contenidos_inacap.ports.rubric_port import RubricNotFoundError, RubricPort
from contenidos_inacap.ports.storage_port import StoragePort
from contenidos_inacap.shared.s3_keys import rubrica_key


class S3RubricStore(RubricPort):
    """Carga rúbricas (``rubrica.json``) desde el almacenamiento por jerarquía.

    Funciona sobre cualquier ``StoragePort`` (S3 en prod, local en dev/tests).
    """

    def __init__(self, *, storage: StoragePort) -> None:
        self._storage = storage

    def load(
        self,
        *,
        env: str,
        universidad_id: str,
        curso_id: str,
        actividad_id: str,
        rubrica_id: str,
    ) -> RubricDTO:
        key = rubrica_key(
            env=env,
            universidad_id=universidad_id,
            curso_id=curso_id,
            actividad_id=actividad_id,
            rubrica_id=rubrica_id,
        )
        if not self._storage.exists(key=key):
            raise RubricNotFoundError(f"No existe rúbrica en '{key}'.")

        payload = self._storage.get_json(key=key)
        return RubricDTO.model_validate(payload)
