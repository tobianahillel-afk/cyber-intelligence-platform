from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse

from cip.modules.research_orchestration.domain.enums import (
    ResearchBlockReason,
    ResearchPlanState,
    ResearchRiskLevel,
    ResearchStepMode,
    ResearchStepState,
)
from cip.modules.research_orchestration.domain.models import (
    ResearchPlan,
    ResearchRuntimeState,
    ResearchStep,
    ResearchStepDecision,
    ResearchUsage,
)
from cip.shared.kernel.time import require_aware_utc

_RISK_ORDER = {
    ResearchRiskLevel.LOW: 0,
    ResearchRiskLevel.MEDIUM: 1,
    ResearchRiskLevel.HIGH: 2,
    ResearchRiskLevel.PROHIBITED: 3,
}
_ALLOWED_PLAN_STATES = {ResearchPlanState.APPROVED, ResearchPlanState.IN_PROGRESS}
_URL_MODES = {ResearchStepMode.MANUAL_LINK, ResearchStepMode.AUTOMATED_ADAPTER}


def evaluate_research_step(
    plan: ResearchPlan,
    step: ResearchStep,
    usage: ResearchUsage,
    runtime: ResearchRuntimeState,
    *,
    now: datetime,
) -> ResearchStepDecision:
    current = require_aware_utc(now, field_name="now")
    reasons: list[ResearchBlockReason] = []
    _plan_reasons(reasons, plan, step, current)
    _budget_reasons(reasons, plan, step, usage)
    _target_reasons(reasons, plan, step)
    _runtime_reasons(reasons, step, runtime)
    unique = tuple(dict.fromkeys(reasons))
    if unique:
        return ResearchStepDecision(False, ResearchStepState.BLOCKED, unique)
    next_state = (
        ResearchStepState.MANUAL_ACTION_REQUIRED
        if step.mode is ResearchStepMode.MANUAL_LINK
        else ResearchStepState.READY
    )
    return ResearchStepDecision(True, next_state, (ResearchBlockReason.ALLOWED,))


def _plan_reasons(
    reasons: list[ResearchBlockReason],
    plan: ResearchPlan,
    step: ResearchStep,
    now: datetime,
) -> None:
    if plan.state not in _ALLOWED_PLAN_STATES:
        reasons.append(ResearchBlockReason.PLAN_NOT_APPROVED)
    if plan.expires_at is not None and plan.expires_at <= now:
        reasons.append(ResearchBlockReason.PLAN_EXPIRED)
    if step.step_key not in plan.approved_step_keys:
        reasons.append(ResearchBlockReason.STEP_NOT_APPROVED)
    if step.source_id not in plan.allowed_source_ids:
        reasons.append(ResearchBlockReason.SOURCE_NOT_ALLOWED)
    if step.tool_id not in plan.allowed_tool_ids:
        reasons.append(ResearchBlockReason.TOOL_NOT_ALLOWED)
    if step.purpose != plan.purpose:
        reasons.append(ResearchBlockReason.PURPOSE_MISMATCH)
    if step.data_category is not plan.data_category:
        reasons.append(ResearchBlockReason.CATEGORY_MISMATCH)
    if _RISK_ORDER[step.risk_level] > _RISK_ORDER[plan.max_risk_level]:
        reasons.append(ResearchBlockReason.RISK_NOT_ALLOWED)


def _budget_reasons(
    reasons: list[ResearchBlockReason],
    plan: ResearchPlan,
    step: ResearchStep,
    usage: ResearchUsage,
) -> None:
    if usage.completed_steps >= plan.budget.max_steps:
        reasons.append(ResearchBlockReason.STEP_BUDGET_EXHAUSTED)
    if (
        step.mode is ResearchStepMode.AUTOMATED_ADAPTER
        and usage.automated_steps >= plan.budget.max_automated_steps
    ):
        reasons.append(ResearchBlockReason.AUTOMATION_BUDGET_EXHAUSTED)
    if step.estimated_cost > plan.budget.max_step_cost:
        reasons.append(ResearchBlockReason.STEP_COST_EXCEEDS_LIMIT)
    if usage.cost_used + step.estimated_cost > plan.budget.max_total_cost:
        reasons.append(ResearchBlockReason.TOTAL_COST_BUDGET_EXHAUSTED)


def _target_reasons(
    reasons: list[ResearchBlockReason],
    plan: ResearchPlan,
    step: ResearchStep,
) -> None:
    if step.mode not in _URL_MODES:
        return
    if step.target_url is None:
        reasons.append(ResearchBlockReason.TARGET_URL_REQUIRED)
        return
    parsed = urlparse(step.target_url)
    if parsed.scheme.lower() != "https":
        reasons.append(ResearchBlockReason.TARGET_SCHEME_NOT_ALLOWED)
    host = (parsed.hostname or "").lower().rstrip(".")
    if host not in plan.allowed_hosts:
        reasons.append(ResearchBlockReason.TARGET_HOST_NOT_ALLOWED)
    path = parsed.path or "/"
    if plan.allowed_path_prefixes and not any(
        path.startswith(prefix) for prefix in plan.allowed_path_prefixes
    ):
        reasons.append(ResearchBlockReason.TARGET_PATH_NOT_ALLOWED)


def _runtime_reasons(
    reasons: list[ResearchBlockReason],
    step: ResearchStep,
    runtime: ResearchRuntimeState,
) -> None:
    if step.mode is ResearchStepMode.AUTOMATED_ADAPTER:
        if not runtime.source_authorized:
            reasons.append(ResearchBlockReason.SOURCE_AUTHORIZATION_REQUIRED)
        if not runtime.source_executable:
            reasons.append(ResearchBlockReason.SOURCE_NOT_EXECUTABLE)
        if not runtime.adapter_capability_present:
            reasons.append(ResearchBlockReason.ADAPTER_CAPABILITY_MISSING)
        if runtime.quota_remaining == 0:
            reasons.append(ResearchBlockReason.QUOTA_EXHAUSTED)
    elif step.mode is ResearchStepMode.MANUAL_LINK:
        if not runtime.manual_link_allowed:
            reasons.append(ResearchBlockReason.MANUAL_LINK_REQUIRED)
    elif step.mode is ResearchStepMode.APPROVED_INGESTION:
        if not runtime.ingestion_path_approved:
            reasons.append(ResearchBlockReason.INGESTION_PATH_NOT_APPROVED)
