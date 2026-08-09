from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from cip.modules.research_orchestration.domain import (
    ResearchBlockReason,
    ResearchBudget,
    ResearchPlan,
    ResearchPlanState,
    ResearchRiskLevel,
    ResearchRuntimeState,
    ResearchStep,
    ResearchStepMode,
    ResearchStepState,
    ResearchUsage,
    evaluate_research_step,
)
from cip.modules.source_governance.domain.models import DataCategory

NOW = datetime(2026, 8, 9, 14, 0, tzinfo=UTC)
PLAN_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
TARGET = "https://search.example.test/results?q=acme"


def test_persisted_search_is_ready_without_network_runtime() -> None:
    step = replace(
        _step(),
        mode=ResearchStepMode.PERSISTED_SEARCH,
        target_url=None,
        estimated_cost=0.0,
    )
    runtime = ResearchRuntimeState(
        source_authorized=False,
        source_executable=False,
        adapter_capability_present=False,
        manual_link_allowed=False,
        ingestion_path_approved=False,
        quota_remaining=0,
    )

    decision = evaluate_research_step(_plan(), step, ResearchUsage(), runtime, now=NOW)

    assert decision.allowed is True
    assert decision.next_state is ResearchStepState.READY


def test_manual_link_is_explicit_manual_action_not_hidden_automation() -> None:
    step = replace(_step(), mode=ResearchStepMode.MANUAL_LINK)
    runtime = replace(_runtime(), source_authorized=False, source_executable=False)

    decision = evaluate_research_step(_plan(), step, ResearchUsage(), runtime, now=NOW)

    assert decision.allowed is True
    assert decision.next_state is ResearchStepState.MANUAL_ACTION_REQUIRED
    assert decision.reasons == (ResearchBlockReason.ALLOWED,)


def test_automated_step_requires_authorization_execution_capability_and_quota() -> None:
    runtime = ResearchRuntimeState(
        source_authorized=False,
        source_executable=False,
        adapter_capability_present=False,
        manual_link_allowed=True,
        ingestion_path_approved=False,
        quota_remaining=0,
    )

    decision = evaluate_research_step(
        _plan(),
        _step(),
        ResearchUsage(),
        runtime,
        now=NOW,
    )

    assert decision.allowed is False
    assert set(decision.reasons) >= {
        ResearchBlockReason.SOURCE_AUTHORIZATION_REQUIRED,
        ResearchBlockReason.SOURCE_NOT_EXECUTABLE,
        ResearchBlockReason.ADAPTER_CAPABILITY_MISSING,
        ResearchBlockReason.QUOTA_EXHAUSTED,
    }


def test_plan_step_tool_source_purpose_category_and_risk_are_exact() -> None:
    plan = replace(_plan(), max_risk_level=ResearchRiskLevel.LOW)
    step = replace(
        _step(),
        step_key="unapproved-step",
        source_id="different-source",
        tool_id="different-tool",
        purpose="different-purpose",
        data_category=DataCategory.PRIVATE_PERSONAL_DATA,
        risk_level=ResearchRiskLevel.HIGH,
    )

    decision = evaluate_research_step(plan, step, ResearchUsage(), _runtime(), now=NOW)

    assert set(decision.reasons) >= {
        ResearchBlockReason.STEP_NOT_APPROVED,
        ResearchBlockReason.SOURCE_NOT_ALLOWED,
        ResearchBlockReason.TOOL_NOT_ALLOWED,
        ResearchBlockReason.PURPOSE_MISMATCH,
        ResearchBlockReason.CATEGORY_MISMATCH,
        ResearchBlockReason.RISK_NOT_ALLOWED,
    }


def test_domain_and_path_boundaries_are_enforced() -> None:
    wrong_host = replace(_step(), target_url="https://other.example.test/results")
    wrong_path = replace(_step(), target_url="https://search.example.test/admin")
    insecure = replace(_step(), target_url="http://search.example.test/results")

    host_decision = evaluate_research_step(
        _plan(), wrong_host, ResearchUsage(), _runtime(), now=NOW
    )
    path_decision = evaluate_research_step(
        _plan(), wrong_path, ResearchUsage(), _runtime(), now=NOW
    )
    scheme_decision = evaluate_research_step(
        _plan(), insecure, ResearchUsage(), _runtime(), now=NOW
    )

    assert ResearchBlockReason.TARGET_HOST_NOT_ALLOWED in host_decision.reasons
    assert ResearchBlockReason.TARGET_PATH_NOT_ALLOWED in path_decision.reasons
    assert ResearchBlockReason.TARGET_SCHEME_NOT_ALLOWED in scheme_decision.reasons


