from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from cip.adapters.sources.public_web.client import PublicWebFetchResult
from cip.adapters.sources.public_web.mapper import map_public_page
from cip.adapters.sources.public_web.provisioning import (
    AutomaticPublicWebPolicy,
    provision_public_web_target,
)
from cip.adapters.sources.public_web.semantic_html import extract_semantic_html
from cip.modules.organizations.domain.entities import Organization
from cip.modules.public_footprint.domain import ClaimEvidenceBasis

_NOW = datetime(2026, 8, 13, 8, 30, tzinfo=UTC)
_ORG_ID = UUID("55555555-5555-5555-5555-555555555555")


def test_extracts_bounded_semantic_and_jsonld_without_sensitive_values() -> None:
    body = b"""
    <html>
      <head>
        <meta property="og:title" content="Example Security Platform">
        <meta name="description" content="Zero Trust architecture for public workloads">
        <meta property="article:published_time" content="2026-08-01T12:00:00Z">
        <meta property="article:modified_time" content="2026-08-02T13:30:00+02:00">
        <script type="application/ld+json">
          {
            "@type": "SoftwareApplication",
            "name": "Example App",
            "description": "Runs Kubernetes for public workloads",
            "apiToken": "DO-NOT-INDEX-THIS-TOKEN",
            "datePublished": "2026-07-20",
            "dateModified": "2026-07-21T10:00:00Z"
          }
        </script>
      </head>
      <body>Visible body</body>
    </html>
    """

    extracted = extract_semantic_html(body)

    assert extracted.preferred_title == "Example Security Platform"
    assert "Zero Trust architecture for public workloads" in extracted.semantic_text
    assert "SoftwareApplication" in extracted.structured_text
    assert "Kubernetes" in extracted.structured_text
    assert "DO-NOT-INDEX-THIS-TOKEN" not in extracted.structured_text
    assert extracted.published_at == datetime(2026, 8, 1, 12, 0, tzinfo=UTC)
    assert extracted.source_updated_at == datetime(2026, 8, 2, 11, 30, tzinfo=UTC)
    assert extracted.structured_record_count == 1


def test_malformed_or_irrelevant_json_does_not_break_semantic_extraction() -> None:
    body = b"""
    <html><head>
      <meta property="og:description" content="Public description">
      <script type="application/ld+json">{"name":</script>
      <script type="text/javascript">window.secret = "ignored";</script>
    </head></html>
    """

    extracted = extract_semantic_html(body)

    assert extracted.semantic_text == "Public description"
    assert extracted.structured_text == ""
    assert extracted.structured_record_count == 0


def test_mapper_keeps_structured_claim_basis_and_semantic_source_timestamps() -> None:
    target = _target()
    body = b"""
    <html lang="en"><head>
      <meta property="og:title" content="Structured Security Evidence">
      <meta name="description" content="Our Zero Trust programme">
      <meta property="article:published_time" content="2026-08-03T09:00:00Z">
      <meta property="article:modified_time" content="2026-08-04T10:00:00Z">
      <script type="application/ld+json">
        {"@type":"TechArticle","description":"Platform architecture uses Kubernetes"}
      </script>
    </head><body>General company information.</body></html>
    """
    result = PublicWebFetchResult(
        requested_url="https://example.com/security",
        fetched_url="https://example.com/security",
        body=body,
        mime_type="text/html",
        etag=None,
        last_modified=None,
        redirects=0,
    )

    mapped = map_public_page(
        target,
        result,
        collection_job_id=uuid4(),
        collected_at=_NOW,
        retention_until=_NOW + timedelta(days=30),
        previous=None,
    )

    version = mapped.projection.version
    claims_by_excerpt = {claim.excerpt: claim for claim in mapped.projection.claims}
    assert version.title == "Structured Security Evidence"
    assert version.language == "en"
    assert version.published_at == datetime(2026, 8, 3, 9, 0, tzinfo=UTC)
    assert version.source_updated_at == datetime(2026, 8, 4, 10, 0, tzinfo=UTC)
    assert claims_by_excerpt["zero trust"].evidence_basis is ClaimEvidenceBasis.TARGET_CONTENT
    assert claims_by_excerpt["kubernetes"].evidence_basis is ClaimEvidenceBasis.STRUCTURED_DATA


def test_noindex_suppresses_semantic_and_structured_claims() -> None:
    target = _target()
    result = PublicWebFetchResult(
        requested_url="https://example.com/private-indexing",
        fetched_url="https://example.com/private-indexing",
        body=(
            b'<html><head><meta name="robots" content="noindex">'
            b'<meta name="description" content="Zero Trust">'
            b'<script type="application/ld+json">'
            b'{"description":"Kubernetes"}'
            b"</script></head><body>Visible page</body></html>"
        ),
        mime_type="text/html",
        etag=None,
        last_modified=None,
        redirects=0,
    )

    mapped = map_public_page(
        target,
        result,
        collection_job_id=uuid4(),
        collected_at=_NOW,
        retention_until=_NOW + timedelta(days=30),
        previous=None,
    )

    assert mapped.projection.claims == ()
    assert mapped.projection.version.extracted_text_hash_sha256 is None


def _target():
    organization = Organization(
        id=_ORG_ID,
        canonical_name="Example",
        website_url="https://example.com/",
        created_at=_NOW,
        updated_at=_NOW,
    )
    provisioned = provision_public_web_target(
        organization,
        AutomaticPublicWebPolicy(
            authorization_reference="sa16-l05-semantic-test",
            reviewed_at=_NOW,
            allowed_path_prefixes=("/",),
            max_link_depth=0,
            discover_sitemaps=False,
            discover_feeds=False,
            max_pages=2,
            max_total_bytes=100_000,
            max_resource_bytes=50_000,
            max_redirects=0,
        ),
        first_crawl_at=_NOW,
    )
    return provisioned.target
