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
    target_organization: Organization | None = None
    merge_candidates: tuple[IdentityMergeCandidate, ...] = ()
    relationships: tuple[IdentityRelationship, ...] = ()

    def __post_init__(self) -> None:
        if self.identity.source_id != self.evidence.source_id:
            raise ValueError("identity and evidence source must match")
        if self.target_organization is None and self.identity.organization_id is not None:
            raise ValueError("attached identity requires its target organization projection")
        if self.target_organization is not None:
            expected = self.target_organization.id
            if self.identity.organization_id not in {None, expected}:
                raise ValueError("identity organization must match target organization")
        for candidate in self.merge_candidates:
            if candidate.identity_id != self.identity.id:
                raise ValueError("merge candidate identity must match projection")
        auto_confirmed = [
            candidate
            for candidate in self.merge_candidates
            if candidate.state is MatchState.AUTO_CONFIRMED
        ]
        if len(auto_confirmed) > 1:
            raise ValueError("identity projection cannot auto-confirm multiple organizations")
        if auto_confirmed and self.target_organization is None:
            raise ValueError("auto-confirmed identity requires a target organization")

    @property
    def attached_organization_id(self) -> UUID | None:
        if self.target_organization is not None:
            return self.target_organization.id
        return self.identity.organization_id
