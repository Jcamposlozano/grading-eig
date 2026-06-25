from __future__ import annotations

import pytest

from contenidos_inacap.adapters.secrets.env_credentials import EnvCredentials
from contenidos_inacap.ports.credentials_port import CredentialsResolutionError


def test_reads_global_env_and_strips_trailing_slash(monkeypatch):
    monkeypatch.setenv("CANVAS_BASE_URL", "https://eig.instructure.com/")
    monkeypatch.setenv("CANVAS_ACCESS_TOKEN", "tok123")

    creds = EnvCredentials().get_canvas_credentials(universidad_id="eig", env="dev")

    assert creds.base_url == "https://eig.instructure.com"
    assert creds.token == "tok123"


def test_raises_when_missing(monkeypatch):
    monkeypatch.delenv("CANVAS_BASE_URL", raising=False)
    monkeypatch.delenv("CANVAS_ACCESS_TOKEN", raising=False)

    with pytest.raises(CredentialsResolutionError):
        EnvCredentials().get_canvas_credentials(universidad_id="eig", env="dev")
