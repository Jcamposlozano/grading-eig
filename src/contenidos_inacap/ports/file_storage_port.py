from __future__ import annotations

from abc import ABC, abstractmethod
from typing import BinaryIO


class FileStoragePort(ABC):
    @abstractmethod
    def save_file(
        self,
        *,
        file_stream: BinaryIO,
        original_filename: str,
        target_subdir: str,
    ) -> tuple[str, str, int]:
        """
        Guarda un archivo y retorna:
        - stored_filename
        - absolute_path
        - file_size
        """
        raise NotImplementedError