from __future__ import annotations

from pathlib import Path

from grading.ports.storage_port import StoragePort


class LocalObjectStorage(StoragePort):
    """Implementación de ``StoragePort`` sobre el sistema de archivos local.

    Útil para desarrollo y tests sin AWS. La clave se interpreta como ruta
    relativa bajo ``base_dir`` (por eso puede contener ``/``).
    """

    def __init__(self, base_dir: str = "data/objects") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, key: str) -> Path:
        return self.base_dir / key

    def put_bytes(self, *, key: str, data: bytes, content_type: str | None = None) -> str:
        path = self._path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def get_bytes(self, *, key: str) -> bytes:
        return self._path_for(key).read_bytes()

    def exists(self, *, key: str) -> bool:
        return self._path_for(key).is_file()
