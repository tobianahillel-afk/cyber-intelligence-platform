from __future__ import annotations

from datetime import datetime
from hashlib import sha256

from cip.adapters.sources.sherlock_local.registry import SherlockTarget
from cip.adapters.sources.sherlock_local.runner import SherlockFinding
from cip.modules.professional_context.domain import (
    CommunityAcquisitionMode,
    ProfessionalProcessingContext,
    ProfessionalReviewState,
    PublicCommunityContext,
)

_SOURCE_ID = "sherlock-local"
_CONTEXT_TYPE = "public_professional_profile_presence"


def map_sherlock_finding(
    target: SherlockTarget,
    finding: SherlockFinding,
    *,
    observed_at: datetime,
) -> PublicCommunityContext:
    processing = ProfessionalProcessingContext(
        lawful_basis=target.lawful_basis,
        lawful_basis_reference=target.authorization_reference,
        purpose=target.purpose,
        reviewed_at=target.reviewed_at,
        retention_until=target.retention_until,
    )
    source_record_key = (
        f"{target.target_id}:{finding.site_name.casefold()}:{finding.username.casefold()}"
    )
    context_key = _context_key(source_record_key, finding.profile_url)
    return PublicCommunityContext(
        context_key=context_key,
        community_name=finding.site_name,
        context_type=_CONTEXT_TYPE,
        context_value=finding.profile_url,
        acquisition_mode=CommunityAcquisitionMode.GOVERNED_LOCAL_TOOL,
        authorization_reference=target.authorization_reference,
        source_id=_SOURCE_ID,
        source_record_key=source_record_key,
        observed_at=observed_at,
        confidence=0.5,
        processing=processing,
        person_key=target.person_key,
        organization_id=target.organization_id,
        source_url=finding.profile_url,
        review_state=ProfessionalReviewState.REVIEW_REQUIRED,
        metadata_only=True,
    )


def _context_key(source_record_key: str, profile_url: str) -> str:
    digest = sha256(f"{_SOURCE_ID}\x1f{source_record_key}\x1f{profile_url}".encode()).hexdigest()
    return f"professional-community:{digest}"
