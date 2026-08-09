from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import datetime
from typing import TypeVar

from cip.modules.corporate_graph.domain.models import (
    GraphEdgeProjection,
    GraphEdgeSnapshot,
    GraphNodeProjection,
    GraphNodeSnapshot,
    GraphReviewState,
)
from cip.shared.kernel.time import require_aware_utc

T = TypeVar("T")


def reconcile_node_snapshots(
    snapshots: Iterable[GraphNodeSnapshot],
    *,
    now: datetime,
) -> GraphNodeProjection:
    items = tuple(snapshots)
    if not items:
        raise ValueError("at least one graph node snapshot is required")
    _require_same(items, lambda item: item.node_key, "node_key")
    _require_same(items, lambda item: item.node_type, "node_type")
    current = require_aware_utc(now, field_name="now")
    ordered = sorted(items, key=lambda item: item.observed_at)
    latest = ordered[-1]
    current_items = (
        ()
        if latest.suppressed
        else tuple(item for item in ordered if item.is_current_at(current))
    )
    organization_ids = {item.organization_id for item in current_items if item.organization_id}
    organization_id = next(iter(organization_ids)) if len(organization_ids) == 1 else None
    active_items = current_items or (latest,)
    return GraphNodeProjection(
        node_key=latest.node_key,
        node_type=latest.node_type,
        display_name=latest.display_name,
        organization_id=organization_id,
        source_count=len({item.source_module for item in active_items}),
        confidence=max(item.confidence for item in active_items),
        current=bool(current_items),
        suppressed=latest.suppressed,
        first_observed_at=ordered[0].observed_at,
        last_observed_at=latest.observed_at,
    )


def reconcile_edge_snapshots(
    snapshots: Iterable[GraphEdgeSnapshot],
    *,
    now: datetime,
) -> GraphEdgeProjection:
    items = tuple(snapshots)
    if not items:
        raise ValueError("at least one graph edge snapshot is required")
    _require_same(items, lambda item: item.edge_key, "edge_key")
    _require_same(items, lambda item: item.source_node_key, "source_node_key")
    _require_same(items, lambda item: item.target_node_key, "target_node_key")
    _require_same(items, lambda item: item.edge_type, "edge_type")
    current = require_aware_utc(now, field_name="now")
    effective = _effective_edge_revisions(items)
    ordered = sorted(effective, key=lambda item: item.observed_at)
    current_items = tuple(item for item in ordered if item.is_current_at(current))
    basis = current_items or (ordered[-1],)
    evidence_classes = {item.source_evidence_class for item in basis}
    source_modules = {item.source_module for item in basis}
    return GraphEdgeProjection(
        edge_key=ordered[-1].edge_key,
        source_node_key=ordered[-1].source_node_key,
        target_node_key=ordered[-1].target_node_key,
        edge_type=ordered[-1].edge_type,
        source_module=_single_or_multiple(source_modules),
        source_evidence_class=_single_or_multiple(evidence_classes),
        review_state=_review_state(basis),
        confidence=max(item.confidence for item in basis),
        current=bool(current_items),
        suppressed=not current_items and all(item.suppressed for item in basis),
        valid_from=_earliest(item.valid_from for item in basis),
        valid_until=_latest(item.valid_until for item in basis),
        first_observed_at=ordered[0].observed_at,
        last_observed_at=ordered[-1].observed_at,
    )


def _effective_edge_revisions(
    snapshots: tuple[GraphEdgeSnapshot, ...],
) -> tuple[GraphEdgeSnapshot, ...]:
    superseded = {
        (snapshot.source_module, snapshot.supersedes_record_key)
        for snapshot in snapshots
        if snapshot.supersedes_record_key is not None
    }
    latest_by_record: dict[tuple[str, str], GraphEdgeSnapshot] = {}
    for snapshot in sorted(snapshots, key=lambda item: item.observed_at):
        latest_by_record[(snapshot.source_module, snapshot.source_record_key)] = snapshot
    effective = tuple(
        snapshot
        for identity, snapshot in latest_by_record.items()
        if identity not in superseded
    )
    if not effective:
        return (max(snapshots, key=lambda item: item.observed_at),)
    return effective


def _review_state(items: tuple[GraphEdgeSnapshot, ...]) -> GraphReviewState:
    states = {item.review_state for item in items}
    if GraphReviewState.REVIEW_REQUIRED in states:
        return GraphReviewState.REVIEW_REQUIRED
    if states == {GraphReviewState.REJECTED}:
        return GraphReviewState.REJECTED
    if GraphReviewState.CONFIRMED in states:
        return GraphReviewState.CONFIRMED
    if GraphReviewState.AUTO_CONFIRMED in states:
        return GraphReviewState.AUTO_CONFIRMED
    return GraphReviewState.UNREVIEWED


def _single_or_multiple(values: set[str]) -> str:
    if len(values) == 1:
        return next(iter(values))
    return "multiple"


def _earliest(values: Iterable[datetime | None]) -> datetime | None:
    concrete = tuple(value for value in values if value is not None)
    return min(concrete) if concrete else None


def _latest(values: Iterable[datetime | None]) -> datetime | None:
    concrete = tuple(value for value in values if value is not None)
    return max(concrete) if concrete else None


def _require_same(items: tuple[T, ...], getter: Callable[[T], object], label: str) -> None:
    expected = getter(items[0])
    if any(getter(item) != expected for item in items[1:]):
        raise ValueError(f"graph snapshots must share {label}")
