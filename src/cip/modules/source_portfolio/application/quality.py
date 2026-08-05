from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from cip.modules.raw_observations.domain.entities import RawObservation
from cip.modules.source_portfolio.domain.models import AnomalyState, SchemaState
from cip.modules.source_portfolio.infrastructure.models import SourceQualityBaselineRecord
from cip.shared.kernel.time import require_aware_utc

MIN_BASELINE_SAMPLES = 3
EWMA_ALPHA = 0.25
VOLUME_LOW_RATIO = 0.2
VOLUME_HIGH_RATIO = 5.0
FIELD_EXPECTED_THRESHOLD = 0.8
FIELD_DROP_THRESHOLD = 0.4


@dataclass(frozen=True, slots=True)
class QualityEvaluation:
    volume_state: AnomalyState
    field_population_state: AnomalyState
    schema_state: SchemaState


def evaluate_quality(
    session: Session,
    source_id: str,
    observations: Sequence[RawObservation],
    *,
    not_modified: bool,
    now: datetime,
) -> QualityEvaluation | None:
    if not_modified:
        return None
    changed_at = require_aware_utc(now, field_name="now")
    baseline = session.get(SourceQualityBaselineRecord, source_id)
    if baseline is None:
        baseline = SourceQualityBaselineRecord(
            source_id=source_id,
            sample_count=0,
            expected_records_per_run=None,
            last_records_count=None,
            accepted_schema_fingerprints=[],
            last_schema_fingerprints=[],
            field_population_baseline={},
            last_field_population={},
            updated_at=changed_at,
        )
        session.add(baseline)

    records_count = len(observations)
    fingerprints = sorted(
        {
            fingerprint
            for observation in observations
            if (fingerprint := _normalized_text(observation.schema_fingerprint))
        }
    )
    population = _field_population(observations)
    volume_state = _volume_state(baseline, records_count)
    field_state = _field_state(baseline, population)
    schema_state = _schema_state(baseline, fingerprints)

    baseline.last_records_count = records_count
    baseline.last_schema_fingerprints = fingerprints
    baseline.last_field_population = population
    warming_up = baseline.sample_count < MIN_BASELINE_SAMPLES
    accepted_sample = warming_up or (
        volume_state is AnomalyState.NORMAL
        and field_state is AnomalyState.NORMAL
        and schema_state is SchemaState.STABLE
    )
    if accepted_sample:
        baseline.expected_records_per_run = _ewma(
            baseline.expected_records_per_run,
            float(records_count),
        )
        baseline.field_population_baseline = _population_ewma(
            baseline.field_population_baseline,
            population,
        )
        if warming_up:
            baseline.accepted_schema_fingerprints = sorted(
                set(baseline.accepted_schema_fingerprints) | set(fingerprints)
            )
        baseline.sample_count += 1
    baseline.updated_at = changed_at
    return QualityEvaluation(
        volume_state=volume_state,
        field_population_state=field_state,
        schema_state=schema_state,
    )


def _volume_state(
    baseline: SourceQualityBaselineRecord,
    records_count: int,
) -> AnomalyState:
    expected = baseline.expected_records_per_run
    if baseline.sample_count < MIN_BASELINE_SAMPLES or expected is None:
        return AnomalyState.NORMAL
    if expected == 0:
        return AnomalyState.ANOMALOUS if records_count > 0 else AnomalyState.NORMAL
    lower = expected * VOLUME_LOW_RATIO
    upper = expected * VOLUME_HIGH_RATIO
    return (
        AnomalyState.ANOMALOUS
        if records_count < lower or records_count > upper
        else AnomalyState.NORMAL
    )


def _field_state(
    baseline: SourceQualityBaselineRecord,
    population: dict[str, float],
) -> AnomalyState:
    if baseline.sample_count < MIN_BASELINE_SAMPLES or not population:
        return AnomalyState.NORMAL
    for field_name, expected in baseline.field_population_baseline.items():
        current = population.get(field_name, 0.0)
        if (
            expected >= FIELD_EXPECTED_THRESHOLD
            and current < expected - FIELD_DROP_THRESHOLD
        ):
            return AnomalyState.ANOMALOUS
    return AnomalyState.NORMAL


def _schema_state(
    baseline: SourceQualityBaselineRecord,
    fingerprints: list[str],
) -> SchemaState:
    if baseline.sample_count < MIN_BASELINE_SAMPLES or not fingerprints:
        return SchemaState.STABLE
    accepted = set(baseline.accepted_schema_fingerprints)
    return (
        SchemaState.DRIFTED
        if not set(fingerprints).issubset(accepted)
        else SchemaState.STABLE
    )


def _field_population(observations: Sequence[RawObservation]) -> dict[str, float]:
    if not observations:
        return {}
    total = len(observations)
    populated = {
        "source_record_key": sum(
            bool(_normalized_text(observation.source_record_key))
            for observation in observations
        ),
        "event_time": sum(
            observation.observed_at is not None
            or observation.published_at is not None
            or observation.source_updated_at is not None
            for observation in observations
        ),
        "content_language": sum(
            bool(_normalized_text(observation.content_language))
            for observation in observations
        ),
        "schema_fingerprint": sum(
            bool(_normalized_text(observation.schema_fingerprint))
            for observation in observations
        ),
        "payload_reference": sum(
            bool(_normalized_text(observation.payload_reference))
            for observation in observations
        ),
    }
    return {field_name: count / total for field_name, count in populated.items()}


def _normalized_text(value: str | None) -> str:
    return value.strip() if value else ""


def _ewma(previous: float | None, current: float) -> float:
    if previous is None:
        return current
    return (1 - EWMA_ALPHA) * previous + EWMA_ALPHA * current


def _population_ewma(
    previous: dict[str, float],
    current: dict[str, float],
) -> dict[str, float]:
    if not current:
        return dict(previous)
    fields = set(previous) | set(current)
    return {
        field_name: _ewma(previous.get(field_name), current.get(field_name, 0.0))
        for field_name in fields
    }
