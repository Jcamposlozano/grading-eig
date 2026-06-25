from __future__ import annotations

from abc import ABC, abstractmethod

from contenidos_inacap.domain.entities.material import Material


class MaterialRepositoryPort(ABC):
    @abstractmethod
    def save(self, material: Material) -> Material:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, material_id: str) -> Material | None:
        raise NotImplementedError

    @abstractmethod
    def update(self, material: Material) -> Material:
        raise NotImplementedError
