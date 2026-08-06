from __future__ import annotations

from datetime import UTC, datetime

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
)
from cip.modules.passive_exposure.domain.reconciliation import (
    latest_passive_snapshots,
)

NOW = datetime(2026, 8, 6, 12, tzinfo=UTC)
ASSET = PassiveAsset(PassiveAssetKind.HOSTNAME, "service.example.com")


def test_rejects_partial_cycle_even_when_unrelated_record_remains() -> None:
    first = _snapshot("record-1", supersedes="record-2")
    second = _snapshot("record-2", supersedes="record-1")
    unrelated = _snapshot("record-3")

    with pytest.raises(ValueError, match="supersession cycle"):
        latest_passive_snapshots((first, second, unrelated))


def _snapshot(
    record_key: str,
    *,
    supersedes: str | None = None,
) -> PassiveObservationSnapshot:
    return PassiveObservationSnapshot(
        source_id="provider-a",
        source_record_key=record_key,
        source_url=f"https://provider.example/records/{record_key}",
        asset=ASSET,
        observation_kind=PassiveObservationKind.PASSIVE_DNS,
        state=PassiveObservationState.CURRENT,
        observed_at=NOW,
        published_at=NOW,
        modified_at=NOW,
        confidence=0.8,
        organization_link=OrganizationLink(
            status=OrganizationLinkStatus.UNRESOLVED,
            method=OrganizationLinkMethod.NONE,
            confidence=0.0,
        ),
        supersedes_record_key=supersedes,
    )
