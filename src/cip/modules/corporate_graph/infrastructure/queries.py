from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from cip.modules.corporate_graph.application.view_models import (
    GraphEdgeSummary,
    GraphNodeDetail,
    GraphNodeFilters,
    GraphNodePage,
    GraphNodeSnapshotView,
    GraphNodeSummary,
    ResolutionCandidateDetail,
    ResolutionCandidatePage,
    ResolutionCandidateSummary,
    ResolutionDecisionSummary,
)
from cip.modules.corporate_graph.domain.reconciliation import (
    reconcile_edge_snapshots,
    reconcile_node_snapshots,
)
from cip.modules.corporate_graph.infrastructure.blast_radius_queries import (
    build_blast_radius_preview,
)
from cip.modules.corporate_graph.infrastructure.errors import (
    GraphNodeNotFoundError,
    ResolutionCandidateNotFoundError,
)
from cip.modules.corporate_graph.infrastructure.models import (
    CorporateGraphEdgeRecord,
    CorporateGraphNodeRecord,
    CorporateGraphNodeSnapshotRecord,
    EntityResolutionCandidateRecord,
    EntityResolutionDecisionRecord,
)
from cip.modules.corporate_graph.infrastructure.projection_hydration import (
    edge_snapshots,
    node_snapshots,
)
from cip.modules.organizations.infrastructure.persistence_time import coerce_utc
from cip.shared.kernel.time import require_aware_utc


def list_graph_nodes(
    session: Session,
    *,
    filters: GraphNodeFilters,
    limit: int,
    offset: int,
) -> GraphNodePage:
    _validate_page(limit, offset)
    statement = _apply_node_filters(select(CorporateGraphNodeRecord), filters)
    total = session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = tuple(
        session.scalars(
            statement.order_by(
                CorporateGraphNodeRecord.last_observed_at.desc(),
                CorporateGraphNodeRecord.node_key,
            )
            .limit(limit)
            .offset(offset)
        )
    )
    return GraphNodePage(
        items=tuple(_node_summary(row) for row in rows),
        total=total,
        limit=limit,
        offset=offset,
    )


def get_graph_node_detail(
    session: Session,
    node_key: str,
    *,
    as_of: datetime | None = None,
) -> GraphNodeDetail:
    record = session.scalar(
        select(CorporateGraphNodeRecord).where(CorporateGraphNodeRecord.node_key == node_key)
    )
    if record is None:
        raise GraphNodeNotFoundError(node_key)
    effective_at = require_aware_utc(as_of, field_name="as_of") if as_of else None
    node = _node_summary_at(session, record, effective_at)
    snapshots = _node_snapshot_views(session, record.id, effective_at)
    outgoing = _related_edges(session, node_key=node_key, outgoing=True, as_of=effective_at)
    incoming = _related_edges(session, node_key=node_key, outgoing=False, as_of=effective_at)
    return GraphNodeDetail(
        node=node,
        snapshots=snapshots,
        outgoing_edges=outgoing,
        incoming_edges=incoming,
        as_of=effective_at,
    )


def list_resolution_candidates(
    session: Session,
    *,
    state: str | None,
    requires_review: bool | None,
    limit: int,
    offset: int,
) -> ResolutionCandidatePage:
    _validate_page(limit, offset)
    statement = select(EntityResolutionCandidateRecord)
    if state:
        statement = statement.where(EntityResolutionCandidateRecord.state == state)
    if requires_review is not None:
        statement = statement.where(
            EntityResolutionCandidateRecord.requires_review == requires_review
        )
    total = session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = tuple(
        session.scalars(
            statement.order_by(
                EntityResolutionCandidateRecord.requires_review.desc(),
                EntityResolutionCandidateRecord.score.desc(),
                EntityResolutionCandidateRecord.created_at,
            )
            .limit(limit)
            .offset(offset)
        )
    )
    return ResolutionCandidatePage(
        items=tuple(_candidate_summary(row) for row in rows),
        total=total,
        limit=limit,
        offset=offset,
    )


