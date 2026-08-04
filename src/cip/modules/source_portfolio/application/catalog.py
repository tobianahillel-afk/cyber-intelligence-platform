from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from cip.modules.source_portfolio.application.backfill import pause_pending_backfills
from cip.modules.source_portfolio.application.errors import SourcePortfolioStateError
from cip.modules.source_portfolio.application.health import ensure_health
from cip.modules.source_portfolio.application.records import (
    audit,
    capability_record,
    get_portfolio_record,
    to_catalog_entry,
)
from cip.modules.source_portfolio.domain.models import (
    AdapterCapabilityManifest,
    CatalogStatus,
    SourceCatalogEntry,
)
from cip.modules.source_portfolio.infrastructure.models import (
    AdapterCapabilityRecord,
    SourcePortfolioRecord,
)
from cip.shared.kernel.time import require_aware_utc


def sync_source_portfolio(
    session: Session,
    entries: Sequence[SourceCatalogEntry],
    *,
    now: datetime,
) -> tuple[str, ...]:
    synchronized_at = require_aware_utc(now, field_name="now")
    synchronized: list[str] = []
    for entry in entries:
        record = session.get(SourcePortfolioRecord, entry.source_id)
        if record is None:
            record = _new_record(entry, synchronized_at)
            session.add(record)
            audit(session, entry.source_id, "catalog_created", "system", synchronized_at)
        else:
            _refresh_record(record, entry, synchronized_at)
        _sync_capability(session, entry.adapter, synchronized_at)
        ensure_health(session, entry, synchronized_at)
        synchronized.append(entry.source_id)
    session.flush()
    return tuple(synchronized)


def list_source_portfolio(session: Session) -> tuple[SourceCatalogEntry, ...]:
    records = session.scalars(
        select(SourcePortfolioRecord).order_by(SourcePortfolioRecord.source_id)
    ).all()
    return tuple(to_catalog_entry(session, record) for record in records)


def get_source_portfolio(session: Session, source_id: str) -> SourceCatalogEntry:
    return to_catalog_entry(session, get_portfolio_record(session, source_id))


def pause_source(
    session: Session,
    source_id: str,
    *,
    actor: str,
    now: datetime,
) -> SourceCatalogEntry:
    return _change_source_status(session, source_id, CatalogStatus.PAUSED, actor, now)


def resume_source(
    session: Session,
    source_id: str,
    *,
    actor: str,
    now: datetime,
) -> SourceCatalogEntry:
    record = get_portfolio_record(session, source_id)
    if capability_record(session, record.source_id) is None:
        raise SourcePortfolioStateError("catalog candidates cannot be resumed")
    return _change_source_status(
        session,
        source_id,
        CatalogStatus.EXECUTABLE,
        actor,
        now,
    )


def disable_source(
    session: Session,
    source_id: str,
    *,
    actor: str,
    now: datetime,
) -> SourceCatalogEntry:
    return _change_source_status(session, source_id, CatalogStatus.DISABLED, actor, now)


def _new_record(entry: SourceCatalogEntry, now: datetime) -> SourcePortfolioRecord:
    return SourcePortfolioRecord(
        source_id=entry.source_id,
        created_at=now,
        updated_at=now,
        display_name=entry.display_name,
        canonical_url=entry.canonical_url,
        category=entry.category,
        status=entry.status.value,
        freshness_max_age_seconds=entry.freshness_max_age_seconds,
        commercial_use_cases=list(entry.commercial_use_cases),
        authorization_expires_at=entry.authorization_expires_at,
        review_due_at=entry.review_due_at,
        candidate_origin=entry.candidate_origin,
        monthly_cost_limit=entry.monthly_cost_limit,
        extra_metadata=dict(entry.metadata),
    )


def _refresh_record(
    record: SourcePortfolioRecord,
    entry: SourceCatalogEntry,
    now: datetime,
) -> None:
    record.display_name = entry.display_name
    record.canonical_url = entry.canonical_url
    record.category = entry.category
    if record.status not in {CatalogStatus.PAUSED.value, CatalogStatus.DISABLED.value}:
        record.status = entry.status.value
    record.freshness_max_age_seconds = entry.freshness_max_age_seconds
    record.commercial_use_cases = list(entry.commercial_use_cases)
    record.authorization_expires_at = entry.authorization_expires_at
    record.review_due_at = entry.review_due_at
    record.candidate_origin = entry.candidate_origin
    record.monthly_cost_limit = entry.monthly_cost_limit
    record.extra_metadata = dict(entry.metadata)
    record.updated_at = now


def _sync_capability(
    session: Session,
    manifest: AdapterCapabilityManifest | None,
    now: datetime,
) -> None:
    if manifest is None:
        return
    record = session.get(AdapterCapabilityRecord, (manifest.source_id, manifest.adapter_id))
    if record is None:
        record = AdapterCapabilityRecord(
            source_id=manifest.source_id,
            adapter_id=manifest.adapter_id,
            adapter_version=manifest.adapter_version,
            provider_schema_version=manifest.provider_schema_version,
            modes=[],
            canonical_output_types=[],
            supports_corrections=False,
            supports_tombstones=False,
            supports_retractions=False,
            max_page_size=None,
            max_window_days=None,
            cost_per_request=0.0,
            updated_at=now,
        )
        session.add(record)
    record.adapter_version = manifest.adapter_version
    record.provider_schema_version = manifest.provider_schema_version
    record.modes = sorted(mode.value for mode in manifest.modes)
    record.canonical_output_types = list(manifest.canonical_output_types)
    record.supports_corrections = manifest.supports_corrections
    record.supports_tombstones = manifest.supports_tombstones
    record.supports_retractions = manifest.supports_retractions
    record.max_page_size = manifest.max_page_size
    record.max_window_days = manifest.max_window_days
    record.cost_per_request = manifest.cost_per_request
    record.updated_at = now


def _change_source_status(
    session: Session,
    source_id: str,
    target: CatalogStatus,
    actor: str,
    now: datetime,
) -> SourceCatalogEntry:
    record = get_portfolio_record(session, source_id)
    if record.status == CatalogStatus.CANDIDATE.value and target is not CatalogStatus.DISABLED:
        raise SourcePortfolioStateError("catalog candidates cannot execute")
    changed_at = require_aware_utc(now, field_name="now")
    record.status = target.value
    record.updated_at = changed_at
    if target in {CatalogStatus.PAUSED, CatalogStatus.DISABLED}:
        pause_pending_backfills(session, record.source_id, now=changed_at)
    audit(session, record.source_id, f"source_{target.value}", actor, changed_at)
    session.flush()
    return to_catalog_entry(session, record)
