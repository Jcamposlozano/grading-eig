from __future__ import annotations

from contenidos_inacap.shared.s3_keys import rubrica_key


def test_rubrica_key_layout():
    key = rubrica_key(
        env="prod",
        universidad_id="eig",
        curso_id="123",
        actividad_id="456",
        rubrica_id="rA",
    )
    assert key == "prod/eig/123/actividades/456/rubrica/rA.json"
