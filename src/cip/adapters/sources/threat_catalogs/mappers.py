from __future__ import annotations

from cip.adapters.sources.threat_catalogs.schemas import (
    MalwareMetadataRecord,
    PassiveDnsMetadataRecord,
    PhishingMetadataRecord,
    RelationMetadata,
    StixTaxiiIndicatorRecord,
    ThreatMetadataRecord,
)
from cip.modules.threat_telemetry.domain.models import (
    IndicatorSnapshot,
    IndicatorState,
    IndicatorType,
    SensorScope,
    TelemetryRelation,
    TelemetryRelationType,
    TelemetrySourceKind,
)


def map_stix_taxii_indicator(
    record: StixTaxiiIndicatorRecord,
    *,
    source_id: str,
) -> IndicatorSnapshot:
    state = IndicatorState.RETRACTED if record.revoked else IndicatorState(record.state)
    return _map_record(
        record,
        source_id=source_id,
        source_kind=TelemetrySourceKind.STIX_TAXII,
        state=state,
    )


def map_phishing_metadata(
    record: PhishingMetadataRecord,
    *,
    source_id: str,
) -> IndicatorSnapshot:
    relations = list(_relations(record.relations))
    if record.phishing_kit:
        relations.append(
            TelemetryRelation(
                relation_type=TelemetryRelationType.PHISHING_KIT,
                target_key=record.phishing_kit,
                confidence=record.confidence,
            )
        )
    return _map_record(
        record,
        source_id=source_id,
        source_kind=TelemetrySourceKind.PHISHING_FEED,
        relations=tuple(relations),
    )


def map_passive_dns_metadata(
    record: PassiveDnsMetadataRecord,
    *,
    source_id: str,
) -> IndicatorSnapshot:
    return _map_record(
        record,
        source_id=source_id,
        source_kind=TelemetrySourceKind.PASSIVE_DNS,
    )


def map_malware_metadata(
    record: MalwareMetadataRecord,
    *,
    source_id: str,
) -> IndicatorSnapshot:
    relations = list(_relations(record.relations))
    relations.append(
        TelemetryRelation(
            relation_type=TelemetryRelationType.MALWARE_FAMILY,
            target_key=record.malware_family,
            confidence=record.confidence,
        )
    )
    return _map_record(
        record,
        source_id=source_id,
        source_kind=TelemetrySourceKind.MALWARE_METADATA,
        relations=tuple(relations),
    )


def _map_record(
    record: ThreatMetadataRecord,
    *,
    source_id: str,
    source_kind: TelemetrySourceKind,
    state: IndicatorState | None = None,
    relations: tuple[TelemetryRelation, ...] | None = None,
) -> IndicatorSnapshot:
    return IndicatorSnapshot(
        source_id=source_id,
        source_kind=source_kind,
        source_record_key=record.record_id,
        source_url=record.source_url,
        indicator_type=IndicatorType(record.observable_type),
        indicator_value=record.value,
        state=state or IndicatorState(record.state),
        published_at=record.published_at,
        modified_at=record.modified_at,
        first_seen_at=record.first_seen_at,
        last_seen_at=record.last_seen_at,
        expires_at=record.expires_at,
        independence_key=record.independence_key,
        sensor_scope=_sensor_scope(record.sensor_scope),
        confidence=record.confidence,
        source_precedence=record.source_precedence,
        active=record.active,
        shared_infrastructure=(
            record.shared_infrastructure
            or record.state.value == IndicatorState.SHARED_INFRASTRUCTURE.value
        ),
        historical_only=record.historical_only,
        metadata_only=True,
        binary_payload_present=False,
        direct_validation_performed=False,
        supersedes_record_key=record.supersedes_record_key,
        relations=relations if relations is not None else _relations(record.relations),
    )


def _relations(
    records: tuple[RelationMetadata, ...],
) -> tuple[TelemetryRelation, ...]:
    return tuple(
        TelemetryRelation(
            relation_type=TelemetryRelationType(record.kind),
            target_key=record.target_key,
            confidence=record.confidence,
        )
        for record in records
    )


def _sensor_scope(value: str) -> SensorScope:
    try:
        return SensorScope(value)
    except ValueError:
        return SensorScope.UNKNOWN
