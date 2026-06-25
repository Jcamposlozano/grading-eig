from __future__ import annotations

import json
from abc import ABC, abstractmethod


class StoragePort(ABC):
    """Almacenamiento de objetos por clave (estilo S3).

    Distinto de ``FileStoragePort`` (que guarda archivos subidos en subcarpetas y
    devuelve rutas locales). ``StoragePort`` es la abstracción para el flujo nuevo
    multi-tenant, con claves jerárquicas tipo
    ``{env}/{universidad}/{curso}/{estudiante}/{entregable}/raw/archivo``.

    Las implementaciones solo necesitan resolver ``put_bytes`` / ``get_bytes`` /
    ``exists``; los helpers de texto y JSON se construyen sobre esos.
    """

    @abstractmethod
    def put_bytes(self, *, key: str, data: bytes, content_type: str | None = None) -> str:
        """Guarda ``data`` bajo ``key``. Retorna la clave almacenada."""
        raise NotImplementedError

    @abstractmethod
    def get_bytes(self, *, key: str) -> bytes:
        """Lee los bytes en ``key``. Lanza si la clave no existe."""
        raise NotImplementedError

    @abstractmethod
    def exists(self, *, key: str) -> bool:
        """Indica si existe un objeto en ``key``."""
        raise NotImplementedError

    def put_text(self, *, key: str, text: str) -> str:
        return self.put_bytes(
            key=key,
            data=text.encode("utf-8"),
            content_type="text/plain; charset=utf-8",
        )

    def get_text(self, *, key: str) -> str:
        return self.get_bytes(key=key).decode("utf-8")

    def put_json(self, *, key: str, obj: dict) -> str:
        data = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
        return self.put_bytes(key=key, data=data, content_type="application/json")

    def get_json(self, *, key: str) -> dict:
        return json.loads(self.get_bytes(key=key).decode("utf-8"))
