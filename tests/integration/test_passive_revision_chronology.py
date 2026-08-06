from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

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
from cip.modules.passive_exposure.infrastructure.models import (
    PassiveAssetRecord,
    PassiveObservationSnapshotRecord,
)
from cip.modules.passive_exposure.infrastructure.persistence_time import normalize_utc
from cip.modules.passive_exposure.infrastructure.projections import (
    persist_passive_snapshots,
)
from cip.shared.persistence.metadata import get_metadata

NOW = datetime(2026, 8, 6, 12, tzinfo=UTC)


def test_same_record_correction_preserves_complete_canonical_chronology() -> None:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    get_metadata().create_all(engine)
    original = _snapshot()
    correction = replace(
        original,
        state=PassiveObservationState.CORRECTED,
        observed_at=NOW - timedelta(days=1),
        published_at=NOW - timedelta(hours=23),
        modified_at=NOW,
        active=False,
        historical_only=True,
    )

    with Session(engine) as session:
        persist_passive_snapshots(
            session,
            (original,),
            now=NOW - timedelta(days=9),
        )
        persist_passive_snapshots(session, (correction,), now=NOW)
        session.commit()

        asset = session.scalar(
            select(PassiveAssetRecord).where(
                PassiveAssetRecord.asset_key == original.asset.key
            )
        )
        snapshot_count = len(
            tuple(session.scalars(select(PassiveObservationSnapshotRecord)))
        )

    assert asset is not None
    assert snapshot_count == 2
    assert normalize_utc(asset.first_seen_at) == NOW - timedelta(days=10)
    assert normalize_utc(asset.last_seen_at) == NOW - timedelta(days=1)
    assert set(asset.observed_states.split(",")) == {"current", "corrected"}
    assert asset.state == "corrected"
    assert asset.active is False
    assert asset.historical_only is True
    assert asset.has_conflict is True


def _snapshot() -> PassiveObservationSnapshot:
    return PassiveObservationSnapshot(
        source_id="provider-a",
        source_record_key="record-1",
        source_url="https://provider.example/records/1",
        asset=PassiveAsset(PassiveAssetKind.HOSTNAME, "history.example.com"),
        observation_kind=PassiveObservationKind.PASSIVE_DNS,
        state=PassiveObservationState.CURRENT,
        observed_at=NOW - timedelta(days=10),
        published_at=NOW - timedelta(days=9, hours=23),
        modified_at=NOW - timedelta(days=9, hours=22),
        confidence=0.8,
        organization_link=OrganizationLink(
            status=OrganizationLinkStatus.UNRESOLVED,
            method=OrganizationLinkMethod.NONE,
            confidence=0.0,
        ),
    )
