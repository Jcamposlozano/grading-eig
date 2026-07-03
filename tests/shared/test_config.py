from __future__ import annotations

from grading.shared.config import load_config


def test_universidades_permitidas_from_yaml(monkeypatch):
    monkeypatch.delenv("UNIVERSIDADES_PERMITIDAS", raising=False)

    cfg = load_config()

    assert set(cfg["universidades"]["permitidas"]) == {"westfield", "eig", "esic", "uide"}


def test_universidades_permitidas_env_override(monkeypatch):
    monkeypatch.setenv("UNIVERSIDADES_PERMITIDAS", "EIG, esic ,")

    cfg = load_config()

    assert cfg["universidades"]["permitidas"] == ["eig", "esic"]
