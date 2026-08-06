from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from cip.adapters.sources.passive_exposure_catalogs.mappers import (
    map_cloud_asset_metadata,
    map_passive_exposure_metadata,
    map_technographic_metadata,
)
from cip.adapters.sources.passive_exposure_catalogs.schemas import (
    CloudAssetMetadataRecord,
    PassiveExposureMetadataRecord,
    ProviderAssetKind,
    ProviderAttributionRisk,
    ProviderObservationKind,
    ProviderObservationState,
    ProviderTechnologyLevel,
    ProviderTechnologyMetadata,
    TechnographicMetadataRecord,
)
from cip.modules.passive_exposure.domain.models import (
    AttributionRisk,
    OrganizationLink,
    OrganizationLinkMethod,
    OrganizationLinkStatus,
    PassiveAssetKind,
    TechnologyEvidenceLevel,
)

NOW = datetime(2026, 8, 6, 12, tzinfo=UTC)


def test_maps_passive_metadata_without_creating_an_organization_link() -> None:
    snapshot = map_passive_exposure_metadata(
        PassiveExposureMetadataRecord(
            **_base_payload(),
            attribution_risks=(ProviderAttributionRisk.CDN,),
        ),
        source_id="licensed-passive-exposure",
    )

    assert snapshot.asset.kind is PassiveAssetKind.HOSTNAME
    assert snapshot.asset.value == "service.example.com"
    assert snapshot.organization_link.status is OrganizationLinkStatus.UNRESOLVED
    assert snapshot.organization_link.attribution_risks == (AttributionRisk.CDN,)
    assert snapshot.can_support_exposure_conclusion is False
    assert snapshot.active_probe_performed is False
    assert snapshot.vulnerability_applicability_assessed is False
    assert snapshot.exposure_verified is False


def test_provider_risk_downgrades_exact_link_to_review_required() -> None:
    link = OrganizationLink(
        status=OrganizationLinkStatus.EXACT,
        method=OrganizationLinkMethod.EXACT_OFFICIAL_DOMAIN,
        confidence=1.0,
        organization_id=uuid4(),
        reasons=("Official domain ownership",),
    )
    snapshot = map_passive_exposure_metadata(
        PassiveExposureMetadataRecord(
            **_base_payload(),
            attribution_risks=(ProviderAttributionRisk.SHARED_HOSTING,),
        ),
        source_id="licensed-passive-exposure",
        organization_link=link,
    )

    assert snapshot.organization_link.status is OrganizationLinkStatus.REVIEW_REQUIRED
    assert snapshot.organization_link.organization_id == link.organization_id
    assert snapshot.organization_link.attribution_risks == (
        AttributionRisk.SHARED_HOSTING,
    )


def test_maps_observed_version_without_assessing_applicability() -> None:
    record = TechnographicMetadataRecord(
        **_base_payload(
            observation_kind=ProviderObservationKind.VERSION,
        ),
        technology=ProviderTechnologyMetadata(
            evidence_level=ProviderTechnologyLevel.OBSERVED_VERSION,
            product_name="Example Server",
            product_version="4.2.1",
        ),
    )

    snapshot = map_technographic_metadata(
        record,
        source_id="licensed-technographic-observations",
    )

    assert snapshot.technology is not None
    assert snapshot.technology.evidence_level is TechnologyEvidenceLevel.OBSERVED_VERSION
    assert snapshot.technology.product_version == "4.2.1"
    assert snapshot.vulnerability_applicability_assessed is False
    assert snapshot.exposure_verified is False


def test_maps_shared_cloud_tenancy_as_review_risk() -> None:
    record = CloudAssetMetadataRecord(
        **_base_payload(
            asset_kind=ProviderAssetKind.CLOUD_RESOURCE,
            asset_value="aws:arn:example",
            observation_kind=ProviderObservationKind.CLOUD,
        ),
        cloud_provider="aws",
        tenant_shared=True,
        attribution_risks=(ProviderAttributionRisk.SHARED_HOSTING,),
    )

    snapshot = map_cloud_asset_metadata(
        record,
        source_id="licensed-cloud-asset-observations",
    )

    assert snapshot.asset.kind is PassiveAssetKind.CLOUD_RESOURCE
    assert snapshot.organization_link.attribution_risks == (
        AttributionRisk.SHARED_HOSTING,
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("active_probe", True),
        ("direct_connection", True),
        ("authenticated_enumeration", True),
        ("access_control_bypass", True),
        ("exploit_attempt", True),
        ("applicability_assessed", True),
        ("exposure_verified", True),
        ("credential", "secret"),
        ("binary_payload", "bytes"),
        ("source_url", "https://user:secret@provider.example/records/1"),
    ],
)
def test_rejects_active_or_sensitive_provider_payloads(field: str, value: object) -> None:
    payload = _base_payload()
    payload[field] = value

    with pytest.raises(ValidationError):
        PassiveExposureMetadataRecord(**payload)


def test_shared_cloud_tenancy_requires_explicit_attribution_risk() -> None:
    with pytest.raises(ValidationError, match="shared cloud tenancy"):
        CloudAssetMetadataRecord(
            **_base_payload(
                asset_kind=ProviderAssetKind.CLOUD_RESOURCE,
                asset_value="aws:arn:example",
                observation_kind=ProviderObservationKind.CLOUD,
            ),
            cloud_provider="aws",
            tenant_shared=True,
        )


def _base_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "record_id": "record-1",
        "source_url": "https://provider.example/records/1",
        "asset_kind": ProviderAssetKind.HOSTNAME,
        "asset_value": "Service.Example.com.",
        "observation_kind": ProviderObservationKind.PASSIVE_DNS,
        "state": ProviderObservationState.CURRENT,
        "observed_at": NOW - timedelta(hours=2),
        "published_at": NOW - timedelta(hours=1),
        "modified_at": NOW,
        "expires_at": NOW + timedelta(days=30),
        "confidence": 0.8,
    }
    payload.update(overrides)
    return payload
