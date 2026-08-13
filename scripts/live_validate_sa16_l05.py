from __future__ import annotations

from base64 import urlsafe_b64encode
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import httpx

from cip.adapters.sources.public_web.client import PublicWebClient
from cip.adapters.sources.public_web.collector import collect_public_web_target
from cip.adapters.sources.public_web.provisioning import (
    AutomaticPublicWebPolicy,
    provision_public_web_target,
)
from cip.modules.organizations.domain.entities import Organization
from cip.modules.public_footprint.domain import ClaimEvidenceBasis

_ORG_ID = UUID("77777777-7777-7777-7777-777777777777")
_PUBLISHED_AT = datetime(2026, 8, 13, 8, 0, tzinfo=UTC)
_UPDATED_AT = datetime(2026, 8, 13, 8, 30, tzinfo=UTC)
_HTML = (
    b'<meta property="og:title" content="SA16 L05 Semantic Live">'
    b'<meta name="description" content="Zero Trust">'
    b'<meta property="article:published_time" content="2026-08-13T08:00:00Z">'
    b'<script type="application/ld+json">'
    b'{"description":"Kubernetes","dateModified":"2026-08-13T08:30:00Z"}'
    b"</script>"
)


def main() -> None:
    now = datetime.now(UTC)
    encoded = urlsafe_b64encode(_HTML).decode("ascii").rstrip("=")
    page_url = f"https://httpbingo.org/base64/{encoded}?content-type=text/html"
    organization = Organization(
        id=_ORG_ID,
        canonical_name="HTTPBingo semantic extraction test surface",
        website_url="https://httpbingo.org/",
        created_at=now,
        updated_at=now,
    )
    provisioned = provision_public_web_target(
        organization,
        AutomaticPublicWebPolicy(
            authorization_reference="sa16-l05-controlled-httpbingo-semantic",
            reviewed_at=now,
            allowed_path_prefixes=("/",),
            max_link_depth=0,
            discover_sitemaps=False,
            discover_feeds=False,
            max_sitemap_depth=0,
            max_sitemaps=1,
            max_feeds=1,
            max_pages=1,
            max_total_bytes=200_000,
            max_resource_bytes=100_000,
            max_redirects=0,
        ),
        first_crawl_at=now,
    )
    target = replace(
        provisioned.target,
        seed_urls=(page_url,),
        discover_security_txt=False,
        discover_sitemaps=False,
        discover_feeds=False,
    )
    with httpx.Client(timeout=30.0) as http_client:
        batch = collect_public_web_target(
            PublicWebClient(http_client),
            provisioned.source_entry,
            target,
            collection_job_id=uuid4(),
            collected_at=now,
            retention_until=now + timedelta(days=30),
        )

    if len(batch.observations) != 1 or len(batch.projections) != 1:
        raise RuntimeError("SA16-L05 live fetch did not produce one canonical projection")
    projection = batch.projections[0]
    version = projection.version
    if version.title != "SA16 L05 Semantic Live":
        raise RuntimeError("SA16-L05 live OpenGraph title was not mapped")
    if version.published_at != _PUBLISHED_AT or version.source_updated_at != _UPDATED_AT:
        raise RuntimeError("SA16-L05 live semantic timestamps were not mapped")

    claims = {claim.excerpt: claim for claim in projection.claims}
    zero_trust = claims.get("zero trust")
    kubernetes = claims.get("kubernetes")
    if zero_trust is None or zero_trust.evidence_basis is not ClaimEvidenceBasis.TARGET_CONTENT:
        raise RuntimeError("SA16-L05 live semantic metadata claim lost TARGET_CONTENT basis")
    if kubernetes is None or kubernetes.evidence_basis is not ClaimEvidenceBasis.STRUCTURED_DATA:
        raise RuntimeError("SA16-L05 live JSON-LD claim lost STRUCTURED_DATA basis")
    checkpoint = batch.checkpoint.pages.get(page_url)
    if checkpoint is None or checkpoint.extraction_profile != 2:
        raise RuntimeError("SA16-L05 live checkpoint did not persist extraction profile 2")
    print(
        "SA-16 L05 live validation passed: "
        f"title={version.title!r} claims={sorted(claims)} "
        f"published_at={version.published_at.isoformat()}"
    )


if __name__ == "__main__":
    main()
