from __future__ import annotations

from collections.abc import Iterable, Mapping
from types import MappingProxyType

from cip.modules.raw_observations.domain.entities import (
    RawObservation,
    SourceRecordAction,
)


def reduce_source_record_state(
    observations: Iterable[RawObservation],
) -> Mapping[str, RawObservation]:
    """Reduce immutable source events into their current active records.

    Ordering is based on provider-effective time, then collection time and event ID,
    so historical backfills and incremental batches converge to the same state.
    """

    ordered = sorted(
        observations,
        key=lambda observation: (
            observation.effective_at,
            observation.collected_at,
            str(observation.id),
        ),
    )
    current: dict[str, RawObservation] = {}
    for observation in ordered:
        record_key = observation.source_record_key
        if record_key is None:
            continue
        if observation.source_record_action in {
            SourceRecordAction.TOMBSTONE,
            SourceRecordAction.RETRACTION,
        }:
            current.pop(record_key, None)
        else:
            current[record_key] = observation
    return MappingProxyType(current)
