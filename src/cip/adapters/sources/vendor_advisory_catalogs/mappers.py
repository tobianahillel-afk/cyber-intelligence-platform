from __future__ import annotations

from cip.adapters.sources.vendor_advisory_catalogs.schemas import (
    ProviderAdvisoryRecord,
    ProviderAffectedRange,
    ProviderProduct,
    ProviderVersionBoundary,
)
from cip.modules.vulnerability_applicability.domain.models import (
    AdvisoryRevision,
    AffectedRange,
    ProductIdentity,
    VersionBoundary,
)


def map_vendor_advisory(
    record: ProviderAdvisoryRecord,
    *,
    source_id: str,
) -> AdvisoryRevision:
    return AdvisoryRevision(
        source_id=source_id,
        source_record_key=record.record_id,
        advisory_id=record.advisory_id,
        source_url=record.source_url,
        state=record.state,
        published_at=record.published_at,
        modified_at=record.modified_at,
        vulnerabilities=record.vulnerabilities,
        affected_ranges=tuple(_map_range(item) for item in record.affected_ranges),
        title=record.title,
        fixed_versions=record.fixed_versions,
        workarounds=record.workarounds,
        supersedes_record_key=record.supersedes_record_key,
        metadata_only=record.metadata_only,
        active_validation_performed=False,
        exposure_verified=False,
    )


def _map_range(value: ProviderAffectedRange) -> AffectedRange:
    return AffectedRange(
        product=_map_product(value.product),
        scheme=value.scheme,
        boundaries=tuple(_map_boundary(item) for item in value.boundaries),
        vulnerable=value.vulnerable,
        backported_fix=value.backported_fix,
        branch=value.branch,
        precision=value.precision,
    )


def _map_product(value: ProviderProduct) -> ProductIdentity:
    return ProductIdentity(
        vendor=value.vendor,
        product=value.product,
        component=value.component,
        edition=value.edition,
        ecosystem=value.ecosystem,
        platform=value.platform,
        identifiers=value.identifiers,
        support_status=value.support_status,
        end_of_support_at=value.end_of_support_at,
    )


def _map_boundary(value: ProviderVersionBoundary) -> VersionBoundary:
    return VersionBoundary(
        kind=value.kind,
        version=value.version,
        inclusive=value.inclusive,
    )
