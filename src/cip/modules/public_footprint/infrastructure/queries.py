from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from cip.modules.organizations.infrastructure.models import OrganizationRecord
from cip.modules.public_footprint.application.view_models import (
    PublicClaimItem,
    PublicResourceDetail,
    PublicResourceListItem,
    PublicResourcePage,
    PublicResourceVersionItem,
)
from cip.modules.public_footprint.domain.models import (
    PublicClaimType,
    PublicResourceKind,
    ResourceAccessState,
    ResourceRetrievalState,
)
from cip.modules.public_footprint.infrastructure.errors import (
    PublicResourceNotFoundError,
)
from cip.modules.public_footprint.infrastructure.models import (
    PublicClaimRecord,
    PublicResourceRecord,
    PublicResourceVersionRecord,
)
from cip.shared.kernel.time import require_aware_utc


def list_public_resources(
    session: Session,
    *,
    now: datetime,
    organization_id: UUID | None = None,
    source_id: str | None = None,
    kind: PublicResourceKind | None = None,
    access_state: ResourceAccessState | None = None,
    retrieval_state: ResourceRetrievalState | None = None,
    claim_type: PublicClaimType | None = None,
    query: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> PublicResourcePage:
    generated_at = require_aware_utc(now, field_name="now")
    _validate_list_options(limit=limit, offset=offset)
    filters: list[ColumnElement[bool]] = []
    if organization_id is not None:
        filters.append(PublicResourceRecord.organization_id == organization_id)
    if source_id is not None:
        normalized_source = source_id.strip()
        if not normalized_source:
            raise ValueError("source_id cannot be blank")
        filters.append(PublicResourceRecord.source_id == normalized_source)
    if kind is not None:
        filters.append(PublicResourceRecord.kind == kind.value)
    if access_state is not None:
        filters.append(PublicResourceRecord.access_state == access_state.value)
    if retrieval_state is not None:
        filters.append(PublicResourceRecord.retrieval_state == retrieval_state.value)
    if claim_type is not None:
        filters.append(_claim_exists(claim_type=claim_type))
    normalized_query = _optional_query(query)
    if normalized_query is not None:
        pattern = f"%{normalized_query}%"
        filters.append(
            or_(
                PublicResourceRecord.canonical_url.ilike(pattern),
                PublicResourceRecord.source_record_key.ilike(pattern),
                PublicResourceRecord.title.ilike(pattern),
                _claim_exists(query_pattern=pattern),
            )
        )

    total = int(
        session.scalar(select(func.count()).select_from(PublicResourceRecord).where(*filters))
        or 0
    )
    records = tuple(
        session.scalars(
            select(PublicResourceRecord)
            .where(*filters)
            .order_by(
                PublicResourceRecord.last_seen_at.desc(),
                PublicResourceRecord.canonical_url.asc(),
            )
            .limit(limit)
            .offset(offset)
        )
    )
    return PublicResourcePage(
        items=tuple(_list_item(session, record) for record in records),
        total=total,
        limit=limit,
        offset=offset,
        generated_at=generated_at,
    )


def get_public_resource_detail(
    session: Session,
    resource_id: UUID,
) -> PublicResourceDetail:
    record = session.get(PublicResourceRecord, resource_id)
    if record is None:
        raise PublicResourceNotFoundError(str(resource_id))
    versions = tuple(
        session.scalars(
            select(PublicResourceVersionRecord)
            .where(PublicResourceVersionRecord.resource_id == resource_id)
            .order_by(
                PublicResourceVersionRecord.fetched_at.desc(),
                PublicResourceVersionRecord.created_at.desc(),
            )
        )
    )
    claims = tuple(
        session.scalars(
            select(PublicClaimRecord)
            .join(
                PublicResourceVersionRecord,
                PublicResourceVersionRecord.id == PublicClaimRecord.resource_version_id,
            )
            .where(PublicResourceVersionRecord.resource_id == resource_id)
            .order_by(
                PublicClaimRecord.updated_at.desc(),
                PublicClaimRecord.claim_type.asc(),
            )
        )
    )
    return PublicResourceDetail(
        resource=_list_item(session, record),
        identity_key=record.identity_key,
        corroboration_group_key=record.corroboration_group_key,
        versions=tuple(_version_item(item) for item in versions),
        claims=tuple(_claim_item(item) for item in claims),
    )


def _claim_exists(
    *,
    claim_type: PublicClaimType | None = None,
    query_pattern: str | None = None,
) -> ColumnElement[bool]:
    conditions: list[ColumnElement[bool]] = [
        PublicResourceVersionRecord.resource_id == PublicResourceRecord.id
    ]
    if claim_type is not None:
        conditions.append(PublicClaimRecord.claim_type == claim_type.value)
    if query_pattern is not None:
        conditions.append(
            or_(
                PublicClaimRecord.statement.ilike(query_pattern),
                PublicClaimRecord.excerpt.ilike(query_pattern),
            )
        )
    return exists(
        select(PublicClaimRecord.id)
        .join(
            PublicResourceVersionRecord,
            PublicResourceVersionRecord.id == PublicClaimRecord.resource_version_id,
        )
        .where(*conditions)
    )


def _list_item(
    session: Session,
    record: PublicResourceRecord,
) -> PublicResourceListItem:
    organization = session.get(OrganizationRecord, record.organization_id)
    if organization is None:
        raise RuntimeError("public resource references a missing organization")
    latest = session.scalar(
        select(PublicResourceVersionRecord)
        .where(PublicResourceVersionRecord.resource_id == record.id)
        .order_by(
            PublicResourceVersionRecord.fetched_at.desc(),
            PublicResourceVersionRecord.created_at.desc(),
        )
        .limit(1)
    )
    version_count = int(
        session.scalar(
            select(func.count())
            .select_from(PublicResourceVersionRecord)
            .where(PublicResourceVersionRecord.resource_id == record.id)
        )
        or 0
    )
    claim_count = int(
        session.scalar(
            select(func.count())
            .select_from(PublicClaimRecord)
            .join(
                PublicResourceVersionRecord,
                PublicResourceVersionRecord.id == PublicClaimRecord.resource_version_id,
            )
            .where(PublicResourceVersionRecord.resource_id == record.id)
        )
        or 0
    )
    return PublicResourceListItem(
        id=record.id,
        organization_id=record.organization_id,
        organization_name=organization.canonical_name,
        source_id=record.source_id,
        source_record_key=record.source_record_key,
        canonical_url=record.canonical_url,
        source_url=record.source_url,
        kind=record.kind,
        discovery_method=record.discovery_method,
        access_state=record.access_state,
        retrieval_state=record.retrieval_state,
        title=record.title,
        first_discovered_at=_database_utc(record.first_discovered_at),
        last_seen_at=_database_utc(record.last_seen_at),
        latest_version_id=latest.id if latest is not None else None,
        latest_fetched_at=(
            _database_utc(latest.fetched_at) if latest is not None else None
        ),
        latest_mime_type=latest.mime_type if latest is not None else None,
        latest_excerpt=latest.excerpt if latest is not None else None,
        version_count=version_count,
        claim_count=claim_count,
        updated_at=_database_utc(record.updated_at),
    )


def _version_item(record: PublicResourceVersionRecord) -> PublicResourceVersionItem:
    return PublicResourceVersionItem(
        id=record.id,
        source_url=record.source_url,
        content_hash_sha256=record.content_hash_sha256,
        fetched_at=_database_utc(record.fetched_at),
        published_at=_optional_database_utc(record.published_at),
        source_updated_at=_optional_database_utc(record.source_updated_at),
        mime_type=record.mime_type,
        byte_size=record.byte_size,
        title=record.title,
        language=record.language,
        extracted_text_hash_sha256=record.extracted_text_hash_sha256,
        excerpt=record.excerpt,
        source_locator=record.source_locator,
        supersedes_version_id=record.supersedes_version_id,
    )


def _claim_item(record: PublicClaimRecord) -> PublicClaimItem:
    return PublicClaimItem(
        id=record.id,
        resource_version_id=record.resource_version_id,
        claim_type=record.claim_type,
        statement=record.statement,
        evidence_basis=record.evidence_basis,
        resolution_status=record.resolution_status,
        confidence=record.confidence,
        corroboration_group_key=record.corroboration_group_key,
        source_locator=record.source_locator,
        excerpt=record.excerpt,
        updated_at=_database_utc(record.updated_at),
    )


def _validate_list_options(*, limit: int, offset: int) -> None:
    if not 1 <= limit <= 200 or offset < 0:
        raise ValueError("invalid pagination")


def _optional_query(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > 200:
        raise ValueError("query cannot exceed 200 characters")
    return normalized


def _database_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _optional_database_utc(value: datetime | None) -> datetime | None:
    return None if value is None else _database_utc(value)
