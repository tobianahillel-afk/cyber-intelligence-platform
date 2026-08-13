from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, uuid4, uuid5

import httpx

from cip.adapters.sources.public_web.browser_fallback import (
    BrowserFallbackPolicy,
    FallbackPublicWebClient,
)
from cip.adapters.sources.public_web.browser_fallback_governance import (
    AutomaticBrowserFallbackPolicy,
    build_browser_fallback_entry,
)
from cip.adapters.sources.public_web.provisioning import (
    AUTOMATIC_PUBLIC_WEB_SOURCE_ID,
    AutomaticPublicWebPolicy,
    provision_public_web_target,
)
from cip.modules.collection_orchestration.application.automatic_public_web_runtime import (
    AutomaticPublicWebRuntimeConfig,
    build_automatic_public_web_runtime,
)
from cip.modules.collection_orchestration.application.public_web_fallback_adapter import (
    PublicWebFallbackAdapter,
)
from cip.modules.organizations.domain.entities import Organization
from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.modules.public_footprint.domain.scope import CrawlUsage
from cip.shared.persistence.metadata import get_metadata
from cip.shared.persistence.session import (
    create_database_engine,
    create_session_factory,
    session_scope,
)

_STATIC_TARGETS = (
    ("Example COM", "https://example.com/"),
    ("Example ORG", "https://example.org/"),
    ("Example NET", "https://example.net/"),
    ("Python", "https://www.python.org/"),
    ("Python Docs", "https://docs.python.org/"),
    ("PyPI", "https://pypi.org/"),
    ("Django", "https://www.djangoproject.com/"),
    ("FreeBSD", "https://www.freebsd.org/"),
    ("Go", "https://go.dev/"),
    ("Node.js", "https://nodejs.org/"),
    ("Kubernetes", "https://kubernetes.io/"),
    ("PostgreSQL", "https://www.postgresql.org/"),
    ("SQLite", "https://sqlite.org/"),
    ("Linux Kernel", "https://www.kernel.org/"),
    ("W3C", "https://www.w3.org/"),
    ("IETF", "https://www.ietf.org/"),
    ("RFC Editor", "https://www.rfc-editor.org/"),
    ("curl", "https://curl.se/"),
    ("Debian", "https://www.debian.org/"),
)
_SELENIUM_ORIGIN = "https://www.selenium.dev/"
_SELENIUM_FIXTURE = "https://www.selenium.dev/selenium/web/javascriptPage.html"


def main() -> None:
    now = datetime.now(UTC)
    static_successes = _validate_automatic_runtime(now)
    _validate_forced_browser_fallback(now)
    total = static_successes + 1
    if total != 20:
        raise RuntimeError(f"SA16-L09 expected 20 validated targets, got {total}")
    print(
        "SA-16 L09 live validation passed: "
        f"targets={total} forced_browser=1 runtime_targets={static_successes}",
        flush=True,
    )


def _validate_automatic_runtime(now: datetime) -> int:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    get_metadata().create_all(engine)
    factory = create_session_factory(engine)
    organization_ids = tuple(uuid5(NAMESPACE_URL, url) for _, url in _STATIC_TARGETS)
    with session_scope(factory) as session:
        session.add_all(
            _organization_record(name, url, now) for name, url in _STATIC_TARGETS
        )
    config = AutomaticPublicWebRuntimeConfig(
        enabled=True,
        organization_ids=organization_ids,
        authorization_reference="sa16-l09-static-live-approval",
        reviewed_at=now,
        refresh_interval_seconds=86_400,
        max_link_depth=0,
        max_pages=2,
        max_total_bytes=2_000_000,
        max_resource_bytes=1_000_000,
        max_redirects=3,
        browser_fallback_enabled=True,
        browser_authorization_reference="sa16-l09-browser-live-approval",
        browser_reviewed_at=now,
        browser_min_static_text_chars=1,
        browser_max_pages=1,
    )
    with session_scope(factory) as session:
        bundle = build_automatic_public_web_runtime(
            session,
            config,
            now=now,
            timeout_seconds=30.0,
        )
    if len(bundle.targets) != len(_STATIC_TARGETS):
        raise RuntimeError("SA16-L09 runtime did not build every approved target")
    targets_by_id = {target.id: target for target in bundle.targets}
    successes = 0
    for schedule in bundle.schedules:
        identity = (schedule.source_id, schedule.adapter_id)
        adapter = bundle.adapters.get(identity)
        target = targets_by_id.get(schedule.source_id)
        if adapter is None or target is None:
            raise RuntimeError(f"SA16-L09 missing runtime binding: {identity}")
        if adapter.adapter_id != "public-web-browser-fallback":
            raise RuntimeError("SA16-L09 runtime did not select fallback-capable adapter")
        print(f"SA16-L09 testing static-first target: {target.base_url}", flush=True)
        batch = adapter.collect(
            collection_job_id=uuid4(),
            checkpoint_payload=None,
            collected_at=now,
            retention_until=now + timedelta(days=30),
        )
        pages = batch.checkpoint_payload.get("pages")
        if not isinstance(pages, dict) or target.base_url not in pages:
            raise RuntimeError(f"SA16-L09 homepage not checkpointed: {target.base_url}")
        if not batch.observations or not batch.public_footprint_projections:
            raise RuntimeError(f"SA16-L09 produced no data: {target.base_url}")
        if any(
            observation.source_id != AUTOMATIC_PUBLIC_WEB_SOURCE_ID
            for observation in batch.observations
        ):
            raise RuntimeError(f"SA16-L09 lost source provenance: {target.base_url}")
        if any(
            not projection.resource.canonical_url.startswith(target.base_url)
            for projection in batch.public_footprint_projections
        ):
            raise RuntimeError(f"SA16-L09 escaped approved origin: {target.base_url}")
        successes += 1
    return successes


