from __future__ import annotations

from hashlib import sha256
from struct import unpack

from playwright.sync_api import Locator, Page

from cip.adapters.sources.public_web.artifact_context import BrowserArtifactExecutionContext
from cip.adapters.sources.public_web.artifact_policy import (
    PNG_MIME,
    BrowserArtifactPolicyError,
    BrowserArtifactUsage,
)
from cip.adapters.sources.public_web.artifact_retention import retain_artifact_if_requested
from cip.adapters.sources.public_web.browser_action_authorization import (
    authorize_browser_action_transition,
)
from cip.adapters.sources.public_web.browser_action_steps import exact_locator
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.public_footprint.domain.artifacts import (
    BrowserArtifactKind,
    BrowserArtifactState,
    BrowserEvidenceArtifact,
    BrowserScreenshotMode,
)
from cip.modules.public_footprint.domain.browser_actions import (
    BrowserActionPlan,
    BrowserActionStep,
    BrowserHttpMethod,
)
from cip.modules.public_footprint.domain.url_identity import CanonicalUrl
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_SENSITIVE_CAPTURE_SELECTOR = ", ".join(
    (
        'input[type="password"]',
        'input[type="file"]',
        'input[autocomplete="one-time-code"]',
        'input[name*="otp" i]',
        'iframe[src*="captcha" i]',
        'iframe[title*="captcha" i]',
        "[data-captcha]",
        '[data-sensitive="true"]',
    )
)


def capture_governed_screenshot(
    page: Page,
    target: PublicWebTarget,
    entry: SourceRegistryEntry,
    plan: BrowserActionPlan,
    step: BrowserActionStep,
    context: BrowserArtifactExecutionContext,
    usage: BrowserArtifactUsage,
) -> BrowserEvidenceArtifact:
    page_url = authorize_browser_action_transition(
        target,
        entry,
        plan,
        page.url,
        BrowserHttpMethod.GET,
        now=context.captured_at,
    )
    scope = _capture_scope(page, step)
    _deny_sensitive_capture(scope)
    usage.begin_screenshot(context.limits)
    content = _capture_png(page, scope, step)
    usage.admit_screenshot_bytes(content, context.limits)
    width, height = png_dimensions(content)
    retention = retain_artifact_if_requested(
        content,
        media_type=PNG_MIME,
        source_url=page_url,
        entry=entry,
        plan=plan,
        step=step,
        context=context,
    )
    return BrowserEvidenceArtifact(
        source_id=plan.source_id,
        provider_id=plan.provider_id,
        target_id=target.id,
        job_id=context.job_id,
        plan_id=plan.plan_id,
        plan_version=plan.version,
        step_id=step.step_id,
        kind=BrowserArtifactKind.SCREENSHOT,
        state=BrowserArtifactState.PROCESSED,
        page_url=CanonicalUrl(page_url).value,
        source_url=CanonicalUrl(page_url).value,
        captured_at=context.captured_at,
        content_hash_sha256=sha256(content).hexdigest(),
        byte_size=len(content),
        media_type=PNG_MIME,
        source_locator=_source_locator(plan, step),
        raw_retention_allowed=retention.allowed,
        raw_retained=retention.retained,
        storage_uri=retention.storage_uri,
        retention_until=context.retention_until if retention.retained else None,
        screenshot_mode=step.screenshot_mode,
        viewport_width=width,
        viewport_height=height,
        element_selector=(
            step.selector if step.screenshot_mode is BrowserScreenshotMode.ELEMENT else None
        ),
    )


def png_dimensions(content: bytes) -> tuple[int, int]:
    if len(content) < 24 or not content.startswith(_PNG_SIGNATURE) or content[12:16] != b"IHDR":
        raise BrowserArtifactPolicyError("browser_screenshot_invalid_png")
    width, height = unpack(">II", content[16:24])
    if width < 1 or height < 1 or width > 20_000 or height > 20_000:
        raise BrowserArtifactPolicyError("browser_screenshot_dimensions_invalid")
    return width, height


def _capture_scope(page: Page, step: BrowserActionStep) -> Locator:
    if step.screenshot_mode is BrowserScreenshotMode.ELEMENT:
        return exact_locator(page, step.selector)
    if step.screenshot_mode is not BrowserScreenshotMode.VIEWPORT:
        raise BrowserArtifactPolicyError("browser_screenshot_mode_invalid")
    root = page.locator("html")
    if root.count() != 1:
        raise BrowserArtifactPolicyError("browser_screenshot_document_root_invalid")
    return root


def _deny_sensitive_capture(scope: Locator) -> None:
    if scope.locator(_SENSITIVE_CAPTURE_SELECTOR).count() > 0:
        raise BrowserArtifactPolicyError("browser_screenshot_sensitive_surface_denied")


def _capture_png(page: Page, scope: Locator, step: BrowserActionStep) -> bytes:
    if step.screenshot_mode is BrowserScreenshotMode.ELEMENT:
        return scope.screenshot(type="png")
    return page.screenshot(type="png", full_page=False)


def _source_locator(plan: BrowserActionPlan, step: BrowserActionStep) -> str:
    return f"browser-action:{plan.plan_id}:{plan.version}:{step.step_id}"
