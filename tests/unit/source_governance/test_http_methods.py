from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from cip.modules.source_governance.domain.models import (
    AuthorizationStatus,
    CollectionRequest,
    DataCategory,
    DecisionReason,
    HttpMethod,
    SourceAuthorization,
    SourcePolicy,
    SourceRuntimeState,
    SourceStatus,
    SourceType,
)
from cip.modules.source_governance.infrastructure.models import SourceRecord
from cip.modules.source_governance.infrastructure.persistence import sync_source_registry
from cip.modules.source_governance.infrastructure.registry import load_source_registry
from cip.shared.persistence.metadata import get_metadata

NOW = datetime(2026, 8, 16, 12, 0, tzinfo=UTC)


def _policy() -> SourcePolicy:
    return SourcePolicy(
        id="public-form",
        name="Public form",
        base_url="https://example.org/public/",
        status=SourceStatus.ENABLED,
        source_type=SourceType.BROWSER,
        owner="Example",
        terms_url="https://example.org/terms",
        allowed_data_categories=frozenset({DataCategory.PUBLIC_RESULT_METADATA}),
        human_review_required=False,
    )


def _authorization(**changes: object) -> SourceAuthorization:
    values: dict[str, object] = {
        "status": AuthorizationStatus.APPROVED,
        "document_reference": "SA16-L13-TEST",
        "reviewed_at": NOW,
        "expires_at": NOW + timedelta(days=30),
        "approved_hosts": frozenset({"example.org"}),
        "approved_path_prefixes": ("/public/",),
        "approved_purposes": frozenset({"public-form-research"}),
        "automated_collection_allowed": True,
    }
    values.update(changes)
    return SourceAuthorization(**values)  # type: ignore[arg-type]


def _request(method: HttpMethod) -> CollectionRequest:
    return CollectionRequest(
        data_category=DataCategory.PUBLIC_RESULT_METADATA,
        target_url="https://example.org/public/search",
        purpose="public-form-research",
        http_method=method,
    )


def test_historical_authorization_defaults_to_get_only() -> None:
    authorization = _authorization()

    assert authorization.approved_http_methods == frozenset({HttpMethod.GET})
    assert _evaluate(authorization, HttpMethod.GET).allowed is True
    assert _evaluate(authorization, HttpMethod.POST).reason is DecisionReason.METHOD_NOT_ALLOWED


def test_post_requires_explicit_method_authorization() -> None:
    authorization = _authorization(
        approved_http_methods=frozenset({HttpMethod.GET, HttpMethod.POST})
    )

    assert _evaluate(authorization, HttpMethod.POST).allowed is True


def test_registry_missing_method_key_remains_get_only(tmp_path: Path) -> None:
    path = tmp_path / "sources.yml"
    path.write_text(_registry_yaml(include_methods=False), encoding="utf-8")

    entry = load_source_registry(path)[0]

    assert entry.authorization.approved_http_methods == frozenset({HttpMethod.GET})


def test_registry_explicit_methods_are_persisted(tmp_path: Path) -> None:
    path = tmp_path / "sources.yml"
    path.write_text(_registry_yaml(include_methods=True), encoding="utf-8")
    entry = load_source_registry(path)[0]
    factory = _factory()

    with factory() as session:
        assert sync_source_registry(session, (entry,)) == 1
        session.commit()
        record = session.get(SourceRecord, "public-form")
        assert record is not None
        assert record.approved_http_methods == ["GET", "POST"]


def _evaluate(
    authorization: SourceAuthorization,
    method: HttpMethod,
):
    return _policy().evaluate(
        _request(method),
        authorization,
        SourceRuntimeState(remaining_requests=10),
        now=NOW,
    )


def _factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    get_metadata().create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _registry_yaml(*, include_methods: bool) -> str:
    method_line = "      approved_http_methods: [GET, POST]\n" if include_methods else ""
    return (
        "version: 1\n"
        "sources:\n"
        "  - id: public-form\n"
        "    name: Public form\n"
        "    base_url: https://example.org/public/\n"
        "    status: enabled\n"
        "    source_type: browser\n"
        "    owner: Example\n"
        "    terms_url: https://example.org/terms\n"
        "    licence: null\n"
        "    allowed_data_categories: [public_result_metadata]\n"
        "    prohibited_data_categories: []\n"
        "    rate_limit_per_minute: 10\n"
        "    retention_days: 30\n"
        "    attribution_required: false\n"
        "    raw_content_storage: false\n"
        "    human_review_required: false\n"
        "    authorization:\n"
        "      status: approved\n"
        "      document_reference: SA16-L13-TEST\n"
        "      reviewed_at: '2026-08-16T12:00:00+00:00'\n"
        "      expires_at: null\n"
        "      approved_hosts: [example.org]\n"
        "      approved_path_prefixes: [/public/]\n"
        "      approved_purposes: [public-form-research]\n"
        f"{method_line}"
        "      automated_collection_allowed: true\n"
        "      raw_storage_allowed: false\n"
        "    economics: {}\n"
    )
