from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path
from typing import BinaryIO

from contenidos_inacap.ports.file_storage_port import FileStoragePort


class LocalFileStorage(FileStoragePort):
    def __init__(self, base_dir: str = "data/uploads") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_file(
        self,
        *,
        file_stream: BinaryIO,
        original_filename: str,
        target_subdir: str,
    ) -> tuple[str, str, int]:
        extension = Path(original_filename).suffix.lower()
        stored_filename = f"{uuid.uuid4().hex}{extension}"

        target_dir = self.base_dir / target_subdir
        target_dir.mkdir(parents=True, exist_ok=True)

        target_path = target_dir / stored_filename

        with open(target_path, "wb") as output_file:
            shutil.copyfileobj(file_stream, output_file)

        file_size = os.path.getsize(target_path)

        return stored_filename, str(target_path.resolve()), file_size


