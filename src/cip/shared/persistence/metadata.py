from __future__ import annotations

from sqlalchemy import MetaData

from cip.modules.collection_orchestration.infrastructure.models import (
    CollectionCheckpointRecord,
    CollectionCircuitRecord,
    CollectionDeadLetterRecord,
    CollectionJobRecord,
)
from cip.modules.data_governance.infrastructure.models import SuppressionRecord
from cip.modules.evidence.infrastructure.models import EvidenceRecord
from cip.modules.opportunities.infrastructure.models import (
    CommercialSignalRecord,
    NeedHypothesisRecord,
    NeedHypothesisSignalRecord,
    OpportunityEvidenceRecord,
    OpportunityRecord,
    OpportunityReviewRecord,
    OpportunityScoreComponentRecord,
)
from cip.modules.organizations.infrastructure.identity_models import (
    OrganizationAliasRecord,
    OrganizationIdentifierRecord,
    OrganizationIdentityClaimRecord,
    OrganizationIdentityEvidenceRecord,
    OrganizationIdentityRecord,
    OrganizationMergeCandidateRecord,
    OrganizationRelationshipRecord,
)
from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.modules.provider_onboarding.infrastructure.models import (
    ProviderOnboardingAuditRecord,
    ProviderOnboardingRecord,
)
from cip.modules.raw_observations.infrastructure.models import RawObservationRecord
from cip.modules.source_governance.infrastructure.models import SourceRecord
from cip.shared.persistence.base import Base

_IMPORTED_MODELS = (
    CollectionCheckpointRecord,
    CollectionCircuitRecord,
    CollectionDeadLetterRecord,
    CollectionJobRecord,
    CommercialSignalRecord,
    EvidenceRecord,
    NeedHypothesisRecord,
    NeedHypothesisSignalRecord,
    OpportunityEvidenceRecord,
    OpportunityRecord,
    OpportunityReviewRecord,
    OpportunityScoreComponentRecord,
    OrganizationAliasRecord,
    OrganizationIdentifierRecord,
    OrganizationIdentityClaimRecord,
    OrganizationIdentityEvidenceRecord,
    OrganizationIdentityRecord,
    OrganizationMergeCandidateRecord,
    OrganizationRecord,
    OrganizationRelationshipRecord,
    ProviderOnboardingAuditRecord,
    ProviderOnboardingRecord,
    RawObservationRecord,
    SourceRecord,
    SuppressionRecord,
)


def get_metadata() -> MetaData:
    """Return metadata after importing all module-owned persistence records."""

    return Base.metadata
