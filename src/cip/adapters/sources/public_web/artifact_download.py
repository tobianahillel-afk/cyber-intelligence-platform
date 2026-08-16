from __future__ import annotations

from hashlib import sha256
from urllib.parse import urljoin

from playwright.sync_api import Page

from cip.adapters.sources.public_web.artifact_context import BrowserArtifactExecutionContext
from cip.adapters.sources.public_web.artifact_policy import (
    BrowserArtifactPolicyError,
    BrowserArtifactUsage,
    original_filename,
    validate_download_media_type,
)
from cip.adapters.sources.public_web.artifact_quarantine import quarantined_artifact
from cip.adapters.sources.public_web.artifact_retention import retain_artifact_if_requested
from cip.adapters.sources.public_web.browser_action_authorization import (
    authorize_browser_action_transition,
)
from cip.adapters.sources.public_web.browser_action_steps import exact_locator
from cip.adapters.sources.public_web.client_contract import (
    PUBLIC_WEB_USER_AGENT,
    REDIRECT_STATUSES,
    PublicWebResponseError,
)
from cip.adapters.sources.public_web.client_helpers import content_type, header
from cip.adapters.sources.public_web.client_http import BoundedHttpTransport
from cip.adapters.sources.public_web.document_parsing import (
    ExtractedDocument,
    extract_pdf_text,
    extract_plain_text,
)
from cip.adapters.sources.public_web.ooxml_parsing import (
    DOCX_MIME,
    PPTX_MIME,
    XLSX_MIME,
    extract_ooxml_text,
)
from cip.adapters.sources.public_web.registry import PublicWebTarget
from cip.modules.public_footprint.domain.artifacts import (
    BrowserArtifactKind,
    BrowserArtifactState,
    BrowserEvidenceArtifact,
)
from cip.modules.public_footprint.domain.browser_actions import (
    BrowserActionPlan,
    BrowserActionStep,
    BrowserHttpMethod,
)
from cip.modules.public_footprint.domain.models import (
    DiscoveryMethod,
    PublicFootprintProjection,
    PublicResource,
    PublicResourceKind,
    PublicResourceVersion,
    ResourceAccessState,
    ResourceRetrievalState,
)
from cip.modules.public_footprint.domain.url_identity import CanonicalUrl
from cip.modules.source_governance.infrastructure.registry import SourceRegistryEntry

_PDF_MIME = "application/pdf"
_TEXT_MIME = "text/plain"
_DOWNLOAD_ACCEPT = ",".join((_PDF_MIME, _TEXT_MIME, DOCX_MIME, XLSX_MIME, PPTX_MIME))


def collect_governed_download(
    page: Page,
    target: PublicWebTarget,
    entry: SourceRegistryEntry,
    plan: BrowserActionPlan,
    step: BrowserActionStep,
    context: BrowserArtifactExecutionContext,
    usage: BrowserArtifactUsage,
    *,
    timeout_ms: int,
) -> tuple[BrowserEvidenceArtifact, PublicFootprintProjection]:
    download_url = _preflight_download(page, target, entry, plan, step, context)
    max_bytes = usage.begin_download(context.limits)
    response_url, body, reported_mime = _fetch_download(
        target,
        entry,
        plan,
        download_url,
        context,
        max_bytes=max_bytes,
        timeout_ms=timeout_ms,
    )
    usage.admit_download_bytes(body, context.limits)
    with quarantined_artifact(body, suffix=".bin") as quarantine_path:
        quarantined = quarantine_path.read_bytes()
        media_type = validate_download_media_type(response_url, reported_mime, quarantined)
        extracted = _parse_download(quarantined, media_type=media_type)
        digest = sha256(quarantined).hexdigest()
        extracted_hash = sha256(extracted.text.encode("utf-8")).hexdigest()
        retention = retain_artifact_if_requested(
            quarantined,
            media_type=media_type,
            source_url=response_url,
            entry=entry,
            plan=plan,
            step=step,
            context=context,
        )
    locator = _source_locator(plan, step)
    artifact = BrowserEvidenceArtifact(
        source_id=plan.source_id,
        provider_id=plan.provider_id,
        target_id=target.id,
        job_id=context.job_id,
        plan_id=plan.plan_id,
        plan_version=plan.version,
        step_id=step.step_id,
        kind=BrowserArtifactKind.DOWNLOAD,
        state=BrowserArtifactState.PROCESSED,
        page_url=CanonicalUrl(page.url).value,
        source_url=response_url,
        captured_at=context.captured_at,
        content_hash_sha256=digest,
        byte_size=len(body),
        media_type=media_type,
        source_locator=locator,
        raw_retention_allowed=retention.allowed,
        raw_retained=retention.retained,
        storage_uri=retention.storage_uri,
        retention_until=context.retention_until if retention.retained else None,
        original_filename=original_filename(response_url),
        extracted_text_hash_sha256=extracted_hash,
        excerpt=extracted.excerpt,
    )
    return artifact, _download_projection(
        target,
        plan,
        response_url,
        body,
        media_type,
        extracted,
        locator,
        context,
    )


