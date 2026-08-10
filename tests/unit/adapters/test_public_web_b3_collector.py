from __future__ import annotations

from datetime import UTC, datetime, timedelta
from io import BytesIO
from uuid import UUID

import httpx
from pypdf import PdfWriter

from cip.adapters.sources.public_web.client import PublicWebClient
from cip.adapters.sources.public_web.collector import collect_public_web_target
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.public_footprint.domain.models import (
    DiscoveryMethod,
    PublicResourceKind,
)
from cip.modules.source_governance.domain.models import (
    AuthorizationStatus,
    DataCategory,
    SourceAuthorization,
    SourcePolicy,
    SourceStatus,
    SourceType,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry

NOW = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
ORG_ID = UUID("00000000-0000-0000-0000-000000000841")
JOB_ID = UUID("00000000-0000-0000-0000-000000000842")


def test_feed_security_txt_and_pdf_share_existing_public_web_collector() -> None:
    pdf_body = _pdf()
    requested_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        if request.url.path == "/robots.txt":
            return _response("text/plain", b"User-agent: *\nAllow: /\n")
        if request.url.path == "/public/feed.xml":
            return _response(
                "application/rss+xml",
                b"<rss version='2.0'><channel><item>"
                b"<link>https://example.com/public/report.pdf</link>"
                b"</item></channel></rss>",
            )
        if request.url.path == "/.well-known/security.txt":
            return _response(
                "text/plain",
                b"Contact: mailto:security@example.com\n"
                b"Canonical: https://example.com/.well-known/security.txt\n",
            )
        if request.url.path == "/public/report.pdf":
            return _response("application/pdf", pdf_body)
        raise AssertionError(f"unexpected request: {request.url}")

    target = _target()
    entry = _entry()
    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        batch = collect_public_web_target(
            PublicWebClient(http_client),
            entry,
            target,
            collection_job_id=JOB_ID,
            collected_at=NOW,
            retention_until=NOW + timedelta(days=365),
        )

    assert requested_paths == [
        "/robots.txt",
        "/public/feed.xml",
        "/.well-known/security.txt",
        "/public/report.pdf",
    ]
    assert len(batch.projections) == 2
    security, report = batch.projections
    assert security.resource.kind is PublicResourceKind.DOCUMENT
    assert security.resource.discovery_method is DiscoveryMethod.DIRECT
    assert security.claims == ()
    assert security.version.excerpt is not None
    assert "security@example.com" in security.version.excerpt
    assert report.resource.kind is PublicResourceKind.DOCUMENT
    assert report.resource.discovery_method is DiscoveryMethod.FEED
    assert report.resource.source_url == "https://example.com/public/feed.xml"
    assert len(batch.observations) == 2
    assert batch.not_modified is False


def _target() -> PublicWebTarget:
    return PublicWebTarget(
        id="public-web-test",
        organization_id=ORG_ID,
        canonical_name="Example",
        base_url="https://example.com",
        sitemap_urls=(),
        feed_urls=("https://example.com/public/feed.xml",),
        discover_security_txt=True,
        allowed_path_prefixes=("/public",),
        enabled=True,
        authorization_reference="test-authorization",
        authorization_reviewed_at=NOW - timedelta(days=1),
        max_pages=10,
        max_total_bytes=2_000_000,
        max_resource_bytes=1_000_000,
        max_redirects=2,
    )


def _entry() -> SourceRegistryEntry:
    policy = SourcePolicy(
        id="public-web-test",
        name="Public web test",
        base_url="https://example.com",
        status=SourceStatus.ENABLED,
        source_type=SourceType.STATIC_HTTP,
        owner="Example",
        allowed_data_categories=frozenset({DataCategory.OFFICIAL_DOCUMENT_DISCOVERY}),
        prohibited_data_categories=frozenset(
            {
                DataCategory.CREDENTIAL,
                DataCategory.VICTIM_FILE,
                DataCategory.PRIVATE_COMMUNICATION,
                DataCategory.PRIVATE_PERSONAL_DATA,
                DataCategory.RESTRICTED_CONTENT,
            }
        ),
        terms_url="https://example.com/terms",
        raw_content_storage=False,
        human_review_required=False,
    )
    authorization = SourceAuthorization(
        status=AuthorizationStatus.APPROVED,
        document_reference="test-authorization",
        reviewed_at=NOW - timedelta(days=1),
        approved_hosts=frozenset({"example.com"}),
        approved_path_prefixes=(
            "/robots.txt",
            "/public",
            "/.well-known/security.txt",
        ),
        approved_purposes=frozenset({"corporate-public-footprint"}),
        automated_collection_allowed=True,
        raw_storage_allowed=False,
    )
    return SourceRegistryEntry(policy=policy, authorization=authorization, economics={})


def _pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.add_metadata({"/Title": "Cloud security roadmap"})
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _response(content_type: str, body: bytes) -> httpx.Response:
    return httpx.Response(200, headers={"content-type": content_type}, content=body)
