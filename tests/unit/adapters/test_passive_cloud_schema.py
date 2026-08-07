from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from cip.adapters.sources.passive_exposure_catalogs.schemas import (
    CloudAssetMetadataRecord,
    ProviderAssetKind,
    ProviderObservationKind,
    ProviderObservationState,
)

NOW = datetime(2026, 8, 6, 12, tzinfo=UTC)


def test_cloud_provider_is_normalized_and_matches_resource_namespace() -> None:
    record = CloudAssetMetadataRecord(
        **_payload(),
        cloud_provider=" AWS ",
    )

    assert record.asset_kind is ProviderAssetKind.CLOUD_RESOURCE
    assert record.cloud_provider == "aws"


@pytest.mark.parametrize(
    "overrides",
    [
        {
            "asset_kind": ProviderAssetKind.HOSTNAME,
            "asset_value": "service.example.com",
        },
        {
            "asset_kind": ProviderAssetKind.CLOUD_RESOURCE,
            "asset_value": "azure:resource:example",
        },
    ],
)
def test_cloud_metadata_rejects_wrong_kind_or_provider_namespace(
    overrides: dict[str, object],
) -> None:
    payload = _payload()
    payload.update(overrides)

    with pytest.raises(ValidationError):
        CloudAssetMetadataRecord(**payload, cloud_provider="aws")


def _payload() -> dict[str, object]:
    return {
        "record_id": "cloud-record-1",
        "source_url": "https://provider.example/records/cloud-1",
        "asset_kind": ProviderAssetKind.CLOUD_RESOURCE,
        "asset_value": "aws:arn:example",
        "observation_kind": ProviderObservationKind.CLOUD,
        "state": ProviderObservationState.CURRENT,
        "observed_at": NOW - timedelta(hours=2),
        "published_at": NOW - timedelta(hours=1),
        "modified_at": NOW,
        "expires_at": NOW + timedelta(days=30),
        "confidence": 0.8,
    }
