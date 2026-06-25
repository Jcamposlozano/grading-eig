from __future__ import annotations

from contenidos_inacap.entrypoints.worker import run_consume_loop
from contenidos_inacap.ports.queue_port import QueueMessage


class FakeShutdown:
    def __init__(self) -> None:
        self._set = False

    def is_set(self) -> bool:
        return self._set

    def wait(self, timeout=None) -> bool:
        self._set = True
        return True


class FakeQueue:
    def __init__(self, batches) -> None:
        self._batches = list(batches)
        self.acked: list[str] = []

    def consume(self, *, max_messages, wait_seconds):
        return self._batches.pop(0) if self._batches else []

    def ack(self, *, receipt_handle):
        self.acked.append(receipt_handle)


def test_processes_and_acks_on_success():
    batch = [
        QueueMessage(body={"i": 1}, receipt_handle="r1"),
        QueueMessage(body={"i": 2}, receipt_handle="r2"),
    ]
    queue = FakeQueue([batch])
    handled: list[dict] = []

    run_consume_loop(
        queue=queue,
        handler=lambda body: handled.append(body),
        shutdown=FakeShutdown(),
        wait_seconds=0,
        max_messages=10,
        idle_sleep=0,
    )

    assert handled == [{"i": 1}, {"i": 2}]
    assert queue.acked == ["r1", "r2"]


def test_no_ack_when_handler_raises():
    queue = FakeQueue([[QueueMessage(body={"i": 1}, receipt_handle="r1")]])

    def boom(_body):
        raise RuntimeError("fallo")

    run_consume_loop(
        queue=queue,
        handler=boom,
        shutdown=FakeShutdown(),
        wait_seconds=0,
        max_messages=10,
        idle_sleep=0,
    )

    assert queue.acked == []
