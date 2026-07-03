from __future__ import annotations

import json

import pytest

from grading.adapters.secrets.secrets_manager_credentials import (
    SecretsManagerCredentials,
)
from grading.ports.credentials_port import CredentialsResolutionError


class FakeSecretsManager:
    def __init__(self, secrets: dict[str, str]) -> None:
        self.secrets = secrets
        self.calls = 0

    def get_secret_value(self, *, SecretId):
        self.calls += 1
        if SecretId not in self.secrets:
            raise RuntimeError("ResourceNotFoundException")
        return {"SecretString": self.secrets[SecretId]}


def test_secret_name_convention():
    sm = SecretsManagerCredentials(client=FakeSecretsManager({}))
    assert sm.secret_name(universidad_id="eig", env="prod") == "prisma/grading/prod/canvas/eig"


def test_parses_secret():
    client = FakeSecretsManager(
        {"prisma/grading/prod/canvas/eig": json.dumps({"base_url": "https://eig.x/", "token": "t"})}
    )
    sm = SecretsManagerCredentials(client=client)

    creds = sm.get_canvas_credentials(universidad_id="eig", env="prod")

    assert creds.base_url == "https://eig.x"
    assert creds.token == "t"


def test_accepts_aliases():
    client = FakeSecretsManager(
        {
            "prisma/grading/dev/canvas/eig": json.dumps(
                {"domain": "https://eig.x", "key-canvas": "T"}
            )
        }
    )
    sm = SecretsManagerCredentials(client=client)

    creds = sm.get_canvas_credentials(universidad_id="eig", env="dev")

    assert creds.base_url == "https://eig.x"
    assert creds.token == "T"


def test_caches_until_ttl_expires():
    clock = {"now": 0.0}
    client = FakeSecretsManager(
        {"prisma/grading/dev/canvas/eig": json.dumps({"base_url": "https://eig.x", "token": "t"})}
    )
    sm = SecretsManagerCredentials(
        client=client, cache_ttl_seconds=100.0, clock=lambda: clock["now"]
    )

    sm.get_canvas_credentials(universidad_id="eig", env="dev")
    sm.get_canvas_credentials(universidad_id="eig", env="dev")
    assert client.calls == 1  # segunda lectura desde cache

    clock["now"] = 200.0  # TTL expirado
    sm.get_canvas_credentials(universidad_id="eig", env="dev")
    assert client.calls == 2


def test_missing_secret_raises():
    sm = SecretsManagerCredentials(client=FakeSecretsManager({}))
    with pytest.raises(CredentialsResolutionError):
        sm.get_canvas_credentials(universidad_id="nope", env="dev")


def test_incomplete_secret_raises():
    client = FakeSecretsManager(
        {"prisma/grading/dev/canvas/eig": json.dumps({"base_url": "https://eig.x"})}
    )
    sm = SecretsManagerCredentials(client=client)
    with pytest.raises(CredentialsResolutionError):
        sm.get_canvas_credentials(universidad_id="eig", env="dev")
