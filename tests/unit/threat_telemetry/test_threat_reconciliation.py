from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from cip.modules.threat_telemetry.domain.models import (
    IndicatorSnapshot,
    IndicatorState,
    IndicatorType,
    SensorScope,
    TelemetryRelation,
    TelemetryRelationType,
    TelemetrySourceKind,
)
from cip.modules.threat_telemetry.domain.reconciliation import (
    reconcile_indicator_snapshots,
)

NOW = datetime(2026, 8, 6, 12, 0, tzinfo=UTC)


def test_syndication_counts_once_and_conflicting_states_remain_visible() -> None:
    malicious_a = replace(
        _snapshot(source_id="feed-a", record_key="a"),
        independence_key="upstream-story-1",
    )
    malicious_b = replace(
        malicious_a,
        source_id="feed-b",
        source_record_key="b",
        source_url="https://feed-b.example/records/b",
    )
    benign = replace(
        _snapshot(source_id="authoritative", record_key="c"),
        state=IndicatorState.BENIGN,
        confidence=1.0,
        source_precedence=90,
        modified_at=NOW + timedelta(hours=1),
    )

    indicator = reconcile_indicator_snapshots(
        (malicious_a, malicious_b, benign)
    )[0]

    assert indicator.state is IndicatorState.BENIGN
    assert set(indicator.observed_states) == {
        IndicatorState.MALICIOUS,
        IndicatorState.BENIGN,
    }
    assert indicator.source_count == 3
    assert indicator.independent_source_count == 1
    assert indicator.has_conflict is True


def test_latest_source_revision_can_retract_without_deleting_history() -> None:
    original = _snapshot(source_id="feed-a", record_key="record-1")
    retraction = replace(
        original,
        state=IndicatorState.RETRACTED,
        modified_at=NOW + timedelta(days=1),
        active=False,
        supersedes_record_key="record-1",
    )

    indicator = reconcile_indicator_snapshots((original, retraction))[0]

    assert indicator.state is IndicatorState.RETRACTED
    assert indicator.active is False
    assert indicator.independent_source_count == 0
    assert indicator.observed_states == (IndicatorState.RETRACTED,)


def test_shared_infrastructure_and_relations_are_preserved() -> None:
    first = replace(
        _snapshot(source_id="passive-dns", record_key="dns-1"),
        shared_infrastructure=True,
        sensor_scope=SensorScope.GLOBAL,
        relations=(
            TelemetryRelation(
                relation_type=TelemetryRelationType.CAMPAIGN,
                target_key="campaign:example",
                confidence=0.6,
            ),
        ),
    )
    second = replace(
        _snapshot(source_id="cti", record_key="cti-1"),
        relations=(
            TelemetryRelation(
                relation_type=TelemetryRelationType.CAMPAIGN,
                target_key="campaign:example",
                confidence=0.9,
            ),
            TelemetryRelation(
                relation_type=TelemetryRelationType.VULNERABILITY,
                target_key="CVE-2026-12345",
                confidence=0.7,
            ),
        ),
    )

    indicator = reconcile_indicator_snapshots((first, second))[0]
    relations = {
        (
            relation.relation_type,
            relation.target_key,
            relation.confidence,
        )
        for relation in indicator.relations
    }

    assert indicator.shared_infrastructure is True
    assert relations == {
        (TelemetryRelationType.CAMPAIGN, "campaign:example", 0.9),
        (TelemetryRelationType.VULNERABILITY, "CVE-2026-12345", 0.7),
    }


def test_snapshot_rejects_binary_payload_and_direct_validation() -> None:
    with pytest.raises(ValueError, match="metadata only"):
        replace(_snapshot(source_id="feed", record_key="1"), binary_payload_present=True)
    with pytest.raises(ValueError, match="direct indicator validation"):
        replace(
            _snapshot(source_id="feed", record_key="1"),
            direct_validation_performed=True,
        )


def _snapshot(*, source_id: str, record_key: str) -> IndicatorSnapshot:
    return IndicatorSnapshot(
        source_id=source_id,
        source_kind=TelemetrySourceKind.PROVIDER,
        source_record_key=record_key,
        source_url=f"https://{source_id}.example/records/{record_key}",
        indicator_type=IndicatorType.DOMAIN,
        indicator_value="malicious.example",
        state=IndicatorState.MALICIOUS,
        published_at=NOW,
        modified_at=NOW,
        first_seen_at=NOW - timedelta(hours=2),
        last_seen_at=NOW,
        expires_at=NOW + timedelta(days=30),
        confidence=0.8,
        source_precedence=50,
        metadata_only=True,
        relations=(),
    )
