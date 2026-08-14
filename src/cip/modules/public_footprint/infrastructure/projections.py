from __future__ import annotations

from datetime import datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.organizations.infrastructure.persistence_time import coerce_utc
from cip.modules.public_footprint.domain.models import (
    PublicClaim,
    PublicFootprintProjection,
    PublicResource,
    PublicResourceVersion,
)
from cip.modules.public_footprint.infrastructure.models import (
    PublicClaimRecord,
    PublicResourceRecord,
    PublicResourceVersionRecord,
)
from cip.modules.public_footprint.infrastructure.surface_persistence import (
    persist_surface_references,
)
from cip.shared.kernel.time import require_aware_utc


def persist_public_footprint_projections(
    session: Session,
    projections: tuple[PublicFootprintProjection, ...],
    *,
    now: datetime,
) -> None:
    persisted_at = require_aware_utc(now, field_name="now")
    for projection in projections:
        resource = _upsert_resource(session, projection.resource, now=persisted_at)
        version = _insert_version(session, resource.id, projection.version, now=persisted_at)
        for claim in projection.claims:
            _upsert_claim(session, version, claim, now=persisted_at)
        persist_surface_references(
            session,
            projection.surfaces,
            resource_version_id=version.id,
            now=persisted_at,
        )


def _upsert_resource(
    session: Session,
    resource: PublicResource,
    *,
    now: datetime,
) -> PublicResourceRecord:
    record = session.scalar(
        select(PublicResourceRecord).where(
            PublicResourceRecord.identity_key == resource.identity_key
        )
    )
    if record is None:
        record = PublicResourceRecord(
            id=uuid5(NAMESPACE_URL, f"public-resource:{resource.identity_key}"),
            organization_id=resource.organization_id,
            source_id=resource.source_id,
            source_record_key=resource.source_record_key,
            identity_key=resource.identity_key,
            corroboration_group_key=resource.corroboration_group_key,
            canonical_url=resource.canonical_url,
            source_url=resource.source_url,
            kind=resource.kind.value,
            discovery_method=resource.discovery_method.value,
            access_state=resource.access_state.value,
            retrieval_state=resource.retrieval_state.value,
            title=resource.title,
            first_discovered_at=resource.first_discovered_at,
            last_seen_at=resource.last_seen_at,
            created_at=now,
            updated_at=now,
        )
        session.add(record)
        session.flush()
        return record
    _validate_resource_identity(record, resource)
    first_discovered = coerce_utc(record.first_discovered_at)
    if resource.first_discovered_at < first_discovered:
        record.first_discovered_at = resource.first_discovered_at
    if resource.last_seen_at >= coerce_utc(record.last_seen_at):
        record.source_id = resource.source_id
        record.source_record_key = resource.source_record_key
        record.source_url = resource.source_url
        record.discovery_method = resource.discovery_method.value
        record.access_state = resource.access_state.value
        record.retrieval_state = resource.retrieval_state.value
        if resource.title is not None:
            record.title = resource.title
        record.last_seen_at = resource.last_seen_at
        record.updated_at = now
    session.flush()
    return record


def _validate_resource_identity(
    record: PublicResourceRecord,
    resource: PublicResource,
) -> None:
    if record.organization_id != resource.organization_id:
        raise ValueError("public resource organization cannot change")
    if record.canonical_url != resource.canonical_url:
        raise ValueError("public resource canonical URL cannot change")
    if record.kind != resource.kind.value:
        raise ValueError("public resource kind cannot change")
    if record.corroboration_group_key != resource.corroboration_group_key:
        raise ValueError("public resource corroboration group cannot change")


def _insert_version(
    session: Session,
    resource_id: UUID,
    version: PublicResourceVersion,
    *,
    now: datetime,
) -> PublicResourceVersionRecord:
    existing = session.scalar(
        select(PublicResourceVersionRecord).where(
            PublicResourceVersionRecord.version_key == version.version_key
        )
    )
    if existing is not None:
        if existing.resource_id != resource_id:
            raise ValueError("public resource version cannot move to another resource")
        return existing
    supersedes = _validated_predecessor(session, resource_id, version)
    record = PublicResourceVersionRecord(
        id=version.id,
        resource_id=resource_id,
        version_key=version.version_key,
        source_url=version.source_url,
        content_hash_sha256=version.content_hash_sha256,
        fetched_at=version.fetched_at,
        published_at=version.published_at,
        source_updated_at=version.source_updated_at,
        mime_type=version.mime_type,
        byte_size=version.byte_size,
        title=version.title,
        language=version.language,
        extracted_text_hash_sha256=version.extracted_text_hash_sha256,
        excerpt=version.excerpt,
        source_locator=version.source_locator,
        supersedes_version_id=supersedes,
        created_at=now,
    )
    session.add(record)
    session.flush()
    return record


def _validated_predecessor(
    session: Session,
    resource_id: UUID,
    version: PublicResourceVersion,
) -> UUID | None:
    predecessor_id = version.supersedes_version_id
    if predecessor_id is None:
        return None
    if predecessor_id == version.id:
        raise ValueError("public resource version cannot supersede itself")
    predecessor = session.get(PublicResourceVersionRecord, predecessor_id)
    if predecessor is None:
        raise ValueError("superseded public resource version does not exist")
    if predecessor.resource_id != resource_id:
        raise ValueError("public resource version predecessor belongs to another resource")
    if version.fetched_at < coerce_utc(predecessor.fetched_at):
        raise ValueError("public resource version cannot supersede a newer version")
    return predecessor_id


def _upsert_claim(
    session: Session,
    version: PublicResourceVersionRecord,
    claim: PublicClaim,
    *,
    now: datetime,
) -> None:
    record = session.scalar(
        select(PublicClaimRecord).where(PublicClaimRecord.claim_key == claim.identity_key)
    )
    if record is None:
        session.add(
            PublicClaimRecord(
                id=claim.id,
                claim_key=claim.identity_key,
                organization_id=claim.organization_id,
                resource_version_id=version.id,
                claim_type=claim.claim_type.value,
                statement=claim.statement,
                evidence_basis=claim.evidence_basis.value,
                resolution_status=claim.resolution_status.value,
                confidence=claim.confidence,
                corroboration_group_key=claim.corroboration_group_key,
                source_locator=claim.source_locator,
                excerpt=claim.excerpt,
                created_at=now,
                updated_at=now,
            )
        )
        session.flush()
        return
    _validate_claim_identity(record, claim)
    current_version = session.get(PublicResourceVersionRecord, record.resource_version_id)
    if current_version is None or coerce_utc(version.fetched_at) >= coerce_utc(
        current_version.fetched_at
    ):
        record.resource_version_id = version.id
        record.statement = claim.statement
        record.evidence_basis = claim.evidence_basis.value
        record.resolution_status = claim.resolution_status.value
        record.confidence = claim.confidence
        record.source_locator = claim.source_locator
        record.excerpt = claim.excerpt
        record.updated_at = now
        session.flush()


def _validate_claim_identity(record: PublicClaimRecord, claim: PublicClaim) -> None:
    if record.organization_id != claim.organization_id:
        raise ValueError("public claim organization cannot change")
    if record.claim_type != claim.claim_type.value:
        raise ValueError("public claim type cannot change")
    if record.corroboration_group_key != claim.corroboration_group_key:
        raise ValueError("public claim corroboration group cannot change")