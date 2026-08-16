from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from cip.adapters.sources.public_web.browser_action_authorization import (
    BrowserActionAuthorizationError,
    authorize_browser_action_transition,
)
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.public_footprint.domain.browser_actions import (
    BrowserActionKind,
    BrowserActionPlan,
    BrowserActionStep,
    BrowserHttpMethod,
    BrowserTransitionRule,
)
from cip.modules.source_governance.domain.models import (
    AuthorizationStatus,
    DataCategory,
    HttpMethod,
    SourceAuthorization,
    SourcePolicy,
    SourceStatus,
    SourceType,
)
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry

NOW = datetime(2026, 8, 16, 17, 0, tzinfo=UTC)


def _target() -> PublicWebTarget:
    return PublicWebTarget(
        id="browser-actions",
        organization_id=uuid4(),
        canonical_name="Browser Actions",
        base_url="https://example.com/",
        seed_urls=("https://example.com/public/form",),
        sitemap_urls=(),
        feed_urls=(),
        discover_security_txt=False,
        discover_sitemaps=False,
        discover_feeds=False,
        allowed_path_prefixes=("/public",),
        enabled=True,
        authorization_reference="L13-test-approval",
        authorization_reviewed_at=NOW,
        max_pages=10,
        max_total_bytes=100_000,
        max_resource_bytes=50_000,
        max_redirects=2,
    )


def _entry(target: PublicWebTarget) -> SourceRegistryEntry:
    return SourceRegistryEntry(
        policy=SourcePolicy(
            id=target.id,
            name="Browser Actions",
            base_url=target.base_url,
            status=SourceStatus.ENABLED,
            source_type=SourceType.BROWSER,
            owner="tests",
            licence="controlled L13 fixture",
            allowed_data_categories=frozenset({DataCategory.OFFICIAL_DOCUMENT_DISCOVERY}),
            human_review_required=False,
        ),
        authorization=SourceAuthorization(
            status=AuthorizationStatus.APPROVED,
            document_reference="L13-test-approval",
            reviewed_at=NOW,
            approved_hosts=frozenset({target.host}),
            approved_path_prefixes=("/public",),
            approved_purposes=frozenset({"corporate-public-footprint"}),
            approved_http_methods=frozenset({HttpMethod.GET, HttpMethod.POST}),
            automated_collection_allowed=True,
        ),
        economics={"monthly_cost": 0},
    )


def _plan(
    target: PublicWebTarget,
    *,
    source_id: str | None = None,
    target_id: str | None = None,
    path_prefix: str = "/public",
) -> BrowserActionPlan:
    return BrowserActionPlan(
        plan_id=uuid4(),
        version=1,
        source_id=source_id or target.id,
        provider_id="fixture-provider",
        target_id=target_id or target.id,
        purpose="corporate-public-footprint",
        steps=(
            BrowserActionStep(
                step_id="navigate",
                kind=BrowserActionKind.NAVIGATE,
                target_url="https://example.com/public/form",
            ),
        ),
        allowed_transitions=(
            BrowserTransitionRule(
                host=target.host,
                path_prefix=path_prefix,
                methods=frozenset({BrowserHttpMethod.GET}),
            ),
        ),
        max_actions=1,
        max_total_value_chars=0,
    )


def test_transition_rejects_source_and_target_identity_mismatches() -> None:
    target = _target()
    entry = _entry(target)

    with pytest.raises(BrowserActionAuthorizationError, match="source_mismatch"):
        authorize_browser_action_transition(
            target,
            entry,
            _plan(target, source_id="other-source"),
            "https://example.com/public/form",
            BrowserHttpMethod.GET,
            now=NOW,
        )

    with pytest.raises(BrowserActionAuthorizationError, match="target_mismatch"):
        authorize_browser_action_transition(
            target,
            entry,
            _plan(target, target_id="other-target"),
            "https://example.com/public/form",
            BrowserHttpMethod.GET,
            now=NOW,
        )


def test_transition_rejects_target_scope_before_plan_scope() -> None:
    target = _target()

    with pytest.raises(BrowserActionAuthorizationError):
        authorize_browser_action_transition(
            target,
            _entry(target),
            _plan(target),
            "https://example.com/private/form",
            BrowserHttpMethod.GET,
            now=NOW,
        )


def test_transition_rejects_url_not_allowed_by_plan() -> None:
    target = _target()

    with pytest.raises(BrowserActionAuthorizationError, match="transition_not_allowed"):
        authorize_browser_action_transition(
            target,
            _entry(target),
            _plan(target, path_prefix="/public/approved"),
            "https://example.com/public/form",
            BrowserHttpMethod.GET,
            now=NOW,
        )


def test_root_plan_transition_prefix_matches_approved_target_path() -> None:
    target = _target()

    authorized = authorize_browser_action_transition(
        target,
        _entry(target),
        _plan(target, path_prefix="/"),
        "https://example.com/public/form",
        BrowserHttpMethod.GET,
        now=NOW,
    )

    assert authorized == "https://example.com/public/form"
