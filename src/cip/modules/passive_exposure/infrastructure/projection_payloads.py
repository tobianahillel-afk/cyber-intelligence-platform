from __future__ import annotations

import hashlib
import json
from uuid import UUID

from cip.modules.passive_exposure.domain.models import (
    PassiveObservationSnapshot,
    TechnologyObservation,
)


def passive_snapshot_digest(snapshot: PassiveObservationSnapshot) -> str:
    payload = {
        "source_id": snapshot.source_id,
        "source_record_key": snapshot.source_record_key,
        "source_url": snapshot.source_url,
        "asset_kind": snapshot.asset.kind.value,
        "asset_value": snapshot.asset.value,
        "observation_kind": snapshot.observation_kind.value,
        "state": snapshot.state.value,
        "observed_at": snapshot.observed_at.isoformat(),
        "published_at": snapshot.published_at.isoformat(),
        "modified_at": snapshot.modified_at.isoformat(),
        "expires_at": snapshot.expires_at.isoformat() if snapshot.expires_at else None,
        "independence_key": snapshot.independence_key,
        "confidence": snapshot.confidence,
        "organization_link": {
            "status": snapshot.organization_link.status.value,
            "method": snapshot.organization_link.method.value,
            "confidence": snapshot.organization_link.confidence,
            "organization_id": str(snapshot.organization_link.organization_id)
            if snapshot.organization_link.organization_id
            else None,
            "reasons": snapshot.organization_link.reasons,
            "attribution_risks": tuple(
                risk.value for risk in snapshot.organization_link.attribution_risks
            ),
        },
        "technology": _technology_payload(snapshot.technology),
        "port": snapshot.port,
        "protocol": snapshot.protocol,
        "active": snapshot.active,
        "historical_only": snapshot.historical_only,
        "metadata_only": snapshot.metadata_only,
        "passive_only": snapshot.passive_only,
        "active_probe_performed": snapshot.active_probe_performed,
        "credentials_used": snapshot.credentials_used,
        "access_control_bypassed": snapshot.access_control_bypassed,
        "exploit_attempted": snapshot.exploit_attempted,
        "direct_validation_performed": snapshot.direct_validation_performed,
        "vulnerability_applicability_assessed": (
            snapshot.vulnerability_applicability_assessed
        ),
        "exposure_verified": snapshot.exposure_verified,
        "supersedes_record_key": snapshot.supersedes_record_key,
    }
    return _digest(payload)


def passive_technology_digest(
    snapshot_key: str,
    technology: TechnologyObservation,
) -> str:
    return _digest(
        {
            "snapshot_key": snapshot_key,
            "technology": _technology_payload(technology),
        }
    )


def encode_text_values(values: tuple[str, ...]) -> str:
    return json.dumps(list(values), ensure_ascii=True, separators=(",", ":"))


def decode_text_values(value: str) -> tuple[str, ...]:
    loaded = json.loads(value)
    if not isinstance(loaded, list) or not all(isinstance(item, str) for item in loaded):
        raise ValueError("persisted text collection is invalid")
    return tuple(loaded)


def encode_uuid_values(values: tuple[UUID, ...]) -> str:
    return encode_text_values(tuple(str(value) for value in values))


def decode_uuid_values(value: str) -> tuple[UUID, ...]:
    return tuple(UUID(item) for item in decode_text_values(value))


def _technology_payload(technology: TechnologyObservation | None) -> dict[str, str | None] | None:
    if technology is None:
        return None
    return {
        "evidence_level": technology.evidence_level.value,
        "product_name": technology.product_name,
        "product_version": technology.product_version,
        "component_name": technology.component_name,
    }


def _digest(payload: object) -> str:
    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
