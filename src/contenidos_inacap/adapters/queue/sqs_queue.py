from __future__ import annotations

import json
from typing import Any

from contenidos_inacap.ports.queue_port import QueueMessage, QueuePort


class SqsQueue(QueuePort):
    """Cola sobre Amazon SQS (boto3). El cliente se inyecta para testear sin red."""

    def __init__(self, *, queue_url: str, region: str | None = None, client: Any = None) -> None:
        if not queue_url:
            raise ValueError("SqsQueue requiere queue_url.")
        self.queue_url = queue_url
        if client is None:
            import boto3

            client = boto3.client("sqs", region_name=region)
        self._client = client

    def enqueue(self, *, message: dict) -> str:
        response = self._client.send_message(
            QueueUrl=self.queue_url,
            MessageBody=json.dumps(message),
        )
        return response.get("MessageId", "")

    def consume(self, *, max_messages: int = 1, wait_seconds: int = 20) -> list[QueueMessage]:
        response = self._client.receive_message(
            QueueUrl=self.queue_url,
            MaxNumberOfMessages=max_messages,
            WaitTimeSeconds=wait_seconds,
        )
        messages = []
        for raw in response.get("Messages", []):
            messages.append(
                QueueMessage(
                    body=json.loads(raw["Body"]),
                    receipt_handle=raw["ReceiptHandle"],
                )
            )
        return messages

    def ack(self, *, receipt_handle: str) -> None:
        self._client.delete_message(QueueUrl=self.queue_url, ReceiptHandle=receipt_handle)

    def extend_visibility(self, *, receipt_handle: str, seconds: int) -> None:
        self._client.change_message_visibility(
            QueueUrl=self.queue_url,
            ReceiptHandle=receipt_handle,
            VisibilityTimeout=seconds,
        )
