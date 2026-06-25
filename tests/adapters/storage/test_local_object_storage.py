from __future__ import annotations

from grading.adapters.storage.local_object_storage import LocalObjectStorage


def test_put_get_bytes_roundtrip(tmp_path):
    storage = LocalObjectStorage(base_dir=str(tmp_path))
    key = "prod/eig/123/1011/789/raw/file.bin"

    returned = storage.put_bytes(key=key, data=b"hello")

    assert returned == key
    assert storage.get_bytes(key=key) == b"hello"


def test_text_roundtrip_utf8(tmp_path):
    storage = LocalObjectStorage(base_dir=str(tmp_path))

    storage.put_text(key="extracted/transcription.txt", text="ñandú — acción")

    assert storage.get_text(key="extracted/transcription.txt") == "ñandú — acción"


def test_json_roundtrip(tmp_path):
    storage = LocalObjectStorage(base_dir=str(tmp_path))
    obj = {"total_score": 10, "publish": True, "general_feedback": "bien"}

    storage.put_json(key="grading/calificacion.json", obj=obj)

    assert storage.get_json(key="grading/calificacion.json") == obj


def test_exists(tmp_path):
    storage = LocalObjectStorage(base_dir=str(tmp_path))

    assert storage.exists(key="missing.txt") is False

    storage.put_text(key="grading/metadata.json", text="{}")

    assert storage.exists(key="grading/metadata.json") is True
