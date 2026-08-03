from __future__ import annotations

from types import SimpleNamespace

import pytest

from cip import cli


def _settings() -> SimpleNamespace:
    return SimpleNamespace(
        api_host="127.0.0.1",
        api_port=8123,
        api_reload=True,
        log_level="INFO",
    )


def test_run_api_uses_validated_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}
    settings = _settings()

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


def test_scheduler_and_worker_commands_use_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings()
    captured: list[tuple[str, object]] = []
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    monkeypatch.setattr(
        cli,
        "run_scheduler_forever",
        lambda value: captured.append(("scheduler", value)),
    )
    monkeypatch.setattr(
        cli,
        "run_worker_forever",
        lambda value: captured.append(("worker", value)),
    )

    cli.run_scheduler()
    cli.run_worker()

    assert captured == [("scheduler", settings), ("worker", settings)]