def _preflight_download(
    page: Page,
    target: PublicWebTarget,
    entry: SourceRegistryEntry,
    plan: BrowserActionPlan,
    step: BrowserActionStep,
    context: BrowserArtifactExecutionContext,
) -> str:
    link = exact_locator(page, step.selector)
    if link.locator("xpath=self::a").count() != 1:
        raise BrowserArtifactPolicyError("browser_download_selector_must_resolve_to_link")
    href = link.get_attribute("href")
    if href is None:
        raise BrowserArtifactPolicyError("browser_download_link_missing_href")
    actual = CanonicalUrl(urljoin(page.url, href)).value
    expected = CanonicalUrl(step.expected_download_url or "").value
    if actual != expected:
        raise BrowserArtifactPolicyError("browser_download_link_does_not_match_plan")
    return authorize_browser_action_transition(
        target,
        entry,
        plan,
        actual,
        BrowserHttpMethod.GET,
        now=context.captured_at,
    )


def _fetch_download(
    target: PublicWebTarget,
    entry: SourceRegistryEntry,
    plan: BrowserActionPlan,
    initial_url: str,
    context: BrowserArtifactExecutionContext,
    *,
    max_bytes: int,
    timeout_ms: int,
) -> tuple[str, bytes, str]:
    transport = BoundedHttpTransport(
        context.download_client,
        request_timeout_seconds=min(
            context.limits.request_timeout_seconds,
            timeout_ms / 1_000,
        ),
    )
    current = initial_url
    redirects = 0
    while True:
        current = authorize_browser_action_transition(
            target,
            entry,
            plan,
            current,
            BrowserHttpMethod.GET,
            now=context.captured_at,
        )
        response = transport.get(
            current,
            headers={"Accept": _DOWNLOAD_ACCEPT, "User-Agent": PUBLIC_WEB_USER_AGENT},
            follow_redirects=False,
            max_bytes=max_bytes,
        )
        if response.status_code in REDIRECT_STATUSES:
            location = header(response, "location")
            if not location:
                raise PublicWebResponseError("download redirect omitted Location")
            redirects += 1
            if redirects > min(context.limits.max_redirects, target.max_redirects):
                raise BrowserArtifactPolicyError("browser_download_redirect_budget_exceeded")
            current = CanonicalUrl(urljoin(current, location)).value
            continue
        response.raise_for_status()
        return current, response.content, content_type(response)


def _parse_download(body: bytes, *, media_type: str) -> ExtractedDocument:
    if media_type == _PDF_MIME:
        return extract_pdf_text(body)
    if media_type == _TEXT_MIME:
        return extract_plain_text(body)
    if media_type in {DOCX_MIME, XLSX_MIME, PPTX_MIME}:
        return extract_ooxml_text(body, mime_type=media_type)
    raise BrowserArtifactPolicyError("browser_download_parser_unavailable")


def _download_projection(
    target: PublicWebTarget,
    plan: BrowserActionPlan,
    source_url: str,
    body: bytes,
    media_type: str,
    extracted: ExtractedDocument,
    source_locator: str,
    context: BrowserArtifactExecutionContext,
) -> PublicFootprintProjection:
    resource = PublicResource(
        organization_id=target.organization_id,
        source_id=plan.source_id,
        source_record_key=f"browser-download:{sha256(source_url.encode('utf-8')).hexdigest()}",
        canonical_url=source_url,
        source_url=source_url,
        kind=PublicResourceKind.DOCUMENT,
        discovery_method=DiscoveryMethod.LINK,
        first_discovered_at=context.captured_at,
        last_seen_at=context.captured_at,
        access_state=ResourceAccessState.PUBLIC,
        retrieval_state=ResourceRetrievalState.FETCHED,
        title=extracted.title,
    )
    version = PublicResourceVersion(
        resource_key=resource.identity_key,
        source_url=source_url,
        content_hash_sha256=sha256(body).hexdigest(),
        fetched_at=context.captured_at,
        mime_type=media_type,
        byte_size=len(body),
        title=extracted.title,
        language=extracted.language,
        extracted_text_hash_sha256=sha256(extracted.text.encode("utf-8")).hexdigest(),
        excerpt=extracted.excerpt,
        source_locator=source_locator,
    )
    return PublicFootprintProjection(resource=resource, version=version)


def _source_locator(plan: BrowserActionPlan, step: BrowserActionStep) -> str:
    return f"browser-action:{plan.plan_id}:{plan.version}:{step.step_id}"
