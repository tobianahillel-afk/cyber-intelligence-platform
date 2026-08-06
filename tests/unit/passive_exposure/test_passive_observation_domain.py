from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

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
from cip.modules.passive_exposure.domain.normalization import (
    normalize_asn,
    normalize_certificate_fingerprint,
    normalize_cloud_resource,
    normalize_domain,
    normalize_ip,
)

NOW = datetime(2026, 8, 6, 12, tzinfo=UTC)


def test_normalizes_public_passive_asset_identifiers() -> None:
    assert normalize_domain("Tést.Example.COM.") == "xn--tst-bma.example.com"
    assert normalize_ip("2606:4700:4700::1111", version=6) == "2606:4700:4700::1111"
    assert normalize_asn("as13335") == "AS13335"
    assert normalize_cloud_resource("aws:arn:example") == "aws:arn:example"
    assert normalize_certificate_fingerprint("AA:" * 31 + "AA") == "aa" * 32


@pytest.mark.parametrize(
    "value",
    ["localhost", "service.internal", "printer.lan", "single-label"],
)
def test_rejects_local_or_non_registrable_domains(value: str) -> None:
    with pytest.raises(ValueError):
        normalize_domain(value)


@pytest.mark.parametrize("value", ["127.0.0.1", "10.0.0.4", "::1", "fe80::1"])
def test_rejects_non_global_addresses(value: str) -> None:
    with pytest.raises(ValueError):
        normalize_ip(value)


def test_exact_organization_link_requires_exact_evidence_without_risk() -> None:
    link = OrganizationLink(
        status=OrganizationLinkStatus.EXACT,
        method=OrganizationLinkMethod.EXACT_OFFICIAL_DOMAIN,
        confidence=1.0,
        organization_id=uuid4(),
        reasons=("Official registry domain ownership",),
    )

    assert link.requires_review is False

    with pytest.raises(ValueError, match="attribution risks"):
        OrganizationLink(
            status=OrganizationLinkStatus.EXACT,
            method=OrganizationLinkMethod.EXACT_OFFICIAL_DOMAIN,
            confidence=0.9,
            organization_id=uuid4(),
            reasons=("Provider correlation",),
            attribution_risks=(AttributionRisk.CDN,),
        )


def test_name_only_links_remain_reviewable() -> None:
    link = OrganizationLink(
        status=OrganizationLinkStatus.REVIEW_REQUIRED,
        method=OrganizationLinkMethod.NAME_ONLY,
        confidence=0.4,
        organization_id=uuid4(),
        reasons=("Name-only provider assertion",),
        attribution_risks=(AttributionRisk.RESELLER,),
    )

    assert link.requires_review is True

    with pytest.raises(ValueError, match="name-only"):
        OrganizationLink(
            status=OrganizationLinkStatus.EXACT,
            method=OrganizationLinkMethod.NAME_ONLY,
            confidence=0.4,
            organization_id=uuid4(),
            reasons=("Name-only provider assertion",),
        )


def test_version_observation_is_not_an_exposure_conclusion() -> None:
    snapshot = _snapshot(
        observation_kind=PassiveObservationKind.VERSION,
        technology=TechnologyObservation(
            evidence_level=TechnologyEvidenceLevel.OBSERVED_VERSION,
            product_name="Example Server",
            product_version="4.2.1",
        ),
    )

    assert snapshot.asset.value == "service.example.com"
    assert snapshot.can_support_exposure_conclusion is False
    assert snapshot.vulnerability_applicability_assessed is False
    assert snapshot.exposure_verified is False


def test_service_observation_requires_bounded_port_and_protocol() -> None:
    snapshot = _snapshot(
        observation_kind=PassiveObservationKind.SERVICE,
        port=443,
        protocol="HTTPS",
    )

    assert snapshot.observation_key.endswith(":service:443/https")

    with pytest.raises(ValueError, match="port and protocol"):
        _snapshot(observation_kind=PassiveObservationKind.PORT, port=443)


def test_rejects_active_validation_and_exposure_claims() -> None:
    with pytest.raises(ValueError, match="active validation"):
        _snapshot(active_probe_performed=True)

    with pytest.raises(ValueError, match="cannot assess"):
        _snapshot(exposure_verified=True)

    with pytest.raises(ValueError, match="cannot assess"):
        _snapshot(vulnerability_applicability_assessed=True)


def test_terminal_observations_are_inactive_and_historical() -> None:
    snapshot = _snapshot(
        state=PassiveObservationState.EXPIRED,
        active=False,
        historical_only=True,
        expires_at=NOW + timedelta(days=1),
    )

    assert snapshot.active is False

    with pytest.raises(ValueError, match="cannot be active"):
        _snapshot(state=PassiveObservationState.RETRACTED)


def _snapshot(**overrides: object) -> PassiveObservationSnapshot:
    values: dict[str, object] = {
        "source_id": "licensed-passive-provider",
        "source_record_key": "record-1",
        "source_url": "https://provider.example/records/1",
        "asset": PassiveAsset(PassiveAssetKind.HOSTNAME, "Service.Example.com."),
        "observation_kind": PassiveObservationKind.PASSIVE_DNS,
        "state": PassiveObservationState.CURRENT,
        "observed_at": NOW,
        "published_at": NOW + timedelta(minutes=1),
        "modified_at": NOW + timedelta(minutes=2),
        "confidence": 0.8,
        "organization_link": OrganizationLink(
            status=OrganizationLinkStatus.UNRESOLVED,
            method=OrganizationLinkMethod.NONE,
            confidence=0.0,
        ),
    }
    values.update(overrides)
    return PassiveObservationSnapshot(**values)  # type: ignore[arg-type]