def get_resolution_candidate_detail(
    session: Session,
    candidate_id: UUID,
) -> ResolutionCandidateDetail:
    candidate = session.get(EntityResolutionCandidateRecord, candidate_id)
    if candidate is None:
        raise ResolutionCandidateNotFoundError(str(candidate_id))
    decisions = tuple(
        _decision_summary(row)
        for row in session.scalars(
            select(EntityResolutionDecisionRecord)
            .where(EntityResolutionDecisionRecord.candidate_id == candidate.id)
            .order_by(EntityResolutionDecisionRecord.decided_at)
        )
    )
    preview = build_blast_radius_preview(
        session,
        node_key=candidate.node_key,
        organization_id=candidate.candidate_organization_id,
    )
    return ResolutionCandidateDetail(
        candidate=_candidate_summary(candidate),
        decisions=decisions,
        blast_radius=preview,
    )


def _apply_node_filters(
    statement: Select[tuple[CorporateGraphNodeRecord]],
    filters: GraphNodeFilters,
) -> Select[tuple[CorporateGraphNodeRecord]]:
    if filters.node_type:
        statement = statement.where(CorporateGraphNodeRecord.node_type == filters.node_type)
    if filters.organization_id is not None:
        statement = statement.where(
            CorporateGraphNodeRecord.organization_id == filters.organization_id
        )
    if filters.current is not None:
        statement = statement.where(CorporateGraphNodeRecord.current == filters.current)
    if filters.suppressed is not None:
        statement = statement.where(CorporateGraphNodeRecord.suppressed == filters.suppressed)
    if filters.query:
        pattern = f"%{filters.query.strip()}%"
        statement = statement.where(
            or_(
                CorporateGraphNodeRecord.node_key.ilike(pattern),
                CorporateGraphNodeRecord.display_name.ilike(pattern),
            )
        )
    return statement


def _node_summary(record: CorporateGraphNodeRecord) -> GraphNodeSummary:
    return GraphNodeSummary(
        id=record.id,
        node_key=record.node_key,
        node_type=record.node_type,
        display_name=record.display_name,
        organization_id=record.organization_id,
        source_count=record.source_count,
        confidence=record.confidence,
        current=record.current,
        suppressed=record.suppressed,
        first_observed_at=coerce_utc(record.first_observed_at),
        last_observed_at=coerce_utc(record.last_observed_at),
    )


def _node_summary_at(
    session: Session,
    record: CorporateGraphNodeRecord,
    as_of: datetime | None,
) -> GraphNodeSummary:
    if as_of is None:
        return _node_summary(record)
    snapshots = tuple(
        snapshot
        for snapshot in node_snapshots(session, record.id)
        if snapshot.observed_at <= as_of
    )
    if not snapshots:
        raise GraphNodeNotFoundError(record.node_key)
    projection = reconcile_node_snapshots(snapshots, now=as_of)
    return GraphNodeSummary(
        id=record.id,
        node_key=projection.node_key,
        node_type=projection.node_type.value,
        display_name=projection.display_name,
        organization_id=projection.organization_id,
        source_count=projection.source_count,
        confidence=projection.confidence,
        current=projection.current,
        suppressed=projection.suppressed,
        first_observed_at=projection.first_observed_at,
        last_observed_at=projection.last_observed_at,
    )


def _node_snapshot_views(
    session: Session,
    node_id: UUID,
    as_of: datetime | None,
) -> tuple[GraphNodeSnapshotView, ...]:
    statement = select(CorporateGraphNodeSnapshotRecord).where(
        CorporateGraphNodeSnapshotRecord.node_id == node_id
    )
    if as_of is not None:
        statement = statement.where(CorporateGraphNodeSnapshotRecord.observed_at <= as_of)
    rows = session.scalars(statement.order_by(CorporateGraphNodeSnapshotRecord.observed_at.desc()))
    return tuple(
        GraphNodeSnapshotView(
            id=row.id,
            snapshot_key=row.snapshot_key,
            source_module=row.source_module,
            source_entity_type=row.source_entity_type,
            source_record_key=row.source_record_key,
            source_url=row.source_url,
            organization_id=row.organization_id,
            observed_at=coerce_utc(row.observed_at),
            valid_from=coerce_utc(row.valid_from) if row.valid_from else None,
            valid_until=coerce_utc(row.valid_until) if row.valid_until else None,
            confidence=row.confidence,
            active=row.active,
            suppressed=row.suppressed,
        )
        for row in rows
    )


