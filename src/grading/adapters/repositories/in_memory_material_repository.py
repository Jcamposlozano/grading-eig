from __future__ import annotations

from grading.domain.entities.material import Material
from grading.ports.material_repository_port import MaterialRepositoryPort


class InMemoryMaterialRepository(MaterialRepositoryPort):
    def __init__(self) -> None:
        self._storage: dict[str, Material] = {}

    def save(self, material: Material) -> Material:
        self._storage[material.id] = material
        return material

    def get_by_id(self, material_id: str) -> Material | None:
        return self._storage.get(material_id)

    def update(self, material: Material) -> Material:
        self._storage[material.id] = material
        return material
