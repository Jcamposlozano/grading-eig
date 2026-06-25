from __future__ import annotations

from collections import deque

from contenidos_inacap.ports.queue_port import QueueMessage, QueuePort


class InMemoryQueue(QueuePort):
    """Cola en memoria para desarrollo y tests (sin AWS).

    ``consume`` entrega y remueve el mensaje en el acto; ``ack`` es no-op. No
    modela visibility timeout ni redelivery: es una ayuda de desarrollo, no un
    sustituto de SQS en producción.
    """

    def __init__(self) -> None:
        self._messages: deque[QueueMessage] = deque()
        self._counter = 0

    def enqueue(self, *, message: dict) -> str:
        self._counter += 1
        receipt_handle = str(self._counter)
        self._messages.append(QueueMessage(body=dict(message), receipt_handle=receipt_handle))
        return receipt_handle

    def consume(self, *, max_messages: int = 1, wait_seconds: int = 20) -> list[QueueMessage]:
        out: list[QueueMessage] = []
        for _ in range(max_messages):
            if not self._messages:
                break
            out.append(self._messages.popleft())
        return out

    def ack(self, *, receipt_handle: str) -> None:
        # El mensaje ya se removió en consume(); nada que hacer.
        return None

    def extend_visibility(self, *, receipt_handle: str, seconds: int) -> None:
        return None
