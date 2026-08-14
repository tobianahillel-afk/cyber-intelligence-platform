from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.public_footprint.domain.surfaces import PublicSurfaceReference
from cip.modules.public_footprint.infrastructure.models import PublicSurfaceReferenceRecord


def persist_surface_references(
    session: Session,
    surfaces: tuple[PublicSurfaceReference, ...],
    *,
    now: datetime,
) -> None:
    for surface in surfaces:
        record = session.scalar(
            select(PublicSurfaceReferenceRecord).where(
                PublicSurfaceReferenceRecord.surface_key == surface.identity_key
            )
        )
        if record is not None:
            _validate_existing(record, surface)
            continue
        session.add(
            PublicSurfaceReferenceRecord(
                id=surface.id,
                surface_key=surface.identity_key,
                organization_id=surface.organization_id,
                resource_version_id=surface.resource_version_id,
                kind=surface.kind.value,
                source_locator=surface.source_locator,
                target_url=surface.target_url,
                relation=surface.relation,
                http_method=surface.http_method,
                media_type=surface.media_type,
                name=surface.name,
                value=surface.value,
                created_at=now,
            )
        )
        session.flush()


def _validate_existing(
    record: PublicSurfaceReferenceRecord,
    surface: PublicSurfaceReference,
) -> None:
    expected = (
        surface.organization_id,
        surface.resource_version_id,
        surface.kind.value,
        surface.source_locator,
        surface.target_url,
        surface.relation,
        surface.http_method,
        surface.media_type,
        surface.name,
        surface.value,
    )
    actual = (
        record.organization_id,
        record.resource_version_id,
        record.kind,
        record.source_locator,
        record.target_url,
        record.relation,
        record.http_method,
        record.media_type,
        record.name,
        record.value,
    )
    if actual != expected:
        raise ValueError("public surface identity collision")
