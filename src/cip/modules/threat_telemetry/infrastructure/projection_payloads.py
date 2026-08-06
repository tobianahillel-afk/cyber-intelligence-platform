from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from enum import Enum
from hashlib import sha256
from uuid import UUID

from cip.modules.threat_telemetry.domain.models import IndicatorSnapshot


def indicator_snapshot_digest(snapshot: IndicatorSnapshot) -> str:
    payload = json.dumps(
        asdict(snapshot),
        sort_keys=True,
        separators=(",", ":"),
        default=_json_default,
    )
    return sha256(payload.encode("utf-8")).hexdigest()


def relation_digest(
    snapshot_key: str,
    relation_type: str,
    target_key: str,
) -> str:
    material = f"{snapshot_key}\0{relation_type}\0{target_key}"
    return sha256(material.encode("utf-8")).hexdigest()


def _json_default(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, UUID):
        return str(value)
    raise TypeError(f"cannot serialize {type(value).__name__}")
