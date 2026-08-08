from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from cip.modules.corporate_graph.domain.blast_radius import BlastRadiusPreview
from cip.modules.corporate_graph.infrastructure.models import (
    CorporateGraphEdgeRecord,
    CorporateGraphNodeRecord,
)
from cip.modules.opportunities.infrastructure.models import CommercialSignalRecord, OpportunityRecord
from cip.modules.organizations.infrastructure.identity_models import OrganizationIdentityRecord
from cip.modules.relationship_intelligence.infrastructure.models import BusinessRelationshipRecord
from cip.modules.vulnerability_applicability.infrastructure.models import ApplicabilityAssessmentRecord


def build_blast_radius_preview(
    session: Session,
    *,
    node_key: str,
    organization_id: UUID | None,
) -> BlastRadiusPreview:
    node_keys = _affected_node_keys(session, node_key=node_key, organization_id=organization_id)
    graph_edges = _edge_count(session, node_keys)
    if organization_id is None:
        return BlastRadiusPreview(
            node_key=node_key,
            target_organization_key=None,
            graph_nodes=len(node_keys),
            graph_edges=graph_edges,
        )
    return BlastRadiusPreview(
        node_key=node_key,
        target_organization_key=f"organization:{organization_id}",
        graph_nodes=len(node_keys),
        graph_edges=graph_edges,
        organization_identities=_count(
            session,
            select(func.count()).select_from(OrganizationIdentityRecord).where(
                OrganizationIdentityRecord.organization_id == organization_id
            ),
        ),
        business_relationships=_count(
            session,
            select(func.count()).select_from(BusinessRelationshipRecord).where(
                or_(
                    BusinessRelationshipRecord.source_organization_id == organization_id,
                    BusinessRelationshipRecord.target_organization_id == organization_id,
                )
            ),
        ),
        applicability_assessments=_count(
            session,
            select(func.count()).select_from(ApplicabilityAssessmentRecord).where(
                ApplicabilityAssessmentRecord.organization_id == organization_id
            ),
        ),
        commercial_signals=_count(
            session,
            select(func.count()).select_from(CommercialSignalRecord).where(
                CommercialSignalRecord.organization_id == organization_id
            ),
        ),
        opportunities=_count(
            session,
            select(func.count()).select_from(OpportunityRecord).where(
                OpportunityRecord.organization_id == organization_id
            ),
        ),
    )


def _affected_node_keys(
    session: Session,
    *,
    node_key: str,
    organization_id: UUID | None,
) -> tuple[str, ...]:
    statement = select(CorporateGraphNodeRecord.node_key).where(
        CorporateGraphNodeRecord.node_key == node_key
    )
    if organization_id is not None:
        statement = select(CorporateGraphNodeRecord.node_key).where(
            or_(
                CorporateGraphNodeRecord.node_key == node_key,
                CorporateGraphNodeRecord.organization_id == organization_id,
            )
        )
    return tuple(session.scalars(statement).all())


def _edge_count(session: Session, node_keys: tuple[str, ...]) -> int:
    if not node_keys:
        return 0
    return _count(
        session,
        select(func.count()).select_from(CorporateGraphEdgeRecord).where(
            or_(
                CorporateGraphEdgeRecord.source_node_key.in_(node_keys),
                CorporateGraphEdgeRecord.target_node_key.in_(node_keys),
            )
        ),
    )


def _count(session: Session, statement: Select[tuple[int]]) -> int:
    value = session.scalar(statement)
    return int(value or 0)
