from __future__ import annotations

from types import SimpleNamespace

import pytest

from cip import cli


def test_run_api_uses_validated_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}
    settings = SimpleNamespace(
        api_host="127.0.0.1",
        api_port=8123,
        api_reload=True,
        log_level="INFO",
    )

    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    monkeypatch.setattr(
        cli.uvicorn,
        "run",
        lambda application, **options: captured.update(
            {"application": application, **options}
        ),
    )

    cli.run_api()

    assert captured == {
        "application": "cip.main:app",
        "host": "127.0.0.1",
        "port": 8123,
        "reload": True,
        "log_level": "info",
    }
