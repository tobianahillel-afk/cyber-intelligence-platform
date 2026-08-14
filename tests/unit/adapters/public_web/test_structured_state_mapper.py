from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from cip.adapters.sources.public_web.mapper import map_public_page
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.adapters.sources.public_web.structured_fetch_result import (
    StructuredPublicWebFetchResult,
)
from cip.adapters.sources.public_web.structured_state_capture import CapturedStructuredState
from cip.modules.public_footprint.domain import PublicStructuredStateKind

_NOW = datetime(2026, 8, 14, 13, tzinfo=UTC)
_ORG_ID = UUID("abababab-abab-abab-abab-abababababab")


def test_mapper_attaches_network_and_script_state_to_exact_page_version() -> None:
    result = StructuredPublicWebFetchResult(
        requested_url="https://example.com/app",
        fetched_url="https://example.com/app",
        body=b"<html><body>rendered</body></html>",
        mime_type="text/html",
        etag=None,
        last_modified=None,
        redirects=0,
        structured_states=(
            CapturedStructuredState(
                kind=PublicStructuredStateKind.NETWORK_JSON,
                source_locator="https://example.com/api/state",
                source_url="https://example.com/api/state",
                http_status=200,
                media_type="application/json",
                payload_json='{"vendor":"Splunk"}',
            ),
            CapturedStructuredState(
                kind=PublicStructuredStateKind.SCRIPT_STATE,
                source_locator="window.__INITIAL_STATE__",
                extractor_id="public-known-globals-v1",
                payload_json='{"company":"Example"}',
            ),
        ),
    )

    mapped = map_public_page(
        _target(),
        result,
        collection_job_id=uuid4(),
        collected_at=_NOW,
        retention_until=_NOW + timedelta(days=30),
        previous=None,
    )

    assert len(mapped.projection.structured_states) == 2
    assert {state.kind for state in mapped.projection.structured_states} == {
        PublicStructuredStateKind.NETWORK_JSON,
        PublicStructuredStateKind.SCRIPT_STATE,
    }
    for state in mapped.projection.structured_states:
        assert state.organization_id == _ORG_ID
        assert state.resource_version_id == mapped.projection.version.id
        assert state.page_url == "https://example.com/app"
    network = next(
        state
        for state in mapped.projection.structured_states
        if state.kind is PublicStructuredStateKind.NETWORK_JSON
    )
    assert network.source_url == "https://example.com/api/state"
    assert network.http_status == 200


def _target() -> PublicWebTarget:
    return PublicWebTarget(
        id="structured-state-mapper-test",
        organization_id=_ORG_ID,
        canonical_name="Example",
        base_url="https://example.com/",
        sitemap_urls=(),
        seed_urls=("https://example.com/app",),
        allowed_path_prefixes=("/",),
        enabled=True,
        authorization_reference="approval:test",
        authorization_reviewed_at=_NOW - timedelta(days=1),
        authorization_expires_at=_NOW + timedelta(days=30),
        max_link_depth=0,
        max_pages=2,
        max_total_bytes=100_000,
        max_resource_bytes=50_000,
        max_redirects=1,
    )
