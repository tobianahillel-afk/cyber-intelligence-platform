from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from textwrap import dedent

import pytest

from cip.modules.source_governance.domain.models import (
    CollectionRequest,
    DataCategory,
    DecisionReason,
    SourceRuntimeState,
    SourceStatus,
)
from cip.modules.source_governance.infrastructure.registry import load_source_registry

NOW = datetime(2026, 8, 3, 16, 0, tzinfo=UTC)


def test_repository_source_registry_loads() -> None:
    entries = load_source_registry(Path("policies/sources.example.yml"))
    entries_by_id = {entry.policy.id: entry for entry in entries}

    assert set(entries_by_id) == {
        "boamp",
        "brixhub",
        "cisa-kev",
        "linkedin-authorized-browser",
        "linkedin-official-api",
        "search-manual-review",
        "ted-search",
    }
    for source_id in ("boamp", "cisa-kev", "ted-search"):
        assert entries_by_id[source_id].policy.status is SourceStatus.ENABLED
    for source_id in ("boamp", "ted-search"):
        assert entries_by_id[source_id].policy.allowed_data_categories == frozenset(
            {DataCategory.PUBLIC_TENDER, DataCategory.ORGANIZATION_METADATA}
        )
    assert entries_by_id["boamp"].policy.licence == "Licence Ouverte 2.0"
    assert entries_by_id["brixhub"].policy.status is SourceStatus.QUARANTINED
    assert entries_by_id["brixhub"].policy.allowed_data_categories == frozenset()


def test_cisa_registry_entry_allows_approved_feed_request() -> None:
    entry = next(
        item
        for item in load_source_registry(Path("policies/sources.example.yml"))
        if item.policy.id == "cisa-kev"
    )
    request = CollectionRequest(
        data_category=DataCategory.VULNERABILITY_METADATA,
        target_url=entry.policy.base_url,
        purpose="vulnerability-intelligence",
    )

    decision = entry.policy.evaluate(
        request,
        entry.authorization,
        SourceRuntimeState(remaining_requests=1),
        now=NOW,
    )

    assert decision.allowed is True


def test_quarantined_source_cannot_execute() -> None:
    entry = next(
        item
        for item in load_source_registry(Path("policies/sources.example.yml"))
        if item.policy.id == "brixhub"
    )
    request = CollectionRequest(
        data_category=DataCategory.ORGANIZATION_METADATA,
        target_url=entry.policy.base_url,
        purpose="commercial-research",
    )

    decision = entry.policy.evaluate(
        request,
        entry.authorization,
        SourceRuntimeState(),
        now=NOW,
    )

    assert decision.reason is DecisionReason.SOURCE_NOT_ENABLED


def test_missing_registry_file_is_reported(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_source_registry(tmp_path / "missing.yml")


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("- not-a-mapping\n", "root must be a mapping"),
        ("version: 2\nsources: []\n", "unsupported"),
        ("version: 1\nsources: {}\n", "sources must be a list"),
        ("version: 1\nsources: [invalid]\n", "each source must be a mapping"),
    ],
)
def test_invalid_registry_structure_is_rejected(
    tmp_path: Path,
    content: str,
    message: str,
) -> None:
    path = tmp_path / "sources.yml"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_source_registry(path)


def test_duplicate_source_ids_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "sources.yml"
    path.write_text(
        dedent(
            """
            version: 1
            sources:
              - &duplicate
                id: duplicate
                name: Duplicate
                base_url: https://example.org
                status: quarantined
                source_type: browser
                owner: Example
                allowed_data_categories: []
                prohibited_data_categories: []
                authorization:
                  status: missing
                  approved_hosts: []
                  approved_path_prefixes: []
                  approved_purposes: []
              - *duplicate
            """
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate ids"):
        load_source_registry(path)


def test_invalid_authorization_and_economics_are_rejected(tmp_path: Path) -> None:
    missing_authorization = tmp_path / "missing-authorization.yml"
    missing_authorization.write_text(
        dedent(
            """
            version: 1
            sources:
              - id: example
                name: Example
                base_url: https://example.org
                status: quarantined
                source_type: browser
                owner: Example
                allowed_data_categories: []
                prohibited_data_categories: []
            """
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="authorization"):
        load_source_registry(missing_authorization)

    bad_economics = tmp_path / "bad-economics.yml"
    bad_economics.write_text(
        dedent(
            """
            version: 1
            sources:
              - id: example
                name: Example
                base_url: https://example.org
                status: quarantined
                source_type: browser
                owner: Example
                allowed_data_categories: []
                prohibited_data_categories: []
                authorization:
                  status: missing
                  approved_hosts: []
                  approved_path_prefixes: []
                  approved_purposes: []
                economics: invalid
            """
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="economics"):
        load_source_registry(bad_economics)
