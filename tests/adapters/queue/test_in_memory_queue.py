from __future__ import annotations

from contenidos_inacap.adapters.queue.in_memory_queue import InMemoryQueue


def test_enqueue_then_consume_fifo():
    queue = InMemoryQueue()
    queue.enqueue(message={"id": 1})
    queue.enqueue(message={"id": 2})

    messages = queue.consume(max_messages=5)

    assert [m.body["id"] for m in messages] == [1, 2]
    assert queue.consume(max_messages=5) == []  # se consumieron


def test_consume_respects_max_messages():
    queue = InMemoryQueue()
    for i in range(3):
        queue.enqueue(message={"i": i})

    assert len(queue.consume(max_messages=2)) == 2
    assert len(queue.consume(max_messages=2)) == 1


def test_ack_and_extend_are_noops():
    queue = InMemoryQueue()
    queue.ack(receipt_handle="x")
    queue.extend_visibility(receipt_handle="x", seconds=30)
