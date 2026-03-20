from __future__ import annotations

from abc import ABC, abstractmethod


class DocumentExtractorPort(ABC):
    @abstractmethod
    def extract(self, *, file_path: str) -> str:
        raise NotImplementedError