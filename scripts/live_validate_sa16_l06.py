from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, uuid4, uuid5

import httpx

from cip.adapters.sources.public_web.client import PublicWebClient
from cip.adapters.sources.public_web.collector import collect_public_web_target
from cip.adapters.sources.public_web.ooxml_parsing import DOCX_MIME
from cip.adapters.sources.public_web.provisioning import (
    AutomaticPublicWebPolicy,
    provision_public_web_target,
)
from cip.modules.organizations.domain.entities import Organization
from cip.modules.public_footprint.domain import PublicResourceKind

_DOCX_URL = (
    "https://dm-publicapi.eesc.europa.eu/v1/documents/"
    "EESC-2020-05749-00-00-AC-TRA-EN.docx/content"
)
_BASE_URL = "https://dm-publicapi.eesc.europa.eu/"


def main() -> None:
    now = datetime.now(UTC)
    organization = Organization(
        id=uuid5(NAMESPACE_URL, _BASE_URL),
        canonical_name="European Economic and Social Committee public documents",
        website_url=_BASE_URL,
        created_at=now,
        updated_at=now,
    )
    provisioned = provision_public_web_target(
        organization,
        AutomaticPublicWebPolicy(
            authorization_reference="sa16-l06-controlled-eesc-public-docx",
            reviewed_at=now,
            allowed_path_prefixes=("/robots.txt", "/v1/documents"),
            max_link_depth=0,
            discover_sitemaps=False,
            discover_feeds=False,
            max_sitemap_depth=0,
            max_sitemaps=1,
            max_feeds=1,
            max_pages=1,
            max_total_bytes=5_000_000,
            max_resource_bytes=5_000_000,
            max_redirects=2,
        ),
        first_crawl_at=now,
    )
    target = replace(
        provisioned.target,
        seed_urls=(_DOCX_URL,),
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
        raise RuntimeError("SA16-L06 live DOCX did not produce one canonical projection")
    projection = batch.projections[0]
    version = projection.version
    if projection.resource.kind is not PublicResourceKind.DOCUMENT:
        raise RuntimeError("SA16-L06 live OOXML resource was not classified as DOCUMENT")
    if version.mime_type != DOCX_MIME:
        raise RuntimeError(f"SA16-L06 live response MIME was {version.mime_type!r}")
    if version.byte_size <= 0 or version.byte_size > 5_000_000:
        raise RuntimeError("SA16-L06 live DOCX violated the bounded document size contract")
    if version.extracted_text_hash_sha256 is None or not version.excerpt:
        raise RuntimeError("SA16-L06 live DOCX produced no bounded extracted text")
    checkpoint = batch.checkpoint.pages.get(_DOCX_URL)
    if checkpoint is None or checkpoint.mime_type != DOCX_MIME:
        raise RuntimeError("SA16-L06 live DOCX representation was not checkpointed")
    print(
        "SA-16 L06 live validation passed: "
        f"url={projection.resource.canonical_url!r} "
        f"mime={version.mime_type!r} bytes={version.byte_size} "
        f"title={version.title!r} excerpt={version.excerpt[:120]!r}"
    )


if __name__ == "__main__":
    main()
