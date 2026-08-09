from __future__ import annotations

from datetime import datetime

from cip.modules.conditional_integrations.domain import (
    ApprovalState,
    ConditionalAccessMethod,
    ConditionalProviderKind,
    ProviderApprovalDossier,
    ProviderRuntimeControl,
    TermsReviewState,
)
from cip.modules.conditional_integrations.infrastructure.models import (
    ConditionalProviderApprovalRecord,
    ConditionalProviderApprovalRevisionRecord,
    ConditionalProviderRuntimeControlRecord,
)
from cip.modules.organizations.infrastructure.persistence_time import coerce_utc
from cip.modules.source_governance.domain.models import DataCategory

ApprovalRow = ConditionalProviderApprovalRecord | ConditionalProviderApprovalRevisionRecord


def dossier_from_record(record: ApprovalRow) -> ProviderApprovalDossier:
    return ProviderApprovalDossier(
        source_id=record.source_id,
        provider_kind=ConditionalProviderKind(record.provider_kind),
        access_method=ConditionalAccessMethod(record.access_method),
        state=ApprovalState(record.state),
        authorization_document_reference=record.authorization_document_reference,
        licence_reference=record.licence_reference,
        terms_reference=record.terms_reference,
        terms_state=TermsReviewState(record.terms_state),
        approved_scopes=frozenset(record.approved_scopes),
        approved_fields=frozenset(record.approved_fields),
        approved_purposes=frozenset(record.approved_purposes),
        approved_data_categories=frozenset(
            DataCategory(value) for value in record.approved_data_categories
        ),
        retention_days=record.retention_days,
        automated_collection_allowed=record.automated_collection_allowed,
        account_reference=record.account_reference,
        reviewed_at=_optional_time(record.reviewed_at),
        review_due_at=_optional_time(record.review_due_at),
        expires_at=_optional_time(record.expires_at),
        revoked_at=_optional_time(record.revoked_at),
        paused_reason=record.paused_reason,
    )


def control_from_record(record: ConditionalProviderRuntimeControlRecord) -> ProviderRuntimeControl:
    return ProviderRuntimeControl(
        source_id=record.source_id,
        paused=record.paused,
        kill_switch_active=record.kill_switch_active,
        paused_reason=record.paused_reason,
        updated_at=coerce_utc(record.updated_at),
    )


def _optional_time(value: datetime | None) -> datetime | None:
    return coerce_utc(value) if value is not None else None
