from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.public_footprint.domain.artifacts import (
    BrowserArtifactKind,
    BrowserArtifactState,
    BrowserEvidenceArtifact,
    BrowserScreenshotMode,
)
from cip.modules.public_footprint.infrastructure.artifact_models import (
    BrowserEvidenceArtifactRecord,
)
from cip.shared.kernel.time import require_aware_utc


def persist_browser_artifact(
    session: Session,
    artifact: BrowserEvidenceArtifact,
    *,
    now: datetime,
) -> None:
    created_at = require_aware_utc(now, field_name="now")
    existing = session.scalar(
        select(BrowserEvidenceArtifactRecord).where(
            BrowserEvidenceArtifactRecord.artifact_key == artifact.identity_key
        )
    )
    if existing is not None:
        _validate_existing(existing, artifact)
        return
    session.add(_record_from_artifact(artifact, created_at=created_at))
    session.flush()


def load_browser_artifacts_for_plan(
    session: Session,
    plan_id: UUID,
    plan_version: int,
) -> tuple[BrowserEvidenceArtifact, ...]:
    records = session.scalars(
        select(BrowserEvidenceArtifactRecord)
        .where(
            BrowserEvidenceArtifactRecord.plan_id == plan_id,
            BrowserEvidenceArtifactRecord.plan_version == plan_version,
        )
        .order_by(BrowserEvidenceArtifactRecord.captured_at, BrowserEvidenceArtifactRecord.step_id)
    ).all()
    return tuple(_artifact_from_record(record) for record in records)


def _record_from_artifact(
    artifact: BrowserEvidenceArtifact,
    *,
    created_at: datetime,
) -> BrowserEvidenceArtifactRecord:
    return BrowserEvidenceArtifactRecord(
        id=artifact.id,
        artifact_key=artifact.identity_key,
        source_id=artifact.source_id,
        provider_id=artifact.provider_id,
        target_id=artifact.target_id,
        job_id=artifact.job_id,
        plan_id=artifact.plan_id,
        plan_version=artifact.plan_version,
        step_id=artifact.step_id,
        kind=artifact.kind.value,
        state=artifact.state.value,
        page_url=artifact.page_url,
        source_url=artifact.source_url,
        captured_at=artifact.captured_at,
        content_hash_sha256=artifact.content_hash_sha256,
        byte_size=artifact.byte_size,
        media_type=artifact.media_type,
        source_locator=artifact.source_locator,
        raw_retention_allowed=artifact.raw_retention_allowed,
        raw_retained=artifact.raw_retained,
        storage_uri=artifact.storage_uri,
        retention_until=artifact.retention_until,
        screenshot_mode=(
            artifact.screenshot_mode.value if artifact.screenshot_mode is not None else None
        ),
        viewport_width=artifact.viewport_width,
        viewport_height=artifact.viewport_height,
        element_selector=artifact.element_selector,
        original_filename=artifact.original_filename,
        extracted_text_hash_sha256=artifact.extracted_text_hash_sha256,
        excerpt=artifact.excerpt,
        rejection_reason=artifact.rejection_reason,
        created_at=created_at,
    )


def _artifact_from_record(record: BrowserEvidenceArtifactRecord) -> BrowserEvidenceArtifact:
    return BrowserEvidenceArtifact(
        id=record.id,
        source_id=record.source_id,
        provider_id=record.provider_id,
        target_id=record.target_id,
        job_id=record.job_id,
        plan_id=record.plan_id,
        plan_version=record.plan_version,
        step_id=record.step_id,
        kind=BrowserArtifactKind(record.kind),
        state=BrowserArtifactState(record.state),
        page_url=record.page_url,
        source_url=record.source_url,
        captured_at=_coerce_utc(record.captured_at),
        content_hash_sha256=record.content_hash_sha256,
        byte_size=record.byte_size,
        media_type=record.media_type,
        source_locator=record.source_locator,
        raw_retention_allowed=record.raw_retention_allowed,
        raw_retained=record.raw_retained,
        storage_uri=record.storage_uri,
        retention_until=(
            _coerce_utc(record.retention_until) if record.retention_until is not None else None
        ),
        screenshot_mode=(
            BrowserScreenshotMode(record.screenshot_mode)
            if record.screenshot_mode is not None
            else None
        ),
        viewport_width=record.viewport_width,
        viewport_height=record.viewport_height,
        element_selector=record.element_selector,
        original_filename=record.original_filename,
        extracted_text_hash_sha256=record.extracted_text_hash_sha256,
        excerpt=record.excerpt,
        rejection_reason=record.rejection_reason,
    )


def _validate_existing(
    record: BrowserEvidenceArtifactRecord,
    artifact: BrowserEvidenceArtifact,
) -> None:
    actual = (
        record.source_id,
        record.provider_id,
        record.target_id,
        record.job_id,
        record.plan_id,
        record.plan_version,
        record.step_id,
        record.kind,
        record.state,
        record.page_url,
        record.source_url,
        record.content_hash_sha256,
        record.byte_size,
        record.media_type,
        record.raw_retained,
        record.storage_uri,
        record.rejection_reason,
    )
    expected = (
        artifact.source_id,
        artifact.provider_id,
        artifact.target_id,
        artifact.job_id,
        artifact.plan_id,
        artifact.plan_version,
        artifact.step_id,
        artifact.kind.value,
        artifact.state.value,
        artifact.page_url,
        artifact.source_url,
        artifact.content_hash_sha256,
        artifact.byte_size,
        artifact.media_type,
        artifact.raw_retained,
        artifact.storage_uri,
        artifact.rejection_reason,
    )
    if actual != expected:
        raise ValueError("browser evidence artifact identity collision")


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
