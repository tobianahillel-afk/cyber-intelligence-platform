from __future__ import annotations

from cip.adapters.sources.passive_exposure_catalogs.schemas import (
    CloudAssetMetadataRecord,
    PassiveAssetMetadataRecord,
    PassiveExposureMetadataRecord,
    ProviderAttributionRisk,
    TechnographicMetadataRecord,
)
from cip.modules.passive_exposure.domain.models import (
    AttributionRisk,
    OrganizationLink,
    OrganizationLinkMethod,
    OrganizationLinkStatus,
    PassiveAsset,
    PassiveAssetKind,
    PassiveObservationKind,
    PassiveObservationSnapshot,
    PassiveObservationState,
    TechnologyEvidenceLevel,
    TechnologyObservation,
)


def map_passive_exposure_metadata(
    record: PassiveExposureMetadataRecord,
    *,
    source_id: str,
    organization_link: OrganizationLink | None = None,
) -> PassiveObservationSnapshot:
    return _map_record(
        record,
        source_id=source_id,
        organization_link=organization_link,
    )


def map_technographic_metadata(
    record: TechnographicMetadataRecord,
    *,
    source_id: str,
    organization_link: OrganizationLink | None = None,
) -> PassiveObservationSnapshot:
    return _map_record(
        record,
        source_id=source_id,
        organization_link=organization_link,
    )


def map_cloud_asset_metadata(
    record: CloudAssetMetadataRecord,
    *,
    source_id: str,
    organization_link: OrganizationLink | None = None,
) -> PassiveObservationSnapshot:
    return _map_record(
        record,
        source_id=source_id,
        organization_link=organization_link,
    )


def _map_record(
    record: PassiveAssetMetadataRecord,
    *,
    source_id: str,
    organization_link: OrganizationLink | None,
) -> PassiveObservationSnapshot:
    link = _merge_attribution_risks(
        organization_link or _unresolved_link(),
        record.attribution_risks,
    )
    technology = (
        TechnologyObservation(
            evidence_level=TechnologyEvidenceLevel(record.technology.evidence_level),
            product_name=record.technology.product_name,
            product_version=record.technology.product_version,
            component_name=record.technology.component_name,
        )
        if record.technology is not None
        else None
    )
    return PassiveObservationSnapshot(
        source_id=source_id,
        source_record_key=record.record_id,
        source_url=record.source_url,
        asset=PassiveAsset(
            kind=PassiveAssetKind(record.asset_kind),
            value=record.asset_value,
        ),
        observation_kind=PassiveObservationKind(record.observation_kind),
        state=PassiveObservationState(record.state),
        observed_at=record.observed_at,
        published_at=record.published_at,
        modified_at=record.modified_at,
        expires_at=record.expires_at,
        confidence=record.confidence,
        independence_key=record.independence_key,
        organization_link=link,
        technology=technology,
        port=record.port,
        protocol=record.protocol,
        active=record.active,
        historical_only=record.historical_only,
        metadata_only=True,
        passive_only=True,
        active_probe_performed=False,
        credentials_used=False,
        access_control_bypassed=False,
        exploit_attempted=False,
        direct_validation_performed=False,
        vulnerability_applicability_assessed=False,
        exposure_verified=False,
        supersedes_record_key=record.supersedes_record_key,
    )


def _merge_attribution_risks(
    link: OrganizationLink,
    provider_risks: tuple[ProviderAttributionRisk, ...],
) -> OrganizationLink:
    mapped_risks = tuple(AttributionRisk(risk.value) for risk in provider_risks)
    risks = tuple(dict.fromkeys((*link.attribution_risks, *mapped_risks)))
    status = link.status
    if status is OrganizationLinkStatus.EXACT and risks:
        status = OrganizationLinkStatus.REVIEW_REQUIRED
    return OrganizationLink(
        status=status,
        method=link.method,
        confidence=link.confidence,
        organization_id=link.organization_id,
        reasons=link.reasons,
        attribution_risks=risks,
    )


def _unresolved_link() -> OrganizationLink:
    return OrganizationLink(
        status=OrganizationLinkStatus.UNRESOLVED,
        method=OrganizationLinkMethod.NONE,
        confidence=0.0,
    )
