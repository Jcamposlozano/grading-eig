from __future__ import annotations

from abc import ABC, abstractmethod


class TranscriptionPort(ABC):
    @abstractmethod
    def transcribe(self, *, audio_path: str) -> str:
        raise NotImplementedError