from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from cip.modules.passive_exposure.domain.models import (
    AttributionRisk,
    OrganizationLinkStatus,
    PassiveAsset,
    PassiveObservationState,
    TechnologyObservation,
)


@dataclass(frozen=True, slots=True)
class ObservedService:
    port: int
    protocol: str


@dataclass(frozen=True, slots=True)
class ReconciledOrganizationLink:
    status: OrganizationLinkStatus
    exact_organization_id: UUID | None
    candidate_organization_ids: tuple[UUID, ...]
    reasons: tuple[str, ...]
    attribution_risks: tuple[AttributionRisk, ...]

    @property
    def requires_review(self) -> bool:
        return self.status in {
            OrganizationLinkStatus.CANDIDATE,
            OrganizationLinkStatus.REVIEW_REQUIRED,
        }


@dataclass(frozen=True, slots=True)
class ReconciledPassiveAsset:
    asset: PassiveAsset
    state: PassiveObservationState
    observed_states: tuple[PassiveObservationState, ...]
    first_seen_at: datetime
    last_seen_at: datetime
    expires_at: datetime | None
    last_updated_at: datetime
    source_count: int
    independent_source_count: int
    active: bool
    historical_only: bool
    has_conflict: bool
    organization_link: ReconciledOrganizationLink
    attribution_risks: tuple[AttributionRisk, ...]
    technologies: tuple[TechnologyObservation, ...]
    services: tuple[ObservedService, ...]

    @property
    def can_support_exposure_conclusion(self) -> bool:
        return False
