from __future__ import annotations

import init_universidades


class FakeS3:
    def __init__(self, existing_prefixes: set[str] | None = None) -> None:
        # prefijos que ya "tienen" objetos
        self.existing = set(existing_prefixes or set())
        self.put: list[str] = []

    def list_objects_v2(self, *, Bucket, Prefix, MaxKeys=1):
        count = 1 if any(p.startswith(Prefix) for p in self.existing) else 0
        return {"KeyCount": count}

    def put_object(self, *, Bucket, Key, Body):
        self.put.append(Key)
        self.existing.add(Key)


def _silent(_msg: str) -> None:
    return None


def test_dry_run_writes_nothing():
    s3 = FakeS3()

    result = init_universidades.init_universidades(
        s3,
        bucket="b",
        env="prod",
        universidades=["westfield", "esic"],
        apply=False,
        log=_silent,
    )

    assert result["created"] == ["westfield", "esic"]
    assert s3.put == []  # dry-run no escribe


def test_apply_creates_keep_and_skips_existing():
    s3 = FakeS3(existing_prefixes={"prod/eig/2692/x.json"})

    result = init_universidades.init_universidades(
        s3,
        bucket="b",
        env="prod",
        universidades=["eig", "westfield", "esic", "uide"],
        apply=True,
        log=_silent,
    )

    assert result["skipped"] == ["eig"]  # ya tiene objetos
    assert result["created"] == ["westfield", "esic", "uide"]
    assert s3.put == [
        "prod/westfield/.keep",
        "prod/esic/.keep",
        "prod/uide/.keep",
    ]


def test_idempotent_second_run_skips_all():
    s3 = FakeS3()
    kwargs = dict(bucket="b", env="prod", universidades=["westfield"], apply=True, log=_silent)

    init_universidades.init_universidades(s3, **kwargs)
    second = init_universidades.init_universidades(s3, **kwargs)

    assert second["created"] == []
    assert second["skipped"] == ["westfield"]
