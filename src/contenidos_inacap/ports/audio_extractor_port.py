from __future__ import annotations

from abc import ABC, abstractmethod


class AudioExtractorPort(ABC):
    @abstractmethod
    def extract_audio(self, *, input_path: str) -> str:
        """
        Recibe la ruta de un video y retorna la ruta del audio extraído.
        """
        raise NotImplementedError