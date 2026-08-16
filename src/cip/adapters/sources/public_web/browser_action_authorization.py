from __future__ import annotations

from datetime import datetime

from cip.adapters.sources.public_web.collection_policy import authorize_public_web_url
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.public_footprint.domain.browser_actions import (
    BrowserActionPlan,
    BrowserHttpMethod,
)
from cip.modules.public_footprint.domain.scope import CrawlUsage
from cip.modules.public_footprint.domain.url_identity import CanonicalUrl, same_origin
from cip.modules.source_governance.domain.models import HttpMethod
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry


class BrowserActionAuthorizationError(RuntimeError):
    """A planned browser transition is outside an approved public-web scope."""


def authorize_browser_action_transition(
    target: PublicWebTarget,
    entry: SourceRegistryEntry,
    plan: BrowserActionPlan,
    url: str,
    method: BrowserHttpMethod,
    *,
    now: datetime,
) -> str:
    canonical = CanonicalUrl(url)
    if plan.source_id not in {entry.policy.id, target.source_id}:
        raise BrowserActionAuthorizationError("browser_action_source_mismatch")
    if plan.target_id != target.id:
        raise BrowserActionAuthorizationError("browser_action_target_mismatch")
    if not same_origin(target.base_url, canonical):
        raise BrowserActionAuthorizationError("browser_action_off_origin_denied")
    decision = target.crawl_scope.evaluate_target(
        canonical,
        depth=0,
        redirects=0,
        usage=CrawlUsage(),
    )
    if not decision.allowed:
        raise BrowserActionAuthorizationError(decision.reason.value)
    if not _plan_transition_allows(plan, canonical, method):
        raise BrowserActionAuthorizationError("browser_action_transition_not_allowed")
    authorize_public_web_url(
        entry,
        canonical.value,
        now=now,
        http_method=HttpMethod(method.value),
        purpose=plan.purpose,
    )
    return canonical.value


def _plan_transition_allows(
    plan: BrowserActionPlan,
    url: CanonicalUrl,
    method: BrowserHttpMethod,
) -> bool:
    return any(
        rule.host == url.host
        and _path_matches(url.path, rule.path_prefix)
        and method in rule.methods
        for rule in plan.allowed_transitions
    )


def _path_matches(path: str, prefix: str) -> bool:
    normalized = prefix.rstrip("/") or "/"
    if normalized == "/":
        return True
    return path == normalized or path.startswith(f"{normalized}/")
