from __future__ import annotations

import pytest

from grading.adapters.rubric.s3_rubric_store import S3RubricStore
from grading.adapters.storage.local_object_storage import LocalObjectStorage
from grading.ports.rubric_port import RubricNotFoundError
from grading.shared.s3_keys import rubrica_key

RUBRIC = {
    "rubric_name": "Rúbrica demo",
    "max_score": 10,
    "criteria": [
        {
            "id": "c1",
            "name": "Claridad",
            "levels": [{"level": "Alto", "points": 10, "description": "muy claro"}],
        }
    ],
}


def test_loads_and_validates_rubric(tmp_path):
    storage = LocalObjectStorage(base_dir=str(tmp_path))
    key = rubrica_key(
        env="dev", universidad_id="eig", curso_id="c", actividad_id="a", rubrica_id="r"
    )
    storage.put_json(key=key, obj=RUBRIC)
    store = S3RubricStore(storage=storage)

    rubric = store.load(
        env="dev", universidad_id="eig", curso_id="c", actividad_id="a", rubrica_id="r"
    )

    assert rubric.rubric_name == "Rúbrica demo"
    assert rubric.criteria[0].id == "c1"
    assert rubric.criteria[0].levels[0].points == 10


def test_missing_rubric_raises(tmp_path):
    store = S3RubricStore(storage=LocalObjectStorage(base_dir=str(tmp_path)))

    with pytest.raises(RubricNotFoundError):
        store.load(
            env="dev", universidad_id="eig", curso_id="c", actividad_id="a", rubrica_id="nope"
        )
