from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text

from cip.shared.config.settings import Settings, get_settings
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import (
    create_database_engine,
    create_session_factory,
    session_scope,
)


def test_settings_have_safe_local_defaults() -> None:
    settings = Settings(environment="development", _env_file=None)

    assert settings.environment == "development"
    assert settings.api_host == "127.0.0.1"
    assert settings.source_registry_path == Path("policies/sources.example.yml")
    assert settings.greenhouse_board_registry_path == Path("policies/greenhouse_boards.yml")
    assert settings.collection_schedule_path == Path("policies/collection_schedules.yml")
    assert settings.scheduler_poll_seconds == 5.0
    assert settings.worker_poll_seconds == 2.0


def test_settings_read_prefixed_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CIP_ENVIRONMENT", "test")
    monkeypatch.setenv("CIP_API_PORT", "9000")

    settings = Settings(_env_file=None)

    assert settings.environment == "test"
    assert settings.api_port == 9000


def test_cached_settings_can_be_loaded() -> None:
    get_settings.cache_clear()

    assert get_settings() is get_settings()


def test_database_metadata_contains_foundation_tables() -> None:
    metadata = get_metadata()

    assert set(metadata.tables) == {
        "collection_checkpoints",
        "collection_circuits",
        "collection_dead_letters",
        "collection_jobs",
        "commercial_signals",
        "evidence",
        "need_hypotheses",
        "need_hypothesis_signals",
        "opportunities",
        "opportunity_evidence",
        "opportunity_reviews",
        "opportunity_score_components",
        "organizations",
        "raw_observations",
        "sources",
        "suppressions",
    }


def test_metadata_creates_on_sqlite() -> None:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")

    get_metadata().create_all(engine)

    assert get_metadata().tables["raw_observations"].foreign_keys
    assert get_metadata().tables["collection_jobs"].foreign_keys
    assert get_metadata().tables["opportunities"].foreign_keys
    assert get_metadata().tables["commercial_signals"].foreign_keys


def test_database_url_is_required() -> None:
    with pytest.raises(ValueError, match="database_url"):
        create_database_engine("  ")


def test_session_scope_commits_and_rolls_back() -> None:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE tx_test (value INTEGER NOT NULL)"))
    factory = create_session_factory(engine)

    with session_scope(factory) as session:
        session.execute(text("INSERT INTO tx_test (value) VALUES (1)"))

    with (
        pytest.raises(RuntimeError, match="rollback"),
        session_scope(factory) as session,
    ):
        session.execute(text("INSERT INTO tx_test (value) VALUES (2)"))
        raise RuntimeError("rollback")

    with engine.connect() as connection:
        count = connection.scalar(text("SELECT COUNT(*) FROM tx_test"))

    assert count == 1