def _validate_forced_browser_fallback(now: datetime) -> None:
    organization = Organization(
        id=uuid5(NAMESPACE_URL, _SELENIUM_ORIGIN),
        canonical_name="Selenium browser fallback fixture",
        legal_name=None,
        country_code=None,
        website_url=_SELENIUM_ORIGIN,
        registration_ids=(),
        created_at=now,
        updated_at=now,
    )
    static_policy = AutomaticPublicWebPolicy(
        authorization_reference="sa16-l09-selenium-static",
        reviewed_at=now,
        discover_sitemaps=False,
        discover_feeds=False,
        max_link_depth=0,
        max_pages=1,
        max_total_bytes=2_000_000,
        max_resource_bytes=1_000_000,
        max_redirects=3,
    )
    provisioned = provision_public_web_target(
        organization,
        static_policy,
        first_crawl_at=now,
    )
    target = replace(
        provisioned.target,
        seed_urls=(_SELENIUM_FIXTURE,),
        discover_security_txt=False,
        discover_sitemaps=False,
        discover_feeds=False,
        max_pages=1,
    )
    browser_policy = AutomaticBrowserFallbackPolicy(
        authorization_reference="sa16-l09-selenium-browser",
        reviewed_at=now,
        min_static_text_chars=100_000,
        max_browser_pages=1,
    )
    browser_entry = build_browser_fallback_entry(
        provisioned.source_entry,
        target,
        browser_policy,
    )
    _assert_direct_fallback(target, browser_entry, browser_policy, now)
    adapter = PublicWebFallbackAdapter(
        provisioned.source_entry,
        browser_entry,
        target,
        fallback_policy=browser_policy.fallback_policy(),
        timeout_seconds=30.0,
    )
    batch = adapter.collect(
        collection_job_id=uuid4(),
        checkpoint_payload=None,
        collected_at=now,
        retention_until=now + timedelta(days=30),
    )
    pages = batch.checkpoint_payload.get("pages")
    if not isinstance(pages, dict) or _SELENIUM_FIXTURE not in pages:
        raise RuntimeError("SA16-L09 browser fixture was not checkpointed")
    if not batch.observations or not batch.public_footprint_projections:
        raise RuntimeError("SA16-L09 browser fixture produced no canonical data")
    print(
        "SA16-L09 forced browser adapter passed: "
        f"url={_SELENIUM_FIXTURE} observations={len(batch.observations)}",
        flush=True,
    )


def _assert_direct_fallback(target, browser_entry, browser_policy, now: datetime) -> None:
    with httpx.Client(timeout=30.0, follow_redirects=False) as http_client:
        client = FallbackPublicWebClient(
            http_client,
            browser_entry,
            collected_at=now,
            policy=BrowserFallbackPolicy(
                min_static_text_chars=browser_policy.min_static_text_chars,
                max_browser_pages=browser_policy.max_browser_pages,
            ),
        )
        robots = client.fetch_robots(target)
        result = client.fetch_page(
            target,
            _SELENIUM_FIXTURE,
            robots,
            usage=CrawlUsage(),
        )
    if client.fallback_urls != (_SELENIUM_FIXTURE,):
        raise RuntimeError(
            "SA16-L09 Selenium fixture did not execute the browser fallback"
        )
    if not result.body or result.mime_type != "text/html":
        raise RuntimeError("SA16-L09 browser fallback returned no rendered HTML")
    print(
        "SA16-L09 browser fallback confirmed: "
        f"url={_SELENIUM_FIXTURE} rendered_bytes={len(result.body)}",
        flush=True,
    )


def _organization_record(
    name: str,
    url: str,
    now: datetime,
) -> OrganizationRecord:
    return OrganizationRecord(
        id=uuid5(NAMESPACE_URL, url),
        canonical_name=name,
        legal_name=None,
        country_code=None,
        website_url=url,
        registration_ids=[],
        created_at=now,
        updated_at=now,
    )


if __name__ == "__main__":
    main()
