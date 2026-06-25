from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class QueueMessage:
    """Un mensaje de la cola: cuerpo ya deserializado + handle para ack/visibility."""

    body: dict
    receipt_handle: str


class QueuePort(ABC):
    """Cola de trabajo (SQS en prod, en memoria en dev/tests)."""

    @abstractmethod
    def enqueue(self, *, message: dict) -> str:
        """Encola ``message`` (JSON-serializable). Retorna el id del mensaje."""
        raise NotImplementedError

    @abstractmethod
    def consume(self, *, max_messages: int = 1, wait_seconds: int = 20) -> list[QueueMessage]:
        """Lee hasta ``max_messages`` mensajes (long-polling ``wait_seconds``)."""
        raise NotImplementedError

    @abstractmethod
    def ack(self, *, receipt_handle: str) -> None:
        """Confirma (borra) un mensaje procesado con éxito."""
        raise NotImplementedError

    @abstractmethod
    def extend_visibility(self, *, receipt_handle: str, seconds: int) -> None:
        """Extiende el visibility timeout (para tareas largas, p. ej. video)."""
        raise NotImplementedError
