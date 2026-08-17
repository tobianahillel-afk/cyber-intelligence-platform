from __future__ import annotations

from cip.adapters.sources.public_web.crawl_runtime import CrawlTelemetry
from cip.modules.collection_orchestration.application.ports import AdapterOperationalMetrics


def crawl_operational_metrics(telemetry: CrawlTelemetry) -> AdapterOperationalMetrics:
    return AdapterOperationalMetrics(
        namespace="public_web.crawl.v1",
        values={
            "attempted_pages": telemetry.attempted_pages,
            "fetched_pages": telemetry.fetched_pages,
            "not_modified_pages": telemetry.not_modified_pages,
            "tombstoned_pages": telemetry.tombstoned_pages,
            "failed_pages": telemetry.failed_pages,
            "bytes_received": telemetry.bytes_received,
            "bytes_accepted": telemetry.bytes_accepted,
            "links_discovered": telemetry.links_discovered,
            "links_admitted": telemetry.links_admitted,
            "links_denied": telemetry.links_denied,
            "browser_fallback_count": telemetry.browser_fallback_count,
            "policy_denials": telemetry.policy_denials,
            "redirects": telemetry.redirects,
            "elapsed_seconds": telemetry.elapsed_seconds,
            "deadline_exceeded": telemetry.deadline_exceeded,
            "cancelled": telemetry.cancelled,
            "configured_concurrency": telemetry.configured_concurrency,
            "effective_concurrency": telemetry.effective_concurrency,
            "max_concurrency_used": telemetry.max_concurrency_used,
        },
    )
