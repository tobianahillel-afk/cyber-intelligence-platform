from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

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
from cip.modules.passive_exposure.infrastructure.projection_payloads import (
    decode_text_values,
    decode_uuid_values,
    encode_text_values,
    encode_uuid_values,
    passive_snapshot_digest,
    passive_technology_digest,
)

NOW = datetime(2026, 8, 6, 12, tzinfo=UTC)


def test_text_and_uuid_collections_round_trip_deterministically() -> None:
    identifiers = (uuid4(), uuid4())

    assert decode_text_values(encode_text_values(("first", "second"))) == (
        "first",
        "second",
    )
    assert decode_uuid_values(encode_uuid_values(identifiers)) == identifiers


@pytest.mark.parametrize("value", ['{"invalid":true}', "[1]", "null"])
def test_rejects_invalid_persisted_text_collections(value: str) -> None:
    with pytest.raises(ValueError, match="persisted text collection"):
        decode_text_values(value)


def test_snapshot_digest_is_stable_and_revision_sensitive() -> None:
    snapshot = _snapshot()
    repeated = _snapshot()
    revised = replace(snapshot, modified_at=NOW + timedelta(minutes=3))

    assert passive_snapshot_digest(snapshot) == passive_snapshot_digest(repeated)
    assert passive_snapshot_digest(snapshot) != passive_snapshot_digest(revised)


def test_technology_digest_is_scoped_to_snapshot() -> None:
    technology = TechnologyObservation(
        evidence_level=TechnologyEvidenceLevel.OBSERVED_VERSION,
        product_name="Example Server",
        product_version="4.2.1",
    )

    assert passive_technology_digest("snapshot-a", technology) != (
        passive_technology_digest("snapshot-b", technology)
    )


def _snapshot() -> PassiveObservationSnapshot:
    return PassiveObservationSnapshot(
        source_id="passive-provider",
        source_record_key="record-1",
        source_url="https://passive-provider.example/records/1",
        asset=PassiveAsset(PassiveAssetKind.HOSTNAME, "service.example.com"),
        observation_kind=PassiveObservationKind.VERSION,
        state=PassiveObservationState.CURRENT,
        observed_at=NOW,
        published_at=NOW + timedelta(minutes=1),
        modified_at=NOW + timedelta(minutes=2),
        expires_at=NOW + timedelta(days=30),
        confidence=0.8,
        organization_link=OrganizationLink(
            status=OrganizationLinkStatus.UNRESOLVED,
            method=OrganizationLinkMethod.NONE,
            confidence=0.0,
        ),
        technology=TechnologyObservation(
            evidence_level=TechnologyEvidenceLevel.OBSERVED_VERSION,
            product_name="Example Server",
            product_version="4.2.1",
        ),
        port=443,
        protocol="https",
    )
