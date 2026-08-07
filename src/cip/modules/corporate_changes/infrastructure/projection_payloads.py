from __future__ import annotations

import hashlib
import json

from cip.modules.corporate_changes.domain.models import ChangeClaimSnapshot


def change_claim_digest(claim: ChangeClaimSnapshot) -> str:
    payload = {
        "source_id": claim.source_id,
        "source_kind": claim.source_kind.value,
        "source_record_key": claim.source_record_key,
        "article_id": claim.article_id,
        "source_url": claim.source_url,
        "event_key": claim.event_key,
        "claim_type": claim.claim_type.value,
        "event_type": claim.event_type.value,
        "title": claim.title,
        "excerpt": claim.excerpt,
        "claimed_organization_name": claim.claimed_organization_name,
        "organization_id": str(claim.organization_id) if claim.organization_id else None,
        "organization_link_status": claim.organization_link_status.value,
        "published_at": claim.published_at.isoformat(),
        "modified_at": claim.modified_at.isoformat(),
        "event_at": claim.event_at.isoformat() if claim.event_at else None,
        "expires_at": claim.expires_at.isoformat() if claim.expires_at else None,
        "independence_key": claim.independence_key,
        "syndication_group_key": claim.syndication_group_key,
        "confidence": claim.confidence,
        "active": claim.active,
        "historical_only": claim.historical_only,
        "metadata_only": claim.metadata_only,
        "supersedes_record_key": claim.supersedes_record_key,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
