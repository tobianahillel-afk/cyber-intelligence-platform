from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.public_footprint.domain.structured_state import PublicStructuredState
from cip.modules.public_footprint.infrastructure.models import PublicStructuredStateRecord


def persist_structured_states(
    session: Session,
    states: tuple[PublicStructuredState, ...],
    *,
    resource_version_id: UUID,
    now: datetime,
) -> None:
    for state in states:
        state_key = state.identity_key_for_version(resource_version_id)
        record = session.scalar(
            select(PublicStructuredStateRecord).where(
                PublicStructuredStateRecord.state_key == state_key
            )
        )
        if record is not None:
            _validate_existing(record, state, resource_version_id=resource_version_id)
            continue
        session.add(
            PublicStructuredStateRecord(
                id=state.id,
                state_key=state_key,
                organization_id=state.organization_id,
                resource_version_id=resource_version_id,
                kind=state.kind.value,
                page_url=state.page_url,
                source_locator=state.source_locator,
                source_url=state.source_url,
                http_status=state.http_status,
                media_type=state.media_type,
                extractor_id=state.extractor_id,
                payload_hash_sha256=state.payload_hash_sha256,
                payload_json=state.payload_json,
                created_at=now,
            )
        )
        session.flush()


def _validate_existing(
    record: PublicStructuredStateRecord,
    state: PublicStructuredState,
    *,
    resource_version_id: UUID,
) -> None:
    expected = (
        state.organization_id,
        resource_version_id,
        state.kind.value,
        state.page_url,
        state.source_locator,
        state.source_url,
        state.http_status,
        state.media_type,
        state.extractor_id,
        state.payload_hash_sha256,
        state.payload_json,
    )
    actual = (
        record.organization_id,
        record.resource_version_id,
        record.kind,
        record.page_url,
        record.source_locator,
        record.source_url,
        record.http_status,
        record.media_type,
        record.extractor_id,
        record.payload_hash_sha256,
        record.payload_json,
    )
    if actual != expected:
        raise ValueError("public structured state identity collision")
