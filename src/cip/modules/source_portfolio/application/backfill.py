from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from cip.modules.source_portfolio.application.errors import SourcePortfolioStateError
from cip.modules.source_portfolio.application.health import set_backfill_health
from cip.modules.source_portfolio.application.records import (
    audit,
    bounded_value,
    get_partition,
    get_portfolio_record,
    to_catalog_entry,
)
from cip.modules.source_portfolio.domain.models import (
    BackfillState,
    CatalogStatus,
    CollectionMode,
)
from cip.modules.source_portfolio.infrastructure.models import BackfillPartitionRecord
from cip.shared.kernel.time import require_aware_utc


def request_backfill(
    session: Session,
    source_id: str,
    partitions: Sequence[tuple[str, str]],
    *,
    actor: str,
    now: datetime,
) -> tuple[UUID, ...]:
    entry = to_catalog_entry(session, get_portfolio_record(session, source_id))
    if not entry.executable or entry.adapter is None:
        raise SourcePortfolioStateError(
            "catalog candidates and disabled sources cannot execute"
        )
    if not entry.adapter.supports(CollectionMode.HISTORICAL_BACKFILL):
        raise SourcePortfolioStateError("adapter does not support historical backfill")
    if not partitions:
        raise ValueError("at least one backfill partition is required")
    changed_at = require_aware_utc(now, field_name="now")
    created: list[UUID] = []
    for lower_bound, upper_bound in partitions:
        lower = bounded_value(lower_bound, "lower_bound")
        upper = bounded_value(upper_bound, "upper_bound")
        if lower >= upper:
            raise ValueError("partition lower_bound must be below upper_bound")
        partition_key = f"{lower}..{upper}"
        existing = session.scalar(
            select(BackfillPartitionRecord).where(
                BackfillPartitionRecord.source_id == entry.source_id,
                BackfillPartitionRecord.adapter_id == entry.adapter.adapter_id,
                BackfillPartitionRecord.partition_key == partition_key,
            )
        )
        if existing is not None:
            created.append(existing.id)
            continue
        partition = BackfillPartitionRecord(
            id=uuid4(),
            source_id=entry.source_id,
            adapter_id=entry.adapter.adapter_id,
            partition_key=partition_key,
            lower_bound=lower,
            upper_bound=upper,
            state=BackfillState.PENDING.value,
            cursor={},
            attempts=0,
            records_written=0,
            last_error_code=None,
            created_at=changed_at,
            updated_at=changed_at,
            completed_at=None,
        )
        session.add(partition)
        created.append(partition.id)
    set_backfill_health(session, entry.source_id, BackfillState.PENDING, changed_at)
    audit(
        session,
        entry.source_id,
        "backfill_requested",
        actor,
        changed_at,
        details={"partition_count": len(partitions)},
    )
    session.flush()
    return tuple(created)


def claim_backfill_partition(
    session: Session,
    source_id: str,
    *,
    actor: str,
    now: datetime,
) -> BackfillPartitionRecord | None:
    entry = to_catalog_entry(session, get_portfolio_record(session, source_id))
    if entry.status is not CatalogStatus.EXECUTABLE:
        return None
    partition = session.scalar(
        select(BackfillPartitionRecord)
        .where(
            BackfillPartitionRecord.source_id == entry.source_id,
            BackfillPartitionRecord.state.in_(
                (BackfillState.PENDING.value, BackfillState.FAILED.value)
            ),
        )
        .order_by(BackfillPartitionRecord.created_at)
        .with_for_update(skip_locked=True)
    )
    if partition is None:
        return None
    changed_at = require_aware_utc(now, field_name="now")
    partition.state = BackfillState.RUNNING.value
    partition.attempts += 1
    partition.updated_at = changed_at
    partition.last_error_code = None
    set_backfill_health(session, entry.source_id, BackfillState.RUNNING, changed_at)
    audit(session, entry.source_id, "backfill_partition_claimed", actor, changed_at)
    session.flush()
    return partition


def complete_backfill_partition(
    session: Session,
    partition_id: UUID,
    *,
    cursor: dict[str, object],
    records_written: int,
    actor: str,
    now: datetime,
) -> None:
    partition = get_partition(session, partition_id)
    if partition.state != BackfillState.RUNNING.value:
        raise SourcePortfolioStateError("only running partitions can complete")
    if records_written < 0:
        raise ValueError("records_written cannot be negative")
    changed_at = require_aware_utc(now, field_name="now")
    partition.cursor = dict(cursor)
    partition.records_written += records_written
    partition.state = BackfillState.COMPLETED.value
    partition.updated_at = changed_at
    partition.completed_at = changed_at
    remaining = session.scalar(
        select(BackfillPartitionRecord.id).where(
            BackfillPartitionRecord.source_id == partition.source_id,
            BackfillPartitionRecord.state.in_(
                (
                    BackfillState.PENDING.value,
                    BackfillState.RUNNING.value,
                    BackfillState.FAILED.value,
                )
            ),
        )
    )
    state = BackfillState.COMPLETED if remaining is None else BackfillState.RUNNING
    set_backfill_health(session, partition.source_id, state, changed_at)
    audit(
        session,
        partition.source_id,
        "backfill_partition_completed",
        actor,
        changed_at,
        details={"records_written": records_written},
    )
    session.flush()


def pause_pending_backfills(
    session: Session,
    source_id: str,
    *,
    now: datetime,
) -> None:
    session.execute(
        update(BackfillPartitionRecord)
        .where(
            BackfillPartitionRecord.source_id == source_id,
            BackfillPartitionRecord.state.in_(
                (BackfillState.PENDING.value, BackfillState.RUNNING.value)
            ),
        )
        .values(state=BackfillState.PAUSED.value, updated_at=now)
    )
    set_backfill_health(session, source_id, BackfillState.PAUSED, now)
