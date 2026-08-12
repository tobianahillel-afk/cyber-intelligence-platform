from __future__ import annotations

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
from cip.modules.public_footprint.domain import ResourceRetrievalState

_ORG_ID = UUID("c26cffc5-02bc-5b72-850d-b20c6c88b4c5")
_ETAG_URL = "https://httpbin.org/etag/sa16-l04"


def main() -> None:
    now = datetime.now(UTC)
    organization = Organization(
        id=_ORG_ID,
        canonical_name="HTTPBin conditional request test surface",
        website_url="https://httpbin.org/",
        created_at=now,
        updated_at=now,
    )
    provisioned = provision_public_web_target(
        organization,
        AutomaticPublicWebPolicy(
            authorization_reference="sa16-l04-controlled-httpbin-etag",
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
        seed_urls=(_ETAG_URL,),
        discover_security_txt=False,
        discover_sitemaps=False,
        discover_feeds=False,
    )
    with httpx.Client(timeout=30.0) as http_client:
        client = PublicWebClient(http_client)
        first = collect_public_web_target(
            client,
            provisioned.source_entry,
            target,
            collection_job_id=uuid4(),
            collected_at=now,
            retention_until=now + timedelta(days=30),
        )
        first_state = first.checkpoint.pages[_ETAG_URL]
        if first_state.etag is None:
            raise RuntimeError("SA16-L04 live surface did not provide an ETag")
        if len(first.observations) != 1 or len(first.projections) != 1:
            raise RuntimeError("SA16-L04 initial live fetch did not persist one representation")

        second = collect_public_web_target(
            client,
            provisioned.source_entry,
            target,
            collection_job_id=uuid4(),
            collected_at=now + timedelta(minutes=1),
            retention_until=now + timedelta(days=30),
            checkpoint=first.checkpoint,
        )
    second_state = second.checkpoint.pages[_ETAG_URL]
    if not second.not_modified or second.observations:
        raise RuntimeError("SA16-L04 live recrawl did not resolve to not-modified")
    if len(second.projections) != 1:
        raise RuntimeError("SA16-L04 live recrawl lost the resource projection")
    if second.projections[0].resource.retrieval_state is not ResourceRetrievalState.NOT_MODIFIED:
        raise RuntimeError("SA16-L04 live recrawl did not map HTTP 304 to NOT_MODIFIED")
    if second_state.version_id != first_state.version_id:
        raise RuntimeError("SA16-L04 live 304 created a replacement content version")
    if second_state.content_hash_sha256 != first_state.content_hash_sha256:
        raise RuntimeError("SA16-L04 live 304 changed the representation hash")
    print(
        "SA-16 L04 live validation passed: "
        f"etag={first_state.etag!r} observations_first={len(first.observations)} "
        f"observations_second={len(second.observations)}"
    )


if __name__ == "__main__":
    main()
