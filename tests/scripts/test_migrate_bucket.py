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


def _migrate(s3, *, map_key=migrate_bucket.default_map_key, apply=False):
    return migrate_bucket.migrate(
        s3,
        source_bucket="old",
        dest_bucket="new",
        map_key=map_key,
        apply=apply,
        log=_silent,
    )


# --- motor genérico (identidad) ---------------------------------------------


def test_dry_run_copies_nothing():
    s3 = FakeS3({"a.txt": b"1", "b.txt": b"2"})

    stats = _migrate(s3, apply=False)

    assert stats.scanned == 2
    assert stats.copied == 2  # "copiaría", pero...
    assert s3.copies == []  # no copió nada


def test_apply_copies_missing_and_skips_existing():
    s3 = FakeS3({"a.txt": b"1", "b.txt": b"2"}, dest={"a.txt": b"x"})

    stats = _migrate(s3, apply=True)

    assert stats.copied == 1
    assert stats.skipped_existing == 1
    assert s3.copies == [("b.txt", "b.txt")]


def test_map_key_empty_filters_out():
    s3 = FakeS3({"keep.json": b"1", "logs/x.log": b"2"})

    def mapper(key: str) -> list[str]:
        return [] if key.startswith("logs/") else [key]

    stats = _migrate(s3, map_key=mapper, apply=True)

    assert stats.filtered_out == 1
    assert stats.copied == 1
    assert s3.copies == [("keep.json", "keep.json")]


def test_one_to_many_mapping():
    s3 = FakeS3({"src.json": b"1"})

    stats = _migrate(s3, map_key=lambda _k: ["a/x.json", "b/x.json"], apply=True)

    assert stats.copied == 2
    assert s3.copies == [("src.json", "a/x.json"), ("src.json", "b/x.json")]


# --- modo eig (curación + estructura nueva) ---------------------------------

OLD = {
    "rubricas/rubrica.json": b"{}",
    "rubricas/": b"",
    "raw/2692_30282_.json": b"{}",
    "raw/2692_30282_5941.json": b"{}",
    "raw/2692_30300_.json": b"{}",
    "raw/log_20260618_x.json": b"{}",
    "audit/test.txt": b"ok",
}


def test_discover_grading_excludes_logs():
    s3 = FakeS3(OLD)

    grading = migrate_bucket.discover_grading(s3, "old")

    assert sorted(k for *_rest, k in grading) == [
        "raw/2692_30282_.json",
        "raw/2692_30282_5941.json",
        "raw/2692_30300_.json",
    ]
    assert ("2692", "30282", "5941", "raw/2692_30282_5941.json") in grading
    assert ("2692", "30282", "", "raw/2692_30282_.json") in grading


def test_eig_mapper_rubric_fans_out_to_activities():
    mapper = migrate_bucket.build_eig_map_key({("2692", "30282"), ("2692", "30300")})

    dests = mapper("rubricas/rubrica.json")

    assert dests == [
        "prod/eig/2692/actividades/30282/rubrica/rubrica.json",
        "prod/eig/2692/actividades/30300/rubrica/rubrica.json",
    ]


def test_eig_mapper_grading_and_self():
    mapper = migrate_bucket.build_eig_map_key(set())

    assert mapper("raw/2692_30282_5941.json") == [
        "prod/eig/2692/5941/30282/grading/legacy_calificacion.json"
    ]
    assert mapper("raw/2692_30300_.json") == [
        "prod/eig/2692/self/30300/grading/legacy_calificacion.json"
    ]


def test_eig_mapper_drops_noise():
    mapper = migrate_bucket.build_eig_map_key({("2692", "30282")})

    assert mapper("raw/log_20260618_x.json") == []
    assert mapper("audit/test.txt") == []
    assert mapper("rubricas/") == []


def test_eig_end_to_end_curates():
    s3 = FakeS3(OLD)
    grading = migrate_bucket.discover_grading(s3, "old")
    curso_actividades = {(c, a) for c, a, _u, _k in grading}
    mapper = migrate_bucket.build_eig_map_key(curso_actividades)

    stats = _migrate(s3, map_key=mapper, apply=True)

    # 1 rúbrica -> 2 actividades (30282, 30300) + 3 calificaciones = 5 copias
    assert stats.copied == 5
    assert stats.filtered_out == 3  # rubricas/, log, audit
    assert (
        "rubricas/rubrica.json",
        "prod/eig/2692/actividades/30282/rubrica/rubrica.json",
    ) in s3.copies
    assert (
        "raw/2692_30282_5941.json",
        "prod/eig/2692/5941/30282/grading/legacy_calificacion.json",
    ) in s3.copies
