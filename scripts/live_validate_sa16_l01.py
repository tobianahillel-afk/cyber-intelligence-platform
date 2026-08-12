from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import httpx

from cip.adapters.sources.public_web.client import PublicWebClient
from cip.adapters.sources.public_web.collector import collect_public_web_target
from cip.adapters.sources.public_web.provisioning import (
    AUTOMATIC_PUBLIC_WEB_SOURCE_ID,
    AutomaticPublicWebPolicy,
    provision_public_web_target,
)
from cip.modules.organizations.domain.entities import Organization

_ORG_ID = UUID("15712d0d-9054-50b4-8a26-e25d9ea1f509")
_TARGET_URL = "https://www.python.org/"


def main() -> None:
    now = datetime.now(UTC)
    organization = Organization(
        id=_ORG_ID,
        canonical_name="Python Software Foundation",
        website_url=_TARGET_URL,
        created_at=now,
        updated_at=now,
    )
    provisioned = provision_public_web_target(
        organization,
        AutomaticPublicWebPolicy(
            authorization_reference="sa16-l01-controlled-python-org-public-target",
            reviewed_at=now,
            allowed_path_prefixes=("/",),
            refresh_interval_seconds=86_400,
            max_pages=2,
            max_total_bytes=2_000_000,
            max_resource_bytes=1_000_000,
            max_redirects=1,
        ),
        first_crawl_at=now,
    )
    with httpx.Client(timeout=30.0) as http_client:
        batch = collect_public_web_target(
            PublicWebClient(http_client),
            provisioned.source_entry,
            provisioned.target,
            collection_job_id=uuid4(),
            collected_at=now,
            retention_until=now + timedelta(days=365),
        )

    homepage = provisioned.target.seed_urls[0]
    if homepage not in batch.checkpoint.pages:
        raise RuntimeError("SA16-L01 live crawl did not checkpoint the generated homepage seed")
    if not batch.observations or not batch.projections:
        raise RuntimeError("SA16-L01 live crawl returned no public-web data")
    if any(item.source_id != AUTOMATIC_PUBLIC_WEB_SOURCE_ID for item in batch.observations):
        raise RuntimeError("SA16-L01 observations lost governed source provenance")
    if any(
        projection.resource.source_id != AUTOMATIC_PUBLIC_WEB_SOURCE_ID
        for projection in batch.projections
    ):
        raise RuntimeError("SA16-L01 projections lost governed source provenance")
    if any(
        not projection.resource.canonical_url.startswith(_TARGET_URL)
        for projection in batch.projections
    ):
        raise RuntimeError("SA16-L01 live crawl escaped the approved origin")

    print(
        "SA-16 L01 live validation passed: "
        f"organization={organization.canonical_name!r} target={provisioned.target.id} "
        f"source={AUTOMATIC_PUBLIC_WEB_SOURCE_ID} observations={len(batch.observations)} "
        f"projections={len(batch.projections)} homepage={homepage}"
    )


if __name__ == "__main__":
    main()
