from __future__ import annotations

import json

import pytest

from grading.adapters.queue.sqs_queue import SqsQueue


class FakeSqsClient:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []
        self.deleted: list[str] = []
        self.visibility: list[tuple[str, int]] = []

    def send_message(self, *, QueueUrl, MessageBody):
        self.sent.append((QueueUrl, MessageBody))
        return {"MessageId": "mid-1"}

    def receive_message(self, *, QueueUrl, MaxNumberOfMessages, WaitTimeSeconds):
        return {
            "Messages": [
                {"Body": json.dumps({"hello": "world"}), "ReceiptHandle": "rh-1"},
            ]
        }

    def delete_message(self, *, QueueUrl, ReceiptHandle):
        self.deleted.append(ReceiptHandle)

    def change_message_visibility(self, *, QueueUrl, ReceiptHandle, VisibilityTimeout):
        self.visibility.append((ReceiptHandle, VisibilityTimeout))


def test_requires_queue_url():
    with pytest.raises(ValueError):
        SqsQueue(queue_url="", client=FakeSqsClient())


def test_enqueue_serializes_body():
    client = FakeSqsClient()
    queue = SqsQueue(queue_url="http://q", client=client)

    message_id = queue.enqueue(message={"a": 1})

    assert message_id == "mid-1"
    assert json.loads(client.sent[0][1]) == {"a": 1}


def test_consume_parses_body_and_handle():
    queue = SqsQueue(queue_url="http://q", client=FakeSqsClient())

    messages = queue.consume(max_messages=1, wait_seconds=0)

    assert messages[0].body == {"hello": "world"}
    assert messages[0].receipt_handle == "rh-1"


def test_ack_and_extend_visibility_delegate():
    client = FakeSqsClient()
    queue = SqsQueue(queue_url="http://q", client=client)

    queue.ack(receipt_handle="rh-1")
    queue.extend_visibility(receipt_handle="rh-1", seconds=60)

    assert client.deleted == ["rh-1"]
    assert client.visibility == [("rh-1", 60)]
