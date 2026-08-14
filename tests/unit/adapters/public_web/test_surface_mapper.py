from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from cip.adapters.sources.public_web.client import PublicWebFetchResult
from cip.adapters.sources.public_web.mapper import PreviousPageState, map_public_page
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.public_footprint.domain import PublicSurfaceKind

_NOW = datetime(2026, 8, 14, 12, 30, tzinfo=UTC)
_ORG_ID = UUID("cdcdcdcd-cdcd-cdcd-cdcd-cdcdcdcdcdcd")


def test_new_page_projects_surfaces_and_unchanged_200_reuses_version() -> None:
    result = _html_result(
        b'<html><head><link rel="canonical" href="/canonical">'
        b'<script src="/app.js"></script></head><body>hello</body></html>'
    )
    first = map_public_page(
        _target(),
        result,
        collection_job_id=uuid4(),
        collected_at=_NOW,
        retention_until=_NOW + timedelta(days=30),
        previous=None,
    )
    assert {surface.kind for surface in first.projection.surfaces} == {
        PublicSurfaceKind.CANONICAL_LINK,
        PublicSurfaceKind.SCRIPT,
        PublicSurfaceKind.RESPONSE_HEADER,
    }

    previous = PreviousPageState(
        content_hash_sha256=first.content_hash_sha256,
        version_id=first.projection.version.id,
        canonical_url=first.projection.resource.canonical_url,
        resource_kind=first.projection.resource.kind,
        mime_type=first.projection.version.mime_type,
        byte_size=first.projection.version.byte_size,
    )
    replay = map_public_page(
        _target(),
        result,
        collection_job_id=uuid4(),
        collected_at=_NOW + timedelta(minutes=5),
        retention_until=_NOW + timedelta(days=30),
        previous=previous,
    )

    assert replay.observation is None
    assert replay.projection.version.id == first.projection.version.id
    assert replay.projection.surfaces == ()


def test_changed_page_gets_new_version_and_surface_inventory() -> None:
    first = map_public_page(
        _target(),
        _html_result(b"<html><body>first</body></html>"),
        collection_job_id=uuid4(),
        collected_at=_NOW,
        retention_until=_NOW + timedelta(days=30),
        previous=None,
    )
    previous = PreviousPageState(
        content_hash_sha256=first.content_hash_sha256,
        version_id=first.projection.version.id,
        canonical_url=first.projection.resource.canonical_url,
        resource_kind=first.projection.resource.kind,
        mime_type=first.projection.version.mime_type,
        byte_size=first.projection.version.byte_size,
    )
    changed = map_public_page(
        _target(),
        _html_result(b'<html><body>second<script src="/new.js"></script></body></html>'),
        collection_job_id=uuid4(),
        collected_at=_NOW + timedelta(minutes=5),
        retention_until=_NOW + timedelta(days=30),
        previous=previous,
    )

    assert changed.projection.version.id != first.projection.version.id
    assert changed.projection.version.supersedes_version_id == first.projection.version.id
    assert {surface.kind for surface in changed.projection.surfaces} == {
        PublicSurfaceKind.SCRIPT,
        PublicSurfaceKind.RESPONSE_HEADER,
    }


def _html_result(body: bytes) -> PublicWebFetchResult:
    return PublicWebFetchResult(
        requested_url="https://example.com/",
        fetched_url="https://example.com/",
        body=body,
        mime_type="text/html",
        etag=None,
        last_modified=None,
        redirects=0,
        response_headers=(("server", "fixture"),),
    )


def _target() -> PublicWebTarget:
    return PublicWebTarget(
        id="surface-mapper-test",
        organization_id=_ORG_ID,
        canonical_name="Example",
        base_url="https://example.com/",
        sitemap_urls=(),
        seed_urls=("https://example.com/",),
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
