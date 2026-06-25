from __future__ import annotations

from typing import Any

from botocore.exceptions import ClientError

from grading.ports.storage_port import StoragePort

_NOT_FOUND_CODES = {"404", "NoSuchKey", "NotFound"}


class S3Storage(StoragePort):
    """Implementación de ``StoragePort`` sobre Amazon S3 (boto3).

    El cliente se inyecta (``client``) para poder testear sin red; si no se
    provee, se construye ``boto3.client("s3", region_name=region)``.
    """

    def __init__(self, *, bucket: str, region: str | None = None, client: Any = None) -> None:
        if not bucket:
            raise ValueError("S3Storage requiere un bucket.")
        self.bucket = bucket
        if client is None:
            import boto3

            client = boto3.client("s3", region_name=region)
        self._client = client

    def put_bytes(self, *, key: str, data: bytes, content_type: str | None = None) -> str:
        extra = {"ContentType": content_type} if content_type else {}
        self._client.put_object(Bucket=self.bucket, Key=key, Body=data, **extra)
        return key

    def get_bytes(self, *, key: str) -> bytes:
        response = self._client.get_object(Bucket=self.bucket, Key=key)
        return response["Body"].read()

    def exists(self, *, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code in _NOT_FOUND_CODES:
                return False
            raise
