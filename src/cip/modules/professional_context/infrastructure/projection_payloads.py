from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

from cip.modules.professional_context.domain import (
    ProfessionalContactEvidence,
    ProfessionalPersonReference,
    ProfessionalProcessingContext,
    ProfessionalRoleClaim,
    PublicCommunityContext,
    ReportingLineClaim,
)


def person_snapshot_digest(item: ProfessionalPersonReference) -> str:
    return _digest(
        {
            "person_key": item.person_key,
            "display_name": item.display_name,
            "source_id": item.source_id,
            "source_kind": item.source_kind,
            "source_record_key": item.source_record_key,
            "source_url": item.source_url,
            "observed_at": item.observed_at.isoformat(),
            "confidence": item.confidence,
            "review_state": item.review_state.value,
            "active": item.active,
            "suppressed": item.suppressed,
            "deleted": item.deleted,
            **_processing_payload(item.processing),
        }
    )


def role_snapshot_digest(item: ProfessionalRoleClaim) -> str:
    return _digest(
        {
            "claim_key": item.claim_key,
            "person_key": item.person_key,
            "source_id": item.source_id,
            "source_record_key": item.source_record_key,
            "source_url": item.source_url,
            "role_title": item.role_title,
            "team_name": item.team_name,
            "organization_id": str(item.organization_id) if item.organization_id else None,
            "claimed_organization_name": item.claimed_organization_name,
            "organization_link_status": item.organization_link_status.value,
            "claim_type": item.claim_type.value,
            "review_state": item.review_state.value,
            "observed_at": item.observed_at.isoformat(),
            "valid_from": item.valid_from.isoformat() if item.valid_from else None,
            "valid_until": item.valid_until.isoformat() if item.valid_until else None,
            "expires_at": item.expires_at.isoformat() if item.expires_at else None,
            "confidence": item.confidence,
            "active": item.active,
            "historical_only": item.historical_only,
            "suppressed": item.suppressed,
            "deleted": item.deleted,
            "supersedes_record_key": item.supersedes_record_key,
            **_processing_payload(item.processing),
        }
    )


def reporting_snapshot_digest(item: ReportingLineClaim) -> str:
    return _digest(
        {
            "claim_key": item.claim_key,
            "subject_person_key": item.subject_person_key,
            "manager_person_key": item.manager_person_key,
            "organization_id": str(item.organization_id) if item.organization_id else None,
            "source_id": item.source_id,
            "source_record_key": item.source_record_key,
            "source_url": item.source_url,
            "claim_type": item.claim_type.value,
            "review_state": item.review_state.value,
            "observed_at": item.observed_at.isoformat(),
            "valid_from": item.valid_from.isoformat() if item.valid_from else None,
            "valid_until": item.valid_until.isoformat() if item.valid_until else None,
            "confidence": item.confidence,
            "active": item.active,
            "suppressed": item.suppressed,
            "deleted": item.deleted,
            "supersedes_record_key": item.supersedes_record_key,
            **_processing_payload(item.processing),
        }
    )


def contact_snapshot_digest(item: ProfessionalContactEvidence) -> str:
    return _digest(
        {
            "contact_key": item.contact_key,
            "channel_type": item.channel_type.value,
            "evidence_scope": item.evidence_scope.value,
            "value": item.value,
            "organization_id": str(item.organization_id) if item.organization_id else None,
            "person_key": item.person_key,
            "source_id": item.source_id,
            "source_record_key": item.source_record_key,
            "source_url": item.source_url,
            "claim_type": item.claim_type.value,
            "review_state": item.review_state.value,
            "observed_at": item.observed_at.isoformat(),
            "confidence": item.confidence,
            "active": item.active,
            "suppressed": item.suppressed,
            "deleted": item.deleted,
            "supersedes_record_key": item.supersedes_record_key,
            **_processing_payload(item.processing),
        }
    )


def community_snapshot_digest(item: PublicCommunityContext) -> str:
    return _digest(
        {
            "context_key": item.context_key,
            "community_name": item.community_name,
            "context_type": item.context_type,
            "context_value": item.context_value,
            "acquisition_mode": item.acquisition_mode.value,
            "authorization_reference": item.authorization_reference,
            "organization_id": str(item.organization_id) if item.organization_id else None,
            "person_key": item.person_key,
            "source_id": item.source_id,
            "source_record_key": item.source_record_key,
            "source_url": item.source_url,
            "claim_type": item.claim_type.value,
            "review_state": item.review_state.value,
            "observed_at": item.observed_at.isoformat(),
            "confidence": item.confidence,
            "active": item.active,
            "suppressed": item.suppressed,
            "deleted": item.deleted,
            "metadata_only": item.metadata_only,
            "supersedes_record_key": item.supersedes_record_key,
            **_processing_payload(item.processing),
        }
    )


def _processing_payload(processing: ProfessionalProcessingContext) -> dict[str, object]:
    return {
        "lawful_basis": processing.lawful_basis.value,
        "lawful_basis_reference": processing.lawful_basis_reference,
        "processing_purpose": processing.purpose,
        "processing_reviewed_at": processing.reviewed_at.isoformat(),
        "retention_until": processing.retention_until.isoformat(),
    }


def _digest(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()
