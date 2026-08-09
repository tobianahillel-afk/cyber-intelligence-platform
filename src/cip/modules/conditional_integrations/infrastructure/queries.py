from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from cip.modules.conditional_integrations.infrastructure.models import (
    ConditionalExecutionDecisionRecord,
    ConditionalProviderApprovalRecord,
    ConditionalProviderApprovalRevisionRecord,
    ConditionalProviderControlDecisionRecord,
    ConditionalProviderRuntimeControlRecord,
)


class ConditionalProviderNotFoundError(LookupError):
    pass


def list_approvals(
    session: Session,
    *,
    limit: int,
    offset: int,
) -> tuple[tuple[ConditionalProviderApprovalRecord, ...], int]:
    _validate_page(limit, offset)
    total = session.scalar(
        select(func.count()).select_from(ConditionalProviderApprovalRecord)
    ) or 0
    records = tuple(
        session.scalars(
            select(ConditionalProviderApprovalRecord)
            .order_by(
                ConditionalProviderApprovalRecord.updated_at.desc(),
                ConditionalProviderApprovalRecord.source_id,
            )
            .limit(limit)
            .offset(offset)
        )
    )
    return records, int(total)


def get_approval(
    session: Session,
    source_id: str,
) -> ConditionalProviderApprovalRecord:
    record = session.scalar(
        select(ConditionalProviderApprovalRecord).where(
            ConditionalProviderApprovalRecord.source_id == source_id
        )
    )
    if record is None:
        raise ConditionalProviderNotFoundError(source_id)
    return record


def get_runtime_control(
    session: Session,
    source_id: str,
) -> ConditionalProviderRuntimeControlRecord | None:
    return session.scalar(
        select(ConditionalProviderRuntimeControlRecord).where(
            ConditionalProviderRuntimeControlRecord.source_id == source_id
        )
    )


def list_revisions(
    session: Session,
    approval_id: UUID,
) -> tuple[ConditionalProviderApprovalRevisionRecord, ...]:
    return tuple(
        session.scalars(
            select(ConditionalProviderApprovalRevisionRecord)
            .where(ConditionalProviderApprovalRevisionRecord.approval_id == approval_id)
            .order_by(ConditionalProviderApprovalRevisionRecord.created_at.desc())
        )
    )


def list_control_decisions(
    session: Session,
    control_id: UUID,
) -> tuple[ConditionalProviderControlDecisionRecord, ...]:
    return tuple(
        session.scalars(
            select(ConditionalProviderControlDecisionRecord)
            .where(ConditionalProviderControlDecisionRecord.control_id == control_id)
            .order_by(ConditionalProviderControlDecisionRecord.decided_at.desc())
        )
    )


def list_execution_decisions(
    session: Session,
    approval_id: UUID,
    *,
    limit: int = 100,
) -> tuple[ConditionalExecutionDecisionRecord, ...]:
    return tuple(
        session.scalars(
            select(ConditionalExecutionDecisionRecord)
            .where(ConditionalExecutionDecisionRecord.approval_id == approval_id)
            .order_by(ConditionalExecutionDecisionRecord.evaluated_at.desc())
            .limit(limit)
        )
    )


def _validate_page(limit: int, offset: int) -> None:
    if not 1 <= limit <= 200:
        raise ValueError("limit must be between 1 and 200")
    if offset < 0:
        raise ValueError("offset cannot be negative")
