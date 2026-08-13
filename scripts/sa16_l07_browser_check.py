from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, uuid4, uuid5

from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.collection_orchestration.application.public_web_browser_adapter import (
    PublicWebBrowserAdapter,
)
from cip.modules.public_footprint.domain import PublicResourceKind
from cip.modules.source_governance.domain.models import (
    AuthorizationStatus,
    DataCategory,
    SourceAuthorization,
    SourcePolicy,
    SourceStatus,
    SourceType,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry

_TARGET_URL = "https://www.selenium.dev/selenium/web/javascriptPage.html"
_BASE_URL = "https://www.selenium.dev/"
_SOURCE_ID = "sa16-l07-selenium-browser-proof"


def main() -> None:
    now = datetime.now(UTC)
    target = _target(now)
    adapter = PublicWebBrowserAdapter(_entry(target, now), target, timeout_seconds=30.0)
    batch = adapter.collect(
        collection_job_id=uuid4(),
        checkpoint_payload=None,
        collected_at=now,
        retention_until=now + timedelta(days=30),
    )
    if len(batch.observations) != 1 or len(batch.public_footprint_projections) != 1:
        raise RuntimeError("SA16-L07 live browser did not produce one canonical projection")
    observation = batch.observations[0]
    projection = batch.public_footprint_projections[0]
    if observation.adapter_id != "public-web-browser":
        raise RuntimeError("SA16-L07 live observation lost browser adapter provenance")
    if projection.resource.kind is not PublicResourceKind.WEB_PAGE:
        raise RuntimeError("SA16-L07 live rendered resource was not classified as WEB_PAGE")
    if projection.version.mime_type != "text/html":
        raise RuntimeError("SA16-L07 live rendered representation was not HTML")
    if projection.version.byte_size <= 0 or projection.version.byte_size > 1_000_000:
        raise RuntimeError("SA16-L07 live rendered DOM violated the size contract")
    if projection.version.extracted_text_hash_sha256 is None or not projection.version.excerpt:
        raise RuntimeError("SA16-L07 live rendered DOM produced no canonical extracted text")
    pages = batch.checkpoint_payload.get("pages")
    if not isinstance(pages, dict) or _TARGET_URL not in pages:
        raise RuntimeError("SA16-L07 live rendered page was not checkpointed")
    print(
        "SA-16 L07 live validation passed: "
        f"url={projection.resource.canonical_url!r} "
        f"mime={projection.version.mime_type!r} bytes={projection.version.byte_size} "
        f"adapter={observation.adapter_id!r} excerpt={projection.version.excerpt[:120]!r}"
    )


def _target(now: datetime) -> PublicWebTarget:
    return PublicWebTarget(
        id=_SOURCE_ID,
        source_id=_SOURCE_ID,
        organization_id=uuid5(NAMESPACE_URL, _BASE_URL),
        canonical_name="Selenium browser automation test surface",
        base_url=_BASE_URL,
        seed_urls=(_TARGET_URL,),
        sitemap_urls=(),
        feed_urls=(),
        discover_security_txt=False,
        discover_sitemaps=False,
        discover_feeds=False,
        allowed_path_prefixes=("/",),
        enabled=True,
        authorization_reference="sa16-l07-controlled-selenium-public-browser",
        authorization_reviewed_at=now,
        max_link_depth=0,
        max_pages=1,
        max_total_bytes=1_000_000,
        max_resource_bytes=1_000_000,
        max_redirects=2,
    )


def _entry(target: PublicWebTarget, now: datetime) -> SourceRegistryEntry:
    return SourceRegistryEntry(
        policy=SourcePolicy(
            id=_SOURCE_ID,
            name="SA16-L07 controlled Selenium browser proof",
            base_url=_BASE_URL,
            status=SourceStatus.ENABLED,
            source_type=SourceType.BROWSER,
            owner="Selenium project",
            licence="Public Selenium browser test surface used for controlled validation",
            allowed_data_categories=frozenset(
                {
                    DataCategory.OFFICIAL_DOCUMENT_DISCOVERY,
                    DataCategory.TECHNOLOGY_OBSERVATION,
                }
            ),
            retention_days=30,
            attribution_required=True,
            raw_content_storage=False,
            human_review_required=False,
        ),
        authorization=SourceAuthorization(
            status=AuthorizationStatus.APPROVED,
            document_reference="sa16-l07-controlled-selenium-public-browser",
            reviewed_at=now,
            approved_hosts=frozenset({target.host}),
            approved_path_prefixes=("/",),
            approved_purposes=frozenset({"corporate-public-footprint"}),
            automated_collection_allowed=True,
            raw_storage_allowed=False,
        ),
        economics={"monthly_cost": 0},
        notes="Neutral public browser-automation fixture for exact-head live validation.",
    )


if __name__ == "__main__":
    main()
