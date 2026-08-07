from __future__ import annotations

import hashlib
import json

from cip.modules.relationship_intelligence.domain.models import RelationshipEvidenceSnapshot


def relationship_evidence_digest(snapshot: RelationshipEvidenceSnapshot) -> str:
    payload = {
        "source_id": snapshot.source_id,
        "source_kind": snapshot.source_kind.value,
        "source_record_key": snapshot.source_record_key,
        "source_url": snapshot.source_url,
        "relationship_key": snapshot.relationship_key,
        "claim_type": snapshot.claim_type.value,
        "role": snapshot.role.value,
        "evidence_class": snapshot.evidence_class.value,
        "title": snapshot.title,
        "excerpt": snapshot.excerpt,
        "claimed_source_organization_name": snapshot.claimed_source_organization_name,
        "claimed_target_organization_name": snapshot.claimed_target_organization_name,
        "source_organization_id": (
            str(snapshot.source_organization_id) if snapshot.source_organization_id else None
        ),
        "target_organization_id": (
            str(snapshot.target_organization_id) if snapshot.target_organization_id else None
        ),
        "source_link_status": snapshot.source_link_status.value,
        "target_link_status": snapshot.target_link_status.value,
        "published_at": snapshot.published_at.isoformat(),
        "modified_at": snapshot.modified_at.isoformat(),
        "observed_at": snapshot.observed_at.isoformat(),
        "valid_from": snapshot.valid_from.isoformat() if snapshot.valid_from else None,
        "valid_until": snapshot.valid_until.isoformat() if snapshot.valid_until else None,
        "expires_at": snapshot.expires_at.isoformat() if snapshot.expires_at else None,
        "contract_reference": snapshot.contract_reference,
        "product_context": snapshot.product_context,
        "service_context": snapshot.service_context,
        "renewal_at": snapshot.renewal_at.isoformat() if snapshot.renewal_at else None,
        "independence_key": snapshot.independence_key,
        "confidence": snapshot.confidence,
        "active": snapshot.active,
        "historical_only": snapshot.historical_only,
        "metadata_only": snapshot.metadata_only,
        "supersedes_record_key": snapshot.supersedes_record_key,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
