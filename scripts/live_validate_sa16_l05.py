from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, uuid4, uuid5

import httpx

from cip.adapters.sources.public_web.client import PublicWebClient
from cip.adapters.sources.public_web.collector import collect_public_web_target
from cip.adapters.sources.public_web.provisioning import (
    AutomaticPublicWebPolicy,
    provision_public_web_target,
)
from cip.modules.organizations.domain.entities import Organization
from cip.modules.public_footprint.domain import ClaimEvidenceBasis

_CANDIDATES = (
    (
        "Google Kubernetes Engine documentation",
        "https://docs.cloud.google.com/kubernetes-engine/docs?hl=en",
    ),
    (
        "Amazon EKS documentation",
        "https://docs.aws.amazon.com/eks/latest/userguide/",
    ),
    (
        "Kubernetes documentation",
        "https://kubernetes.io/docs/home/",
    ),
)


def main() -> None:
    diagnostics: list[str] = []
    with httpx.Client(timeout=30.0) as http_client:
        for name, page_url in _CANDIDATES:
            try:
                result = _validate_candidate(http_client, name=name, page_url=page_url)
            except (httpx.HTTPError, RuntimeError, ValueError) as exc:
                diagnostics.append(f"{name}: {type(exc).__name__}: {exc}")
                continue
            print(result)
            return
    raise RuntimeError(
        "SA16-L05 live validation found no natural public HTML page with "
        f"structured-data evidence; diagnostics={diagnostics}"
    )


def _validate_candidate(http_client: httpx.Client, *, name: str, page_url: str) -> str:
    now = datetime.now(UTC)
    organization = Organization(
        id=uuid5(NAMESPACE_URL, page_url),
        canonical_name=name,
        website_url=page_url,
        created_at=now,
        updated_at=now,
    )
    provisioned = provision_public_web_target(
        organization,
        AutomaticPublicWebPolicy(
            authorization_reference=f"sa16-l05-controlled-{organization.id.hex}",
            reviewed_at=now,
            allowed_path_prefixes=("/",),
            max_link_depth=0,
            discover_sitemaps=False,
            discover_feeds=False,
            max_sitemap_depth=0,
            max_sitemaps=1,
            max_feeds=1,
            max_pages=1,
            max_total_bytes=2_000_000,
            max_resource_bytes=2_000_000,
            max_redirects=3,
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
    batch = collect_public_web_target(
        PublicWebClient(http_client),
        provisioned.source_entry,
        target,
        collection_job_id=uuid4(),
        collected_at=now,
        retention_until=now + timedelta(days=30),
    )
    if not batch.observations or not batch.projections:
        raise RuntimeError("natural HTML fetch produced no canonical projection")

    structured_claims = tuple(
        claim
        for projection in batch.projections
        for claim in projection.claims
        if claim.evidence_basis is ClaimEvidenceBasis.STRUCTURED_DATA
    )
    if not structured_claims:
        raise RuntimeError("page produced no STRUCTURED_DATA claim")
    if not any(
        page.extraction_profile == 2 for page in batch.checkpoint.pages.values()
    ):
        raise RuntimeError("checkpoint did not persist extraction profile 2")

    projection = batch.projections[0]
    if not projection.version.title:
        raise RuntimeError("natural HTML projection did not preserve a title")
    excerpts = sorted({claim.excerpt for claim in structured_claims})
    return (
        "SA-16 L05 live validation passed: "
        f"surface={name!r} url={projection.resource.canonical_url!r} "
        f"title={projection.version.title!r} structured_claims={excerpts}"
    )


if __name__ == "__main__":
    main()
