from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

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
from cip.modules.passive_exposure.domain.reconciliation import (
    latest_passive_snapshots,
    reconcile_passive_snapshots,
)

NOW = datetime(2026, 8, 6, 12, tzinfo=UTC)
ASSET = PassiveAsset(PassiveAssetKind.HOSTNAME, "service.example.com")


def test_keeps_only_latest_revision_for_each_source_record() -> None:
    original = _snapshot(modified_at=NOW + timedelta(minutes=2))
    corrected = _snapshot(
        modified_at=NOW + timedelta(minutes=3),
        state=PassiveObservationState.CORRECTED,
    )

    latest = latest_passive_snapshots((original, corrected))

    assert latest == (corrected,)


def test_equal_timestamp_revision_selection_is_deterministic() -> None:
    current = _snapshot()
    corrected = _snapshot(state=PassiveObservationState.CORRECTED)

    assert latest_passive_snapshots((current, corrected)) == (corrected,)
    assert latest_passive_snapshots((corrected, current)) == (corrected,)


def test_new_provider_record_can_supersede_previous_record_key() -> None:
    original = _snapshot()
    correction = _snapshot(
        source_record_key="record-2",
        source_url="https://provider-a.example/records/2",
        state=PassiveObservationState.CORRECTED,
        modified_at=NOW + timedelta(minutes=3),
        active=False,
        historical_only=True,
        supersedes_record_key="record-1",
    )

    assert latest_passive_snapshots((original, correction)) == (correction,)


def test_expires_current_observation_at_read_time() -> None:
    result = reconcile_passive_snapshots(
        (
            _snapshot(
                expires_at=NOW + timedelta(hours=1),
            ),
        ),
        at=NOW + timedelta(hours=2),
    )[0]

    assert result.state is PassiveObservationState.EXPIRED
    assert result.active is False
    assert result.historical_only is True
    assert result.can_support_exposure_conclusion is False


def test_syndicated_sources_count_once_for_independence() -> None:
    result = reconcile_passive_snapshots(
        (
            _snapshot(source_id="provider-a", independence_key="upstream-feed"),
            _snapshot(
                source_id="provider-b",
                source_record_key="record-2",
                source_url="https://provider-b.example/records/2",
                independence_key="upstream-feed",
            ),
        ),
        at=NOW,
    )[0]

    assert result.source_count == 2
    assert result.independent_source_count == 1


def test_conflicting_exact_organization_links_require_review() -> None:
    first_organization = uuid4()
    second_organization = uuid4()
    result = reconcile_passive_snapshots(
        (
            _snapshot(organization_link=_exact_link(first_organization)),
            _snapshot(
                source_id="provider-b",
                source_record_key="record-2",
                source_url="https://provider-b.example/records/2",
                organization_link=_exact_link(second_organization),
            ),
        ),
        at=NOW,
    )[0]

    assert result.organization_link.status is OrganizationLinkStatus.REVIEW_REQUIRED
    assert result.organization_link.exact_organization_id is None
    assert result.organization_link.candidate_organization_ids == tuple(
        sorted((first_organization, second_organization), key=str)
    )


def test_attribution_risk_prevents_automatic_exact_projection() -> None:
    organization_id = uuid4()
    result = reconcile_passive_snapshots(
        (
            _snapshot(
                organization_link=OrganizationLink(
                    status=OrganizationLinkStatus.REVIEW_REQUIRED,
                    method=OrganizationLinkMethod.PASSIVE_CORRELATION,
                    confidence=0.7,
                    organization_id=organization_id,
                    reasons=("Hostname correlation",),
                    attribution_risks=(AttributionRisk.CDN,),
                )
            ),
        ),
        at=NOW,
    )[0]

    assert result.organization_link.status is OrganizationLinkStatus.REVIEW_REQUIRED
    assert result.organization_link.candidate_organization_ids == (organization_id,)
    assert result.attribution_risks == (AttributionRisk.CDN,)


def test_inactive_retraction_cannot_override_current_attribution() -> None:
    current_organization = uuid4()
    retracted_organization = uuid4()
    active_technology = TechnologyObservation(
        evidence_level=TechnologyEvidenceLevel.PASSIVE_OBSERVATION,
        product_name="Current Product",
    )
    retracted_technology = TechnologyObservation(
        evidence_level=TechnologyEvidenceLevel.PASSIVE_OBSERVATION,
        product_name="Retracted Product",
    )
    result = reconcile_passive_snapshots(
        (
            _snapshot(
                organization_link=_exact_link(current_organization),
                observation_kind=PassiveObservationKind.PRODUCT,
                technology=active_technology,
                expires_at=NOW + timedelta(days=1),
            ),
            _snapshot(
                source_id="provider-b",
                source_record_key="record-2",
                source_url="https://provider-b.example/records/2",
                modified_at=NOW + timedelta(minutes=4),
                state=PassiveObservationState.RETRACTED,
                active=False,
                organization_link=_exact_link(retracted_organization),
                observation_kind=PassiveObservationKind.PRODUCT,
                technology=retracted_technology,
                expires_at=NOW + timedelta(days=365),
            ),
        ),
        at=NOW,
    )[0]

    assert result.state is PassiveObservationState.CURRENT
    assert result.organization_link.status is OrganizationLinkStatus.EXACT
    assert result.organization_link.exact_organization_id == current_organization
    assert result.organization_link.candidate_organization_ids == ()
    assert result.technologies == (active_technology,)
    assert result.expires_at == NOW + timedelta(days=1)


def test_preserves_state_conflict_while_active_observation_remains_current() -> None:
    product = TechnologyObservation(
        evidence_level=TechnologyEvidenceLevel.PASSIVE_OBSERVATION,
        product_name="Example Server",
    )
    version = TechnologyObservation(
        evidence_level=TechnologyEvidenceLevel.OBSERVED_VERSION,
        product_name="Example Server",
        product_version="4.2.1",
    )
    result = reconcile_passive_snapshots(
        (
            _snapshot(
                observation_kind=PassiveObservationKind.PRODUCT,
                technology=product,
            ),
            _snapshot(
                source_id="provider-b",
                source_record_key="record-2",
                source_url="https://provider-b.example/records/2",
                observation_kind=PassiveObservationKind.VERSION,
                technology=version,
                port=443,
                protocol="https",
            ),
            _snapshot(
                source_id="provider-c",
                source_record_key="record-3",
                source_url="https://provider-c.example/records/3",
                state=PassiveObservationState.RETRACTED,
                active=False,
                modified_at=NOW + timedelta(minutes=4),
            ),
        ),
        at=NOW,
    )[0]

    assert result.has_conflict is True
    assert result.state is PassiveObservationState.CURRENT
    assert len(result.technologies) == 2
    assert [(service.port, service.protocol) for service in result.services] == [
        (443, "https")
    ]


def _exact_link(organization_id: UUID) -> OrganizationLink:
    return OrganizationLink(
        status=OrganizationLinkStatus.EXACT,
        method=OrganizationLinkMethod.EXACT_OFFICIAL_DOMAIN,
        confidence=1.0,
        organization_id=organization_id,
        reasons=("Official domain claim",),
    )


def _snapshot(**overrides: object) -> PassiveObservationSnapshot:
    values: dict[str, object] = {
        "source_id": "provider-a",
        "source_record_key": "record-1",
        "source_url": "https://provider-a.example/records/1",
        "asset": ASSET,
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
