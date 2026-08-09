from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

from cip.modules.corporate_graph.domain.models import GraphEdgeSnapshot, GraphNodeSnapshot


def graph_node_digest(snapshot: GraphNodeSnapshot) -> str:
    payload = {
        "node_key": snapshot.node_key,
        "node_type": snapshot.node_type.value,
        "display_name": snapshot.display_name,
        "source_module": snapshot.source_module,
        "source_entity_type": snapshot.source_entity_type,
        "source_record_key": snapshot.source_record_key,
        "source_entity_id": str(snapshot.source_entity_id) if snapshot.source_entity_id else None,
        "organization_id": str(snapshot.organization_id) if snapshot.organization_id else None,
        "source_url": snapshot.source_url,
        "observed_at": snapshot.observed_at.isoformat(),
        "valid_from": snapshot.valid_from.isoformat() if snapshot.valid_from else None,
        "valid_until": snapshot.valid_until.isoformat() if snapshot.valid_until else None,
        "confidence": snapshot.confidence,
        "active": snapshot.active,
        "suppressed": snapshot.suppressed,
        "metadata_only": snapshot.metadata_only,
    }
    return _digest(payload)


def graph_edge_digest(snapshot: GraphEdgeSnapshot) -> str:
    payload = {
        "edge_key": snapshot.edge_key,
        "source_node_key": snapshot.source_node_key,
        "target_node_key": snapshot.target_node_key,
        "edge_type": snapshot.edge_type.value,
        "source_module": snapshot.source_module,
        "source_record_key": snapshot.source_record_key,
        "source_evidence_class": snapshot.source_evidence_class,
        "claim_type": snapshot.claim_type.value,
        "review_state": snapshot.review_state.value,
        "source_url": snapshot.source_url,
        "observed_at": snapshot.observed_at.isoformat(),
        "valid_from": snapshot.valid_from.isoformat() if snapshot.valid_from else None,
        "valid_until": snapshot.valid_until.isoformat() if snapshot.valid_until else None,
        "expires_at": snapshot.expires_at.isoformat() if snapshot.expires_at else None,
        "confidence": snapshot.confidence,
        "active": snapshot.active,
        "suppressed": snapshot.suppressed,
        "supersedes_record_key": snapshot.supersedes_record_key,
    }
    return _digest(payload)


def _digest(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
