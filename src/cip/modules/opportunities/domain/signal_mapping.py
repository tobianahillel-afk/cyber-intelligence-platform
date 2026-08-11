from __future__ import annotations

from dataclasses import replace

from cip.modules.opportunities.domain.entities import (
    CommercialSignal,
    NeedHypothesisClass,
    SignalType,
)
from cip.modules.service_taxonomy.domain.classifier import classify_service_families
from cip.modules.service_taxonomy.domain.models import SERVICE_TAXONOMY_VERSION


def map_signal_to_canonical_needs(
    signal: CommercialSignal,
    *,
    source_id: str,
) -> CommercialSignal:
    source = source_id.strip()
    if not source:
        raise ValueError("source_id is required")
    if signal.service_families and signal.hypothesis_classes:
        return _with_source_independence(signal, source_id=source)
    mapping = _legacy_mapping(signal)
    if mapping is None:
        return _with_source_independence(signal, source_id=source)
    hypothesis_classes, explicit = mapping
    matches = classify_service_families(signal.title, signal.summary)
    if not matches:
        return _with_source_independence(signal, source_id=source)
    families = tuple(match.family for match in matches)
    matched_terms = tuple(
        dict.fromkeys(
            signal.matched_terms
            + tuple(term for match in matches for term in match.matched_terms)
        )
    )
    return replace(
        signal,
        service_families=families,
        hypothesis_classes=hypothesis_classes,
        matched_terms=matched_terms,
        independence_key=signal.independence_key or f"source:{source}",
        corroboration_group_key=signal.corroboration_group_key or f"source:{source}",
        is_explicit=signal.is_explicit or explicit,
        mapping_rule_id="canonical-service-taxonomy",
        mapping_rule_version=SERVICE_TAXONOMY_VERSION,
    )


def _legacy_mapping(
    signal: CommercialSignal,
) -> tuple[tuple[NeedHypothesisClass, ...], bool] | None:
    if signal.signal_type is SignalType.PUBLIC_TENDER:
        return (NeedHypothesisClass.EXPLICIT_PROCUREMENT,), True
    if signal.signal_type is SignalType.JOB_POSTING:
        return (
            NeedHypothesisClass.CAPABILITY_GAP,
            NeedHypothesisClass.PROGRAM_BUILD_TRANSFORMATION,
            NeedHypothesisClass.SKILLS_TRAINING,
        ), False
    return None


def _with_source_independence(
    signal: CommercialSignal,
    *,
    source_id: str,
) -> CommercialSignal:
    if signal.independence_key is not None:
        return signal
    return replace(signal, independence_key=f"source:{source_id}")
