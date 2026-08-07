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
from cip.modules.incident_intelligence.infrastructure.models import (
    IncidentClaimSnapshotRecord,
    IncidentRecord,
)
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
from cip.modules.passive_exposure.infrastructure.models import (
    PassiveAssetRecord,
    PassiveObservationSnapshotRecord,
    PassiveTechnologyRecord,
)
from cip.modules.procurement_history.infrastructure.models import (
    ProcurementContractPartyRecord,
    ProcurementContractRecord,
    ProcurementProcedureRecord,
    ProcurementPublicationRecord,
    ProcurementServiceClassificationRecord,
)
from cip.modules.provider_onboarding.infrastructure.models import (
    ProviderOnboardingAuditRecord,
    ProviderOnboardingRecord,
)
from cip.modules.public_footprint.infrastructure.models import (
    PublicClaimRecord,
    PublicResourceRecord,
    PublicResourceVersionRecord,
)
from cip.modules.raw_observations.infrastructure.models import RawObservationRecord
from cip.modules.source_governance.infrastructure.models import SourceRecord
from cip.modules.source_portfolio.infrastructure.models import (
    AdapterCapabilityRecord,
    BackfillPartitionRecord,
    SourceHealthRecord,
    SourcePortfolioAuditRecord,
    SourcePortfolioRecord,
    SourceQualityBaselineRecord,
    SourceValueEventRecord,
)
from cip.modules.threat_telemetry.infrastructure.models import (
    ThreatIndicatorRecord,
    ThreatIndicatorRelationRecord,
    ThreatIndicatorSnapshotRecord,
)
from cip.modules.vulnerability_applicability.infrastructure.models import (
    ApplicabilityAssessmentRecord,
    ApplicabilityAssessmentSnapshotRecord,
    VendorAdvisoryRangeRecord,
    VendorAdvisoryRevisionRecord,
    VendorProductRecord,
)
from cip.modules.vulnerability_knowledge.infrastructure.models import (
    VulnerabilityAffectedRangeRecord,
    VulnerabilityAliasRecord,
    VulnerabilityCweRecord,
    VulnerabilityExploitationRecord,
    VulnerabilityRecord,
    VulnerabilityReferenceRecord,
    VulnerabilityScoreRecord,
    VulnerabilitySourceSnapshotRecord,
)
from cip.shared.persistence.base import Base

_IMPORTED_MODELS = (
    AdapterCapabilityRecord,
    ApplicabilityAssessmentRecord,
    ApplicabilityAssessmentSnapshotRecord,
    BackfillPartitionRecord,
    CollectionCheckpointRecord,
    CollectionCircuitRecord,
    CollectionDeadLetterRecord,
    CollectionJobRecord,
    CommercialSignalRecord,
    EvidenceRecord,
    IncidentClaimSnapshotRecord,
    IncidentRecord,
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
    PassiveAssetRecord,
    PassiveObservationSnapshotRecord,
    PassiveTechnologyRecord,
    ProcurementContractPartyRecord,
    ProcurementContractRecord,
    ProcurementProcedureRecord,
    ProcurementPublicationRecord,
    ProcurementServiceClassificationRecord,
    ProviderOnboardingAuditRecord,
    ProviderOnboardingRecord,
    PublicClaimRecord,
    PublicResourceRecord,
    PublicResourceVersionRecord,
    RawObservationRecord,
    SourceHealthRecord,
    SourcePortfolioAuditRecord,
    SourcePortfolioRecord,
    SourceQualityBaselineRecord,
    SourceRecord,
    SourceValueEventRecord,
    SuppressionRecord,
    ThreatIndicatorRecord,
    ThreatIndicatorRelationRecord,
    ThreatIndicatorSnapshotRecord,
    VendorAdvisoryRangeRecord,
    VendorAdvisoryRevisionRecord,
    VendorProductRecord,
    VulnerabilityAffectedRangeRecord,
    VulnerabilityAliasRecord,
    VulnerabilityCweRecord,
    VulnerabilityExploitationRecord,
    VulnerabilityRecord,
    VulnerabilityReferenceRecord,
    VulnerabilityScoreRecord,
    VulnerabilitySourceSnapshotRecord,
)


def get_metadata() -> MetaData:
    """Return metadata after importing all module-owned persistence records."""

    return Base.metadata