def _related_edges(
    session: Session,
    *,
    node_key: str,
    outgoing: bool,
    as_of: datetime | None,
) -> tuple[GraphEdgeSummary, ...]:
    column = (
        CorporateGraphEdgeRecord.source_node_key
        if outgoing
        else CorporateGraphEdgeRecord.target_node_key
    )
    records = tuple(session.scalars(select(CorporateGraphEdgeRecord).where(column == node_key)))
    summaries: list[GraphEdgeSummary] = []
    for record in records:
        summary = _edge_summary_at(session, record, as_of)
        if summary is not None:
            summaries.append(summary)
    return tuple(sorted(summaries, key=lambda item: (item.edge_type, item.edge_key)))


def _edge_summary_at(
    session: Session,
    record: CorporateGraphEdgeRecord,
    as_of: datetime | None,
) -> GraphEdgeSummary | None:
    if as_of is None:
        return _edge_summary(record)
    snapshots = tuple(
        snapshot
        for snapshot in edge_snapshots(session, record.id)
        if snapshot.observed_at <= as_of
    )
    if not snapshots:
        return None
    projection = reconcile_edge_snapshots(snapshots, now=as_of)
    return GraphEdgeSummary(
        id=record.id,
        edge_key=projection.edge_key,
        source_node_key=projection.source_node_key,
        target_node_key=projection.target_node_key,
        edge_type=projection.edge_type.value,
        source_module=projection.source_module,
        source_evidence_class=projection.source_evidence_class,
        review_state=projection.review_state.value,
        confidence=projection.confidence,
        current=projection.current,
        suppressed=projection.suppressed,
        valid_from=projection.valid_from,
        valid_until=projection.valid_until,
        first_observed_at=projection.first_observed_at,
        last_observed_at=projection.last_observed_at,
    )


def _edge_summary(record: CorporateGraphEdgeRecord) -> GraphEdgeSummary:
    return GraphEdgeSummary(
        id=record.id,
        edge_key=record.edge_key,
        source_node_key=record.source_node_key,
        target_node_key=record.target_node_key,
        edge_type=record.edge_type,
        source_module=record.source_module,
        source_evidence_class=record.source_evidence_class,
        review_state=record.review_state,
        confidence=record.confidence,
        current=record.current,
        suppressed=record.suppressed,
        valid_from=coerce_utc(record.valid_from) if record.valid_from else None,
        valid_until=coerce_utc(record.valid_until) if record.valid_until else None,
        first_observed_at=coerce_utc(record.first_observed_at),
        last_observed_at=coerce_utc(record.last_observed_at),
    )


def _candidate_summary(record: EntityResolutionCandidateRecord) -> ResolutionCandidateSummary:
    return ResolutionCandidateSummary(
        id=record.id,
        node_key=record.node_key,
        candidate_organization_id=record.candidate_organization_id,
        method=record.method,
        score=record.score,
        reasons=tuple(json.loads(record.reasons_json)),
        conflicting_organization_ids=tuple(
            UUID(value) for value in json.loads(record.conflicting_organization_ids_json)
        ),
        state=record.state,
        requires_review=record.requires_review,
        created_at=coerce_utc(record.created_at),
        updated_at=coerce_utc(record.updated_at),
    )


def _decision_summary(record: EntityResolutionDecisionRecord) -> ResolutionDecisionSummary:
    return ResolutionDecisionSummary(
        id=record.id,
        candidate_id=record.candidate_id,
        node_key=record.node_key,
        decision_type=record.decision_type,
        actor=record.actor,
        reason=record.reason,
        organization_id=record.organization_id,
        reverses_decision_id=record.reverses_decision_id,
        blast_radius_fingerprint=record.blast_radius_fingerprint,
        decided_at=coerce_utc(record.decided_at),
    )


def _validate_page(limit: int, offset: int) -> None:
    if not 1 <= limit <= 200:
        raise ValueError("limit must be between 1 and 200")
    if offset < 0:
        raise ValueError("offset cannot be negative")
