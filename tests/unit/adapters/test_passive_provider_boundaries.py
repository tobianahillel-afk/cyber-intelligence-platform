from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from cip.adapters.sources.passive_exposure_catalogs.schemas import (
    PassiveExposureMetadataRecord,
    ProviderAssetKind,
    ProviderObservationKind,
    ProviderObservationState,
    ProviderTechnologyLevel,
    ProviderTechnologyMetadata,
)

NOW = datetime(2026, 8, 6, 12, tzinfo=UTC)


def test_rejects_naive_provider_timestamps_before_mapping() -> None:
    payload = _payload()
    payload["observed_at"] = datetime(2026, 8, 6, 10)

    with pytest.raises(ValidationError, match="timezone-aware"):
        PassiveExposureMetadataRecord(**payload)


def test_normalizes_aware_provider_timestamps_to_utc() -> None:
    paris = timezone(timedelta(hours=2))
    record = PassiveExposureMetadataRecord(
        **_payload(
            observed_at=datetime(2026, 8, 6, 12, tzinfo=paris),
            published_at=datetime(2026, 8, 6, 13, tzinfo=paris),
            modified_at=datetime(2026, 8, 6, 14, tzinfo=paris),
            expires_at=datetime(2026, 8, 7, 12, tzinfo=paris),
        )
    )

    assert record.observed_at == datetime(2026, 8, 6, 10, tzinfo=UTC)
    assert record.published_at == datetime(2026, 8, 6, 11, tzinfo=UTC)
    assert record.modified_at == datetime(2026, 8, 6, 12, tzinfo=UTC)
    assert record.expires_at == datetime(2026, 8, 7, 10, tzinfo=UTC)


@pytest.mark.parametrize(
    "field",
    ["independence_key", "supersedes_record_key", "provider_asset_id"],
)
def test_rejects_blank_optional_provider_identifiers(field: str) -> None:
    payload = _payload()
    payload[field] = "   "

    with pytest.raises(ValidationError):
        PassiveExposureMetadataRecord(**payload)


def test_rejects_blank_protocol_when_port_is_present() -> None:
    with pytest.raises(ValidationError):
        PassiveExposureMetadataRecord(
            **_payload(port=443, protocol="   ")
        )


def test_rejects_blank_optional_technology_fields() -> None:
    with pytest.raises(ValidationError):
        ProviderTechnologyMetadata(
            evidence_level=ProviderTechnologyLevel.OBSERVED_VERSION,
            product_name="Example Server",
            product_version="   ",
        )


def _payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "record_id": "record-1",
        "source_url": "https://provider.example/records/1",
        "asset_kind": ProviderAssetKind.HOSTNAME,
        "asset_value": "service.example.com",
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
