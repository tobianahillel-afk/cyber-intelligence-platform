from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from cip.modules.passive_exposure.domain.models import (
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
    reconcile_passive_snapshots,
)

NOW = datetime(2026, 8, 6, 12, tzinfo=UTC)
ASSET = PassiveAsset(PassiveAssetKind.HOSTNAME, "service.example.com")


@pytest.mark.parametrize(
    "terminal_state",
    [PassiveObservationState.RETRACTED, PassiveObservationState.DELETED],
)
def test_terminal_revision_removes_provider_observation_from_current_projection(
    terminal_state: PassiveObservationState,
) -> None:
    organization_id = uuid4()
    original = _current_snapshot(organization_id)
    terminal = PassiveObservationSnapshot(
        source_id="provider-a",
        source_record_key=f"record-{terminal_state.value}",
        source_url=f"https://provider.example/records/{terminal_state.value}",
        asset=ASSET,
        observation_kind=PassiveObservationKind.VERSION,
        state=terminal_state,
        observed_at=NOW,
        published_at=NOW + timedelta(minutes=1),
        modified_at=NOW + timedelta(minutes=3),
        confidence=1.0,
        organization_link=_unresolved_link(),
        active=False,
        historical_only=True,
        supersedes_record_key=original.source_record_key,
        technology=original.technology,
    )

    result = reconcile_passive_snapshots((original, terminal), at=NOW)[0]

    assert result.state is terminal_state
    assert result.active is False
    assert result.historical_only is True
    assert result.organization_link.status is OrganizationLinkStatus.UNRESOLVED
    assert result.organization_link.exact_organization_id is None
    assert result.organization_link.candidate_organization_ids == ()
    assert result.technologies == ()
    assert result.services == ()
    assert result.observed_states == tuple(
        sorted(
            (PassiveObservationState.CURRENT, terminal_state),
            key=lambda state: state.value,
        )
    )
    assert result.has_conflict is True
    assert result.can_support_exposure_conclusion is False


def _current_snapshot(organization_id: UUID) -> PassiveObservationSnapshot:
    return PassiveObservationSnapshot(
        source_id="provider-a",
        source_record_key="record-current",
        source_url="https://provider.example/records/current",
        asset=ASSET,
        observation_kind=PassiveObservationKind.VERSION,
        state=PassiveObservationState.CURRENT,
        observed_at=NOW - timedelta(days=1),
        published_at=NOW - timedelta(hours=23),
        modified_at=NOW - timedelta(hours=22),
        expires_at=NOW + timedelta(days=30),
        confidence=0.8,
        organization_link=OrganizationLink(
            status=OrganizationLinkStatus.EXACT,
            method=OrganizationLinkMethod.EXACT_OFFICIAL_DOMAIN,
            confidence=1.0,
            organization_id=organization_id,
            reasons=("Official domain ownership",),
        ),
        technology=TechnologyObservation(
            evidence_level=TechnologyEvidenceLevel.OBSERVED_VERSION,
            product_name="Example Server",
            product_version="4.2.1",
        ),
        port=443,
        protocol="https",
    )


def _unresolved_link() -> OrganizationLink:
    return OrganizationLink(
        status=OrganizationLinkStatus.UNRESOLVED,
        method=OrganizationLinkMethod.NONE,
        confidence=0.0,
    )
