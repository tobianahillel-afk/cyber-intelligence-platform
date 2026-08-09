from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import datetime

from cip.modules.conditional_integrations.domain import (
    ConditionalExecutionDecision,
    ConditionalExecutionRequest,
    ConditionalRuntimeDependencies,
    ProviderApprovalDossier,
    ProviderControlDecision,
)


def dossier_revision_key(dossier: ProviderApprovalDossier) -> str:
    return _digest(dossier_payload(dossier))


def dossier_payload(dossier: ProviderApprovalDossier) -> dict[str, object]:
    return {
        "source_id": dossier.source_id,
        "provider_kind": dossier.provider_kind.value,
        "access_method": dossier.access_method.value,
        "state": dossier.state.value,
        "authorization_document_reference": dossier.authorization_document_reference,
        "licence_reference": dossier.licence_reference,
        "terms_reference": dossier.terms_reference,
        "terms_state": dossier.terms_state.value,
        "approved_scopes": sorted(dossier.approved_scopes),
        "approved_fields": sorted(dossier.approved_fields),
        "approved_purposes": sorted(dossier.approved_purposes),
        "approved_data_categories": sorted(
            value.value for value in dossier.approved_data_categories
        ),
        "retention_days": dossier.retention_days,
        "automated_collection_allowed": dossier.automated_collection_allowed,
        "account_reference": dossier.account_reference,
        "reviewed_at": _optional_time(dossier.reviewed_at),
        "review_due_at": _optional_time(dossier.review_due_at),
        "expires_at": _optional_time(dossier.expires_at),
        "revoked_at": _optional_time(dossier.revoked_at),
        "paused_reason": dossier.paused_reason,
    }


def control_decision_key(decision: ProviderControlDecision) -> str:
    return _digest(
        {
            "source_id": decision.source_id,
            "action": decision.action.value,
            "actor": decision.actor,
            "reason": decision.reason,
            "decided_at": decision.decided_at.isoformat(),
        }
    )


def execution_decision_key(
    request: ConditionalExecutionRequest,
    dependencies: ConditionalRuntimeDependencies,
    decision: ConditionalExecutionDecision,
    *,
    evaluated_at: str,
) -> str:
    return _digest(
        {
            "source_id": request.source_id,
            "access_method": request.access_method.value,
            "purpose": request.purpose,
            "data_category": request.data_category.value,
            "requested_scopes": sorted(request.requested_scopes),
            "requested_fields": sorted(request.requested_fields),
            "retention_days": request.retention_days,
            "automated": request.automated,
            "account_reference": request.account_reference,
            "onboarding_state": dependencies.onboarding_state.value,
            "source_policy_allowed": dependencies.source_policy_allowed,
            "adapter_capability_present": dependencies.adapter_capability_present,
            "provider_paused": dependencies.provider_paused,
            "kill_switch_active": dependencies.kill_switch_active,
            "quota_remaining": dependencies.quota_remaining,
            "monthly_cost_used": dependencies.monthly_cost_used,
            "monthly_cost_limit": dependencies.monthly_cost_limit,
            "allowed": decision.allowed,
            "reasons": [reason.value for reason in decision.reasons],
            "evaluated_at": evaluated_at,
        }
    )


def _optional_time(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _digest(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()
