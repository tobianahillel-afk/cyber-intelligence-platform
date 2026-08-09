from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.corporate_graph.application.batches import GraphProjectionBatch
from cip.modules.corporate_graph.infrastructure.organization_identity_adapter import (
    project_organization_identities,
)
from cip.modules.corporate_graph.infrastructure.organization_reference_adapter import (
    project_organization_references,
)
from cip.modules.organizations.infrastructure.identity_models import (
    OrganizationIdentityRecord,
    OrganizationRelationshipRecord,
)
from cip.modules.organizations.infrastructure.models import OrganizationRecord


def load_organization_graph(session: Session) -> GraphProjectionBatch:
    organizations = tuple(session.scalars(select(OrganizationRecord)).all())
    identities = tuple(session.scalars(select(OrganizationIdentityRecord)).all())
    relationships = tuple(session.scalars(select(OrganizationRelationshipRecord)).all())
    references = project_organization_references(organizations)
    identity_graph = project_organization_identities(identities, relationships)
    return references.combine(identity_graph)
