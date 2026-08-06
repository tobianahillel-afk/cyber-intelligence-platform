from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from cip.adapters.sources.threat_catalogs.mappers import (
    map_malware_metadata,
    map_phishing_metadata,
    map_stix_taxii_indicator,
)
from cip.adapters.sources.threat_catalogs.schemas import (
    MalwareMetadataRecord,
    ObservableType,
    PhishingMetadataRecord,
    ProviderState,
    StixTaxiiIndicatorRecord,
)
from cip.modules.threat_telemetry.domain.models import (
    IndicatorState,
    TelemetryRelationType,
    TelemetrySourceKind,
)

NOW = datetime(2026, 8, 6, 12, 0, tzinfo=UTC)


def test_stix_revocation_maps_to_retracted_metadata() -> None:
    record = StixTaxiiIndicatorRecord(
        record_id="indicator--1",
        stix_id="indicator--1",
        source_url="https://cti.example/objects/indicator--1",
        observable_type=ObservableType.DOMAIN,
        value="malicious.example",
        state=ProviderState.MALICIOUS,
        published_at=NOW,
        modified_at=NOW,
        revoked=True,
    )

    snapshot = map_stix_taxii_indicator(record, source_id="cti-provider")

    assert snapshot.state is IndicatorState.RETRACTED
    assert snapshot.source_kind is TelemetrySourceKind.STIX_TAXII
    assert snapshot.binary_payload_present is False
    assert snapshot.direct_validation_performed is False


def test_phishing_and_malware_mappings_add_selected_relations() -> None:
    phishing = PhishingMetadataRecord(
        record_id="phish-1",
        source_url="https://phishing.example/records/1",
        observable_type=ObservableType.URL,
        value="https://malicious.example/login?b=2&a=1",
        state=ProviderState.MALICIOUS,
        published_at=NOW,
        modified_at=NOW,
        phishing_kit="kit:example",
    )
    malware = MalwareMetadataRecord(
        record_id="malware-1",
        source_url="https://malware.example/records/1",
        observable_type=ObservableType.FILE_HASH,
        value="ab" * 32,
        state=ProviderState.MALICIOUS,
        published_at=NOW,
        modified_at=NOW,
        malware_family="family:example",
    )

    phishing_snapshot = map_phishing_metadata(
        phishing,
        source_id="phishing-provider",
    )
    malware_snapshot = map_malware_metadata(
        malware,
        source_id="malware-provider",
    )

    assert phishing_snapshot.relations[0].relation_type is (
        TelemetryRelationType.PHISHING_KIT
    )
    assert malware_snapshot.relations[0].relation_type is (
        TelemetryRelationType.MALWARE_FAMILY
    )


def test_schema_rejects_binary_sample_or_direct_validation() -> None:
    base = {
        "record_id": "malware-1",
        "source_url": "https://malware.example/records/1",
        "observable_type": ObservableType.FILE_HASH,
        "value": "ab" * 32,
        "state": ProviderState.MALICIOUS,
        "published_at": NOW,
        "modified_at": NOW,
        "malware_family": "family:example",
    }
    with pytest.raises(ValidationError, match="samples are outside"):
        MalwareMetadataRecord(**base, sample_available=True)
    with pytest.raises(ValidationError, match="download URLs are forbidden"):
        MalwareMetadataRecord(
            **base,
            sample_download_url="https://malware.example/samples/1",
        )
    with pytest.raises(ValidationError, match="direct validation"):
        MalwareMetadataRecord(**base, direct_validation=True)
