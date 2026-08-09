from __future__ import annotations

import hashlib
import json
from datetime import datetime
from uuid import UUID

from cip.modules.research_orchestration.domain import (
    ResearchPlan,
    ResearchRuntimeState,
    ResearchStep,
    ResearchStepDecision,
    ResearchUsage,
)


def plan_revision_key(plan: ResearchPlan, *, context: str | None = None) -> str:
    payload: dict[str, object] = {
        "plan_id": str(plan.plan_id),
        "question": plan.question,
        "purpose": plan.purpose,
        "data_category": plan.data_category.value,
        "state": plan.state.value,
        "budget": _budget(plan),
        "allowed_source_ids": sorted(plan.allowed_source_ids),
        "allowed_tool_ids": sorted(plan.allowed_tool_ids),
        "approved_step_keys": sorted(plan.approved_step_keys),
        "allowed_hosts": sorted(plan.allowed_hosts),
        "allowed_path_prefixes": list(plan.allowed_path_prefixes),
        "max_risk_level": plan.max_risk_level.value,
        "expires_at": _time(plan.expires_at),
    }
    if context is not None:
        payload["revision_context"] = context
    return _digest(payload)


def plan_decision_key(
    *,
    plan_revision: str,
    decision_type: str,
    actor: str,
    reason: str,
    previous_state: str,
    resulting_state: str,
) -> str:
    return _digest(
        {
            "plan_revision": plan_revision,
            "decision_type": decision_type,
            "actor": actor.strip(),
            "reason": reason.strip(),
            "previous_state": previous_state,
            "resulting_state": resulting_state,
        }
    )


def step_definition_key(plan_id: UUID, step: ResearchStep) -> str:
    return _digest({"plan_id": str(plan_id), **step_payload(step)})


def step_decision_key(
    *,
    plan_revision: str,
    step_definition: str,
    usage: ResearchUsage,
    runtime: ResearchRuntimeState,
    decision: ResearchStepDecision,
    evaluated_at: datetime,
) -> str:
    return _digest(
        {
            "plan_revision": plan_revision,
            "step_definition": step_definition,
            "usage": usage_payload(usage),
            "runtime": runtime_payload(runtime),
            "allowed": decision.allowed,
            "next_state": decision.next_state.value,
            "reasons": [reason.value for reason in decision.reasons],
            "evaluated_at": evaluated_at.isoformat(),
        }
    )


def attempt_key(plan_id: UUID, step_key: str, idempotency_key: str) -> str:
    return _digest(
        {
            "plan_id": str(plan_id),
            "step_key": step_key,
            "idempotency_key": idempotency_key.strip(),
        }
    )


def result_key(
    *,
    plan_id: UUID,
    step_key: str,
    result_type: str,
    evidence_reference: str,
    provenance_reference: str,
) -> str:
    return _digest(
        {
            "plan_id": str(plan_id),
            "step_key": step_key,
            "result_type": result_type.strip(),
            "evidence_reference": evidence_reference.strip(),
            "provenance_reference": provenance_reference.strip(),
        }
    )


def step_payload(step: ResearchStep) -> dict[str, object]:
    return {
        "step_key": step.step_key,
        "sequence": step.sequence,
        "source_id": step.source_id,
        "tool_id": step.tool_id,
        "mode": step.mode.value,
        "purpose": step.purpose,
        "data_category": step.data_category.value,
        "estimated_cost": step.estimated_cost,
        "risk_level": step.risk_level.value,
        "target_url": step.target_url,
        "query_text": step.query_text,
        "ingestion_path_id": step.ingestion_path_id,
    }


def usage_payload(usage: ResearchUsage) -> dict[str, object]:
    return {
        "completed_steps": usage.completed_steps,
        "automated_steps": usage.automated_steps,
        "cost_used": usage.cost_used,
    }


def runtime_payload(runtime: ResearchRuntimeState) -> dict[str, object]:
    return {
        "source_authorized": runtime.source_authorized,
        "source_executable": runtime.source_executable,
        "adapter_capability_present": runtime.adapter_capability_present,
        "manual_link_allowed": runtime.manual_link_allowed,
        "ingestion_path_approved": runtime.ingestion_path_approved,
        "quota_remaining": runtime.quota_remaining,
    }


def _budget(plan: ResearchPlan) -> dict[str, object]:
    return {
        "max_steps": plan.budget.max_steps,
        "max_automated_steps": plan.budget.max_automated_steps,
        "max_total_cost": plan.budget.max_total_cost,
        "max_step_cost": plan.budget.max_step_cost,
    }


def _time(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _digest(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()
