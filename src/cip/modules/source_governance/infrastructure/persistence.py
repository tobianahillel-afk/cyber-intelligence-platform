from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from cip.modules.source_governance.infrastructure.models import SourceRecord
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry


def sync_source_registry(
    session: Session,
    entries: Iterable[SourceRegistryEntry],
) -> int:
    changed = 0
    for entry in entries:
        values = _record_values(entry)
        record = session.get(SourceRecord, entry.policy.id)
        if record is None:
            session.add(SourceRecord(**values))
            changed += 1
            continue
        updated = False
        for name, value in values.items():
            current = getattr(record, name)
            if not _values_equal(current, value):
                setattr(record, name, value)
                updated = True
        changed += int(updated)
    return changed


def _record_values(entry: SourceRegistryEntry) -> dict[str, object]:
    policy = entry.policy
    authorization = entry.authorization
    return {
        "id": policy.id,
        "name": policy.name,
        "base_url": policy.base_url,
        "status": policy.status.value,
        "source_type": policy.source_type.value,
        "owner": policy.owner,
        "terms_url": policy.terms_url,
        "licence": policy.licence,
        "allowed_data_categories": sorted(
            category.value for category in policy.allowed_data_categories
        ),
        "prohibited_data_categories": sorted(
            category.value for category in policy.prohibited_data_categories
        ),
        "rate_limit_per_minute": policy.rate_limit_per_minute,
        "retention_days": policy.retention_days,
        "attribution_required": policy.attribution_required,
        "raw_content_storage": policy.raw_content_storage,
        "human_review_required": policy.human_review_required,
        "authorization_status": authorization.status.value,
        "authorization_document_reference": authorization.document_reference,
        "authorization_reviewed_at": authorization.reviewed_at,
        "authorization_expires_at": authorization.expires_at,
        "approved_hosts": sorted(authorization.approved_hosts),
        "approved_path_prefixes": list(authorization.approved_path_prefixes),
        "approved_purposes": sorted(authorization.approved_purposes),
        "approved_http_methods": sorted(
            method.value for method in authorization.approved_http_methods
        ),
        "automated_collection_allowed": authorization.automated_collection_allowed,
        "raw_storage_allowed": authorization.raw_storage_allowed,
    }


def _values_equal(current: object, desired: object) -> bool:
    if isinstance(current, datetime) and isinstance(desired, datetime):
        return _database_utc(current) == _database_utc(desired)
    return current == desired


def _database_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
