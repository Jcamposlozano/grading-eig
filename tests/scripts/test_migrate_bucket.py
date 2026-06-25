from __future__ import annotations

import migrate_bucket
from botocore.exceptions import ClientError


class FakeS3:
    def __init__(self, source: dict[str, bytes], dest: dict[str, bytes] | None = None) -> None:
        self.source = dict(source)
        self.dest = dict(dest or {})
        self.copies: list[tuple[str, str]] = []

    def get_paginator(self, _op):
        store = self

        class _Paginator:
            def paginate(self, *, Bucket, Prefix=""):
                contents = [
                    {"Key": k, "Size": len(v)}
                    for k, v in store.source.items()
                    if k.startswith(Prefix)
                ]
                yield {"Contents": contents}

        return _Paginator()

    def head_object(self, *, Bucket, Key):
        if Key in self.dest:
            return {}
        raise ClientError({"Error": {"Code": "404"}}, "HeadObject")

    def copy_object(self, *, Bucket, Key, CopySource):
        self.copies.append((CopySource["Key"], Key))
        self.dest[Key] = self.source[CopySource["Key"]]


def _silent(_msg: str) -> None:
    return None


def test_dry_run_copies_nothing():
    s3 = FakeS3({"a.txt": b"1", "b.txt": b"2"})

    stats = migrate_bucket.migrate(
        s3, source_bucket="old", dest_bucket="new", apply=False, log=_silent
    )

    assert stats.scanned == 2
    assert stats.copied == 2  # "copiaría", pero...
    assert s3.copies == []  # no copió nada


def test_apply_copies_missing_and_skips_existing():
    s3 = FakeS3({"a.txt": b"1", "b.txt": b"2"}, dest={"a.txt": b"x"})

    stats = migrate_bucket.migrate(
        s3, source_bucket="old", dest_bucket="new", apply=True, log=_silent
    )

    assert stats.copied == 1
    assert stats.skipped_existing == 1
    assert s3.copies == [("b.txt", "b.txt")]


def test_map_key_none_filters_out():
    s3 = FakeS3({"keep.json": b"1", "logs/x.log": b"2"})

    def mapper(key: str):
        return None if key.startswith("logs/") else key

    stats = migrate_bucket.migrate(
        s3, source_bucket="old", dest_bucket="new", map_key=mapper, apply=True, log=_silent
    )

    assert stats.filtered_out == 1
    assert stats.copied == 1
    assert s3.copies == [("keep.json", "keep.json")]
