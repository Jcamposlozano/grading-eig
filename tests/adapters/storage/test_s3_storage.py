from __future__ import annotations

import pytest

pytest.importorskip("boto3")

from botocore.exceptions import ClientError

from grading.adapters.storage.s3_storage import S3Storage


class _FakeBody:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def read(self) -> bytes:
        return self._data


class FakeS3Client:
    """Cliente S3 mínimo en memoria para testear S3Storage sin red."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.content_types: dict[str, str] = {}

    def put_object(self, *, Bucket, Key, Body, ContentType=None):
        self.objects[Key] = Body
        if ContentType:
            self.content_types[Key] = ContentType
        return {}

    def get_object(self, *, Bucket, Key):
        return {"Body": _FakeBody(self.objects[Key])}

    def head_object(self, *, Bucket, Key):
        if Key not in self.objects:
            raise ClientError({"Error": {"Code": "404"}}, "HeadObject")
        return {}


def test_requires_bucket():
    with pytest.raises(ValueError):
        S3Storage(bucket="", client=FakeS3Client())


def test_roundtrip_and_exists():
    client = FakeS3Client()
    storage = S3Storage(bucket="prisma-calificacion-canvas", client=client)

    assert storage.exists(key="grading/calificacion.json") is False

    storage.put_json(key="grading/calificacion.json", obj={"total_score": 7})

    assert storage.exists(key="grading/calificacion.json") is True
    assert storage.get_json(key="grading/calificacion.json") == {"total_score": 7}
    assert client.content_types["grading/calificacion.json"] == "application/json"


def test_exists_reraises_non_404():
    class BoomClient(FakeS3Client):
        def head_object(self, *, Bucket, Key):
            raise ClientError({"Error": {"Code": "500"}}, "HeadObject")

    storage = S3Storage(bucket="b", client=BoomClient())

    with pytest.raises(ClientError):
        storage.exists(key="x")
