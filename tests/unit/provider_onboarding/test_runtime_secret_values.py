from __future__ import annotations

from pathlib import Path

import pytest

from cip.modules.provider_onboarding.application.secrets import LocalSecretValueResolver
from cip.modules.provider_onboarding.domain.models import SecretReference


def test_env_secret_is_resolved_transiently(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CIP_BRAVE_SEARCH_API_TOKEN", "secret-value")
    resolver = LocalSecretValueResolver()

    value = resolver.resolve(SecretReference("env://CIP_BRAVE_SEARCH_API_TOKEN"))

    assert value == "secret-value"


def test_missing_env_secret_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CIP_BRAVE_SEARCH_API_TOKEN", raising=False)
    resolver = LocalSecretValueResolver()

    with pytest.raises(RuntimeError, match="unavailable"):
        resolver.resolve(SecretReference("env://CIP_BRAVE_SEARCH_API_TOKEN"))


def test_file_secret_is_bounded_to_run_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    resolver = LocalSecretValueResolver()
    reference = SecretReference("file-secret:///run/secrets/brave_search_token")

    monkeypatch.setattr(Path, "is_file", lambda _self: True)
    monkeypatch.setattr(Path, "stat", lambda _self: _Stat(12))
    monkeypatch.setattr(Path, "read_text", lambda _self, **_kwargs: "file-secret")

    assert resolver.resolve(reference) == "file-secret"


class _Stat:
    def __init__(self, size: int) -> None:
        self.st_size = size
