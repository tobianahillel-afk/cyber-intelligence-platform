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
from cip.modules.public_footprint.domain import DiscoveryMethod

_ORG_ID = UUID("15712d0d-9054-50b4-8a26-e25d9ea1f509")
_TARGET_URL = "https://www.python.org/"
_MAX_PAGES = 6


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
            authorization_reference="sa16-l02-controlled-python-org-recursive-target",
            reviewed_at=now,
            allowed_path_prefixes=("/",),
            refresh_interval_seconds=86_400,
            max_depth=1,
            max_pages=_MAX_PAGES,
            max_total_bytes=4_000_000,
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
    linked = [
        projection
        for projection in batch.projections
        if projection.resource.discovery_method is DiscoveryMethod.LINK
    ]
    if homepage not in batch.checkpoint.pages:
        raise RuntimeError("SA16-L02 live crawl did not checkpoint the homepage seed")
    if not linked:
        raise RuntimeError("SA16-L02 live crawl did not fetch a same-origin linked child page")
    if len(batch.projections) > _MAX_PAGES:
        raise RuntimeError("SA16-L02 live crawl exceeded the page budget")
    if any(item.source_id != AUTOMATIC_PUBLIC_WEB_SOURCE_ID for item in batch.observations):
        raise RuntimeError("SA16-L02 observations lost governed source provenance")
    if any(
        projection.resource.source_id != AUTOMATIC_PUBLIC_WEB_SOURCE_ID
        for projection in batch.projections
    ):
        raise RuntimeError("SA16-L02 projections lost governed source provenance")
    if any(
        not projection.resource.canonical_url.startswith(_TARGET_URL)
        for projection in batch.projections
    ):
        raise RuntimeError("SA16-L02 recursive crawl escaped the approved origin")
    if any(
        projection.resource.source_url == homepage
        for projection in linked
    ):
        raise RuntimeError("SA16-L02 linked child lost its discovery source locator")

    print(
        "SA-16 L02 live validation passed: "
        f"organization={organization.canonical_name!r} target={provisioned.target.id} "
        f"source={AUTOMATIC_PUBLIC_WEB_SOURCE_ID} observations={len(batch.observations)} "
        f"projections={len(batch.projections)} linked_children={len(linked)} "
        f"checkpoint_pages={len(batch.checkpoint.pages)} max_depth={provisioned.target.max_depth}"
    )


if __name__ == "__main__":
    main()
