from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from cip.adapters.sources.marginalia_search.registry import (
    load_marginalia_search_entitlement,
)
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.collection_orchestration.application.marginalia_search_adapter import (
    MarginaliaSearchAdapter,
)
from cip.modules.collection_orchestration.application.ports import AdapterCollectionBatch
from cip.modules.public_footprint.domain.models import PublicResourceKind, ResourceRetrievalState
from cip.modules.public_footprint.domain.search import SearchQueryTemplate
from cip.modules.source_governance.infrastructure.registry import load_source_registry

_POLICY_PATH = Path("policies/sources.search_providers_sa15.yml")
_ENTITLEMENT_PATH = Path("policies/marginalia_search_entitlement.yml")
_ORG_ID = UUID("314457e3-e3d9-5c9a-b112-c5747b14f216")
_MAX_RESULTS = 20


def main() -> None:
    entitlement = load_marginalia_search_entitlement(_ENTITLEMENT_PATH)
    target = _controlled_target()
    template = SearchQueryTemplate(
        id="sa15-controlled-independent-search",
        version=1,
        query_pattern="{organization} cybersecurity",
        purpose="corporate-public-footprint",
        enabled=True,
    )
    entry = next(
        item
        for item in load_source_registry(_POLICY_PATH)
        if item.policy.id == "marginalia-web-search-metadata"
    )
    now = datetime.now(UTC)
    batch = MarginaliaSearchAdapter(
        entry,
        (target,),
        (template,),
        entitlement,
        token_provider=lambda: _required_env("MARGINALIA_API_KEY"),
        timeout_seconds=60,
    ).collect(
        collection_job_id=uuid4(),
        checkpoint_payload=None,
        collected_at=now,
        retention_until=now + timedelta(days=90),
    )
    _validate_batch(batch)
    print(
        "SA-15 L06 live validation passed: "
        f"organization={target.canonical_name!r} "
        f"marginalia_observations={len(batch.observations)} "
        f"marginalia_projections={len(batch.public_footprint_projections)} claims=0 bodies=0"
    )


def _controlled_target() -> PublicWebTarget:
    name = os.environ.get("SA15_SEARCH_ORGANIZATION", "Internet Archive").strip()
    base_url = os.environ.get("SA15_SEARCH_ORGANIZATION_URL", "https://archive.org/").strip()
    if not name or not base_url:
        raise RuntimeError("controlled search organization name and URL are required")
    now = datetime.now(UTC)
    return PublicWebTarget(
        id="sa15-controlled-marginalia-search-organization",
        organization_id=_ORG_ID,
        canonical_name=name,
        base_url=base_url,
        sitemap_urls=(),
        feed_urls=(),
        seed_urls=(base_url,),
        discover_security_txt=False,
        allowed_path_prefixes=("/",),
        enabled=True,
        authorization_reference="sa15-controlled-public-search-validation",
        authorization_reviewed_at=now,
        terms_url=base_url,
        max_pages=_MAX_RESULTS,
        max_total_bytes=2_000_000,
        max_resource_bytes=1_000_000,
        max_redirects=0,
    )


def _validate_batch(batch: AdapterCollectionBatch) -> None:
    observations = batch.observations
    projections = batch.public_footprint_projections
    if not 1 <= len(observations) <= _MAX_RESULTS or len(projections) != len(observations):
        raise RuntimeError("Marginalia live validation returned invalid result counts")
    if any(
        observation.source_id != "marginalia-web-search-metadata"
        for observation in observations
    ):
        raise RuntimeError("Marginalia live validation lost source provenance")
    if any(projection.claims for projection in projections):
        raise RuntimeError("Marginalia search metadata unexpectedly produced claims")
    if any(
        projection.resource.kind is not PublicResourceKind.SEARCH_RESULT
        or projection.resource.retrieval_state is not ResourceRetrievalState.QUARANTINED
        for projection in projections
    ):
        raise RuntimeError("Marginalia search results escaped discovery quarantine")
    if batch.checkpoint_payload != {"pair_index": 0}:
        raise RuntimeError("Marginalia live validation checkpoint did not converge")


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required for controlled live validation")
    return value


if __name__ == "__main__":
    main()
