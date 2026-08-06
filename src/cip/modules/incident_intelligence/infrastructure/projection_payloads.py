from __future__ import annotations

import json
from hashlib import sha256

from cip.modules.incident_intelligence.domain.models import IncidentClaimSnapshot


def incident_claim_digest(claim: IncidentClaimSnapshot) -> str:
    payload = {
        "source_id": claim.source_id,
        "source_kind": claim.source_kind.value,
        "source_record_key": claim.source_record_key,
        "source_url": claim.source_url,
        "incident_key": claim.incident_key,
        "claim_type": claim.claim_type.value,
        "incident_type": claim.incident_type.value,
        "title": claim.title,
        "summary": claim.summary,
        "claimed_organization_name": claim.claimed_organization_name,
        "organization_id": str(claim.organization_id) if claim.organization_id else None,
        "organization_link_status": claim.organization_link_status.value,
        "published_at": claim.published_at.isoformat(),
        "modified_at": claim.modified_at.isoformat(),
        "occurrence_start_at": _timestamp(claim.occurrence_start_at),
        "occurrence_end_at": _timestamp(claim.occurrence_end_at),
        "discovered_at": _timestamp(claim.discovered_at),
        "confirmed_at": _timestamp(claim.confirmed_at),
        "independence_key": claim.independence_key,
        "confidence": claim.confidence,
        "active": claim.active,
        "historical_only": claim.historical_only,
        "metadata_only": claim.metadata_only,
        "supersedes_record_key": claim.supersedes_record_key,
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return sha256(encoded).hexdigest()


def _timestamp(value: object) -> str | None:
    return value.isoformat() if hasattr(value, "isoformat") else None
