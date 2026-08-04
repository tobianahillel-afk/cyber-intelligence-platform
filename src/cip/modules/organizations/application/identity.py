from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from cip.modules.evidence.domain.entities import Evidence
from cip.modules.organizations.domain.entities import Organization
from cip.modules.organizations.domain.identity import (
    IdentityMergeCandidate,
    IdentityRelationship,
    MatchState,
    OrganizationIdentity,
)


@dataclass(frozen=True, slots=True)
class IdentityProjection:
    identity: OrganizationIdentity
    evidence: Evidence
    attached_organization: Organization | None = None
    candidate_organizations: tuple[Organization, ...] = ()
    merge_candidates: tuple[IdentityMergeCandidate, ...] = ()
    relationships: tuple[IdentityRelationship, ...] = ()

    def __post_init__(self) -> None:
        if self.identity.source_id != self.evidence.source_id:
            raise ValueError("identity and evidence source must match")
        if self.attached_organization is None and self.identity.organization_id is not None:
            raise ValueError("attached identity requires its organization projection")
        if self.attached_organization is not None:
            expected = self.attached_organization.id
            if self.identity.organization_id not in {None, expected}:
                raise ValueError("identity organization must match attached organization")
        organizations = {
            organization.id: organization
            for organization in (
                *((self.attached_organization,) if self.attached_organization else ()),
                *self.candidate_organizations,
            )
        }
        for candidate in self.merge_candidates:
            if candidate.identity_id != self.identity.id:
                raise ValueError("merge candidate identity must match projection")
            if candidate.organization_id not in organizations:
                raise ValueError("merge candidate organization must be projected")
        auto_confirmed = [
            candidate
            for candidate in self.merge_candidates
            if candidate.state is MatchState.AUTO_CONFIRMED
        ]
        if len(auto_confirmed) > 1:
            raise ValueError("identity projection cannot auto-confirm multiple organizations")
        if auto_confirmed:
            attached_id = self.attached_organization.id if self.attached_organization else None
            if attached_id != auto_confirmed[0].organization_id:
                raise ValueError("auto-confirmed candidate must be the attached organization")

    @property
    def projected_organizations(self) -> tuple[Organization, ...]:
        values = [*self.candidate_organizations]
        if self.attached_organization is not None:
            values.append(self.attached_organization)
        return tuple({organization.id: organization for organization in values}.values())

    @property
    def attached_organization_id(self) -> UUID | None:
        if self.attached_organization is not None:
            return self.attached_organization.id
        return self.identity.organization_id