def test_step_automation_and_cost_budgets_fail_closed() -> None:
    plan = replace(
        _plan(),
        budget=ResearchBudget(
            max_steps=2,
            max_automated_steps=1,
            max_total_cost=5.0,
            max_step_cost=2.0,
        ),
    )
    usage = ResearchUsage(completed_steps=2, automated_steps=1, cost_used=4.0)
    step = replace(_step(), estimated_cost=3.0)

    decision = evaluate_research_step(plan, step, usage, _runtime(), now=NOW)

    assert set(decision.reasons) >= {
        ResearchBlockReason.STEP_BUDGET_EXHAUSTED,
        ResearchBlockReason.AUTOMATION_BUDGET_EXHAUSTED,
        ResearchBlockReason.STEP_COST_EXCEEDS_LIMIT,
        ResearchBlockReason.TOTAL_COST_BUDGET_EXHAUSTED,
    }


def test_expired_or_unapproved_plan_blocks_before_execution() -> None:
    expired = replace(_plan(), expires_at=NOW)
    draft = replace(_plan(), state=ResearchPlanState.DRAFT)

    expired_decision = evaluate_research_step(
        expired, _step(), ResearchUsage(), _runtime(), now=NOW
    )
    draft_decision = evaluate_research_step(
        draft, _step(), ResearchUsage(), _runtime(), now=NOW
    )

    assert ResearchBlockReason.PLAN_EXPIRED in expired_decision.reasons
    assert ResearchBlockReason.PLAN_NOT_APPROVED in draft_decision.reasons


def test_approved_ingestion_requires_approved_ingestion_path() -> None:
    step = replace(
        _step(),
        mode=ResearchStepMode.APPROVED_INGESTION,
        target_url=None,
        ingestion_path_id="public-footprint-ingestion",
    )
    runtime = replace(_runtime(), ingestion_path_approved=False)

    decision = evaluate_research_step(_plan(), step, ResearchUsage(), runtime, now=NOW)

    assert ResearchBlockReason.INGESTION_PATH_NOT_APPROVED in decision.reasons


def test_manual_and_automated_url_steps_require_absolute_target() -> None:
    with pytest.raises(ValueError, match="target_url"):
        replace(_step(), target_url=None)
    with pytest.raises(ValueError, match="absolute URL"):
        replace(_step(), target_url="/relative")


def _plan() -> ResearchPlan:
    return ResearchPlan(
        plan_id=PLAN_ID,
        question="What public evidence supports Acme's cloud security priorities?",
        purpose="organization-research",
        data_category=DataCategory.ORGANIZATION_METADATA,
        state=ResearchPlanState.APPROVED,
        budget=ResearchBudget(
            max_steps=10,
            max_automated_steps=3,
            max_total_cost=20.0,
            max_step_cost=5.0,
        ),
        allowed_source_ids=frozenset({"search-catalog"}),
        allowed_tool_ids=frozenset({"approved-search"}),
        approved_step_keys=frozenset({"step-1"}),
        allowed_hosts=frozenset({"search.example.test"}),
        allowed_path_prefixes=("/results",),
        max_risk_level=ResearchRiskLevel.MEDIUM,
        expires_at=NOW + timedelta(hours=4),
    )


def _step() -> ResearchStep:
    return ResearchStep(
        step_key="step-1",
        sequence=1,
        source_id="search-catalog",
        tool_id="approved-search",
        mode=ResearchStepMode.AUTOMATED_ADAPTER,
        purpose="organization-research",
        data_category=DataCategory.ORGANIZATION_METADATA,
        estimated_cost=1.0,
        risk_level=ResearchRiskLevel.LOW,
        target_url=TARGET,
        query_text="site:acme.example security cloud",
    )


def _runtime() -> ResearchRuntimeState:
    return ResearchRuntimeState(
        source_authorized=True,
        source_executable=True,
        adapter_capability_present=True,
        manual_link_allowed=True,
        ingestion_path_approved=True,
        quota_remaining=100,
    )
